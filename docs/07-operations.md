# 7 — Operate and clean up

## Prerequisites

A successful deployment and its release SHA/run ID. Keep demo data only. The application uses the RDS-managed administrator credential for simplicity; a production system should separate migration and limited runtime database users and add authentication/HTTPS.

## Diagnose by layer

| Symptom | Inspect | Likely next step |
| --- | --- | --- |
| Browser times out, SSM smoke passes | Learner CIDR, instance public IP | Review/apply corrected `/32`; use current output URL |
| EC2 absent from SSM | Instance profile, outbound route, SSM agent | Repair IAM/network/cloud-init, then retry |
| Image pull fails | ECR digest, repository, instance role | Verify image exists and role can pull |
| Container exits | SSM command output, CloudWatch app logs | Fix configuration/image, build a new release |
| Liveness 200, readiness 503 | Database availability, schema, secret, security groups | Restore connectivity or rerun idempotent initialization |
| Authentication fails after rotation | Worker startup time, RDS secret status | Redeploy/restart to fetch the new secret |
| Terraform apply fails halfway | Error, new plan, AWS objects and state | Reconcile partial progress; never assume rollback |

The deployment's SSM command output includes the relevant command ID on failure. View Run Command history in AWS Systems Manager. Use Session Manager for interactive diagnostics if your local identity has session permissions. Useful host commands:

```sh
sudo cloud-init status --long
sudo tail -n 60 /var/log/cloud-init-output.log
sudo docker ps -a
sudo docker inspect inventory-app --format '{{json .State.Health}}'
curl -i http://localhost:8000/health/ready
curl -s http://localhost:8000/version
```

App output is sent through Docker's awslogs driver to `/inventory-manager/dev/app`. Avoid printing container environment values or secret responses. Database logs are in `/aws/rds/instance/inventory-manager-dev-db/postgresql`.

## Exercise: recover an unhealthy release

Use a local-only configuration error first: stop the Compose database and observe readiness while liveness remains healthy. **Hint:** changing the image is unnecessary when the database is stopped. **Solution:** restart PostgreSQL and wait for readiness. For AWS release failures, choose a previously successful image through the rollback workflow after checking database compatibility.

Image rollback changes application code. Terraform state recovery changes resource bookkeeping. RDS snapshot restore recovers database storage into a database instance. These are three different recovery operations; none substitutes for the others.

## Deliberate teardown

1. Stop creating inventory data. Export anything you intend to keep.
2. Decide whether to keep a final RDS snapshot. The reference lab defaults to disposable data (`db_skip_final_snapshot=true`). For retention, set it false and provide a unique `inventory-manager-dev-...` snapshot identifier. For CI, make these defaults a reviewed configuration change before planning destroy; local tfvars are not uploaded to GitHub.
3. Dispatch a destroy plan, inspect it, then apply that exact plan. Local alternative:

```powershell
terraform -chdir=infra/dev plan -destroy -out=destroy.tfplan
terraform -chdir=infra/dev apply destroy.tfplan
terraform -chdir=infra/dev state list
```

4. Verify dev state has no entries. In AWS, verify EC2, RDS, network interfaces, security groups, VPC resources, and application log groups are removed. Inspect retained snapshots and managed secret deletion status separately.
5. Destroy the disposable state-lab resources with their own reviewed destroy plan. Confirm the marker parameter is gone.
6. Retain bootstrap state, buckets, ECR, and OIDC/IAM for future lessons. Inventory their remaining storage charges; remove unused plan objects and old images deliberately once rollback/recovery exercises are finished.

Bootstrap buckets and ECR have `prevent_destroy`; buckets also refuse automatic content deletion. Final bootstrap removal is a separate administrator exercise: export and verify required state, remove every owned version/delete marker/image deliberately, migrate bootstrap state to a secure local file, review removal of the retention guards, then review a bootstrap destroy plan. Never remove an account-wide OIDC provider used by another project; an externally supplied provider is not owned by this lab.

## Checkpoint

Demonstrate one failure diagnosis and one rollback. Finish with empty dev/exercise states, verify remote resources are gone, and explain what retained resources can still cost money. Local cleanup is `docker compose down`; add `--volumes` only to discard local demo data.
