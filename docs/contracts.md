# Interface and operational contracts

## Application

| Route | Behavior |
| --- | --- |
| `GET /` | Product list and creation form |
| `POST /products` | Code/name form; 302 success, 400 invalid, 409 duplicate |
| `GET /products/<id>` | Stock and adjustment history; 404 missing |
| `POST /products/<id>/adjustments` | Integer quantity and reason; 409 stock bounds, 400 invalid |
| `GET /health/live` | Process alive, 200 JSON |
| `GET /health/ready` | Database/schema available, 200; otherwise 503 without connection details |
| `GET /version` | JSON `version` matching the deployed commit SHA or `local` |

Forms require the session's CSRF token. Product codes normalize to uppercase; names and notes are escaped by templates. Initial stock is zero. Every accepted adjustment updates stock and inserts history in one transaction; conditional SQL updates prevent concurrent negative stock. Quantity is nonzero and at most 1,000,000 in magnitude; final stock fits a signed 32-bit integer. This app has no user accounts and is only intended for an IP-restricted demo.

## Runtime configuration

| Variable | Meaning |
| --- | --- |
| `DATABASE_URL` | Local PostgreSQL URL; SQLite fallback for local development |
| `DB_SECRET_ARN` | AWS mode: fetch username/password at worker startup |
| `DB_HOST` | RDS hostname in AWS mode |
| `AWS_REGION` | Region used by the runtime Secrets Manager client |
| `APP_SECRET` | Per-host random session signing secret; local demo default only |
| `APP_VERSION` | Full release commit SHA for `/version` |
| `TEST_DATABASE_URL` | Disposable integration database; tests drop/recreate tables |

AWS mode takes precedence over DATABASE_URL. PostgreSQL uses `verify-full` TLS against the RDS CA bundle. Credentials are fetched at startup, so restart after rotation. Terraform contains the secret ARN, not its value. `flask --app app init-db` creates absent tables without dropping existing data; it is not a schema migration framework.

## Terraform and delivery

Dev outputs: `instance_id`, `app_url`, `db_host`, `db_secret_arn`, and `log_group`. Bootstrap outputs: `state_bucket`, `artifact_bucket`, `ecr_repository`, and the map `github_roles` with `build`, `plan`, and `deploy` entries. Local AMI/CIDR values must match repository variables when switching to CI management.

Private artifact bucket records:

- `releases/<sha>.json`: source SHA, repository, full ECR digest reference, and originating build run ID.
- `plans/<run-id>/plan`: binary Terraform plan, paired with `manifest.json` containing infrastructure SHA, repository, operation, release, target settings, timestamp, Terraform version, and SHA256 checksum.
- `successful/<run-id>.json`: release and repository, written only after the SSM readiness/version checks pass.

Records use conditional creation to prevent overwrites. ECR commit tags are immutable. Never use `latest` as the deployment contract. Infrastructure planning always uses current main; the selected application release may be an older successful main build. Apply rechecks build/plan workflow identity and refuses stale or altered inputs. Rollback requires a success marker and does not change Terraform or database schema.

Only trusted main workflows get OIDC credentials. Build has ECR push and release-write permissions; plan reads infrastructure/state and writes reviewed plans; deploy changes the application stack and writes success records. Network creation actions use a regional boundary where API resources are generated; these roles are appropriate for a sandbox account, not a shared production administrative boundary. The EC2 role's inline secret permission is the exact RDS secret ARN; its boundary alone grants nothing.

The single-instance rollout briefly interrupts service and does not provide automatic rollback or high availability. Runtime AWS calls originate from the public EC2 instance over outbound internet access, while RDS has no public endpoint. GitHub smoke probes execute through SSM on the host, so no runner IP allowlist or public health endpoint is needed.

Both startup commands use two Gunicorn `gthread` workers with four threads each. This accommodates idle browser preconnections when serving the learner directly. The default synchronous workers can block waiting for request bytes and time out before Flask sees a request. See [Gunicorn's worker design](https://gunicorn.org/design/). The Docker smoke test holds idle TCP connections open while checking HTTP responsiveness to guard against this regression.
