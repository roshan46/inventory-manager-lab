# 5 — Build, review, deploy, and roll back

## Prerequisites

Complete bootstrap. Publish **this directory as the repository root**, not the enclosing collection of labs. Initialize Git here if necessary, add the files, and push to a new main branch in the repository matching bootstrap's `github_repository`. Keep `.terraform.lock.hcl` files and `uv.lock` tracked. Do not publish real tfvars, state, plan files, `.env`, or `.scratch`.

Workflows use [GitHub OIDC for AWS](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws), restricted to the configured repository's `main` branch. No long-lived AWS access-key secrets are needed. Protect main and require checks/reviews as supported by your repository. The baseline uses separate manual plan/apply dispatches and does not require GitHub environment approval features. If GitHub emits a customized subject, set its exact `sub` claim as `github_oidc_subject` in the bootstrap tfvars, review and apply the bootstrap trust-policy change, and then rerun authentication. If you add an environment, update the subject to match it before running.

## Configure repository variables

In GitHub Settings → Secrets and variables → Actions → Variables:

| Variable | Value |
| --- | --- |
| `STATE_BUCKET` | Bootstrap state bucket output |
| `ARTIFACT_BUCKET` | Bootstrap artifact bucket output |
| `ECR_REPOSITORY` | Full bootstrap ECR repository URL, without tag |
| `BUILD_ROLE_ARN` | Bootstrap `github_roles.build` |
| `PLAN_ROLE_ARN` | Bootstrap `github_roles.plan` |
| `DEPLOY_ROLE_ARN` | Bootstrap `github_roles.deploy` |
| `LEARNER_CIDR` | Your public IPv4 `/32` |
| `AMI_ID` | Pinned AL2023 x86_64 AMI from the AWS lesson |
| `LAB_READY` | `true` only after the above are configured |

Region and project name are intentionally fixed to the defaults in the workflow examples. Do not customize Terraform names independently of scoped IAM and delivery configuration.

## Build and release

1. Open a PR. Checks run SQLite and disposable PostgreSQL tests, Terraform mocked tests, HCL/YAML/lesson checks, actionlint, and the real Docker lifecycle smoke test. PRs receive no AWS credentials.
2. Merge to main. The build workflow repeats checks, builds an amd64 image, pushes an immutable commit tag to ECR, and records its digest in private S3 at `releases/<sha>.json`.
3. Copy the full commit SHA from a **successful** build run. Re-running a completed publish for the same SHA deliberately fails rather than overwriting immutable tags/manifests; use the existing successful release, or create a new commit if a publish was interrupted.

## Review and deploy

1. Manually run **Plan deployment or destroy** on main with `operation=deploy` and the successful release SHA. Older successful main releases are allowed; the infrastructure is always planned from current main.
2. Review Terraform's plan log, especially replacements/deletions. The summary identifies the plan run ID, infrastructure commit, and image digest.
3. Manually run **Apply reviewed plan** on main with that plan run ID and `operation=deploy`.
4. Confirm readiness/version checks succeed, then visit the app from your allowed IP and inspect inventory data.

Binary plans are stored only in the private S3 artifact bucket, not public GitHub artifacts. Plan text may still contain infrastructure identifiers; keep repository access appropriate. The helper checks successful run identity, repository, main commit, region, bucket configuration, AMI, CIDR, age (24 hours), Terraform version, plan hash, and release identity. Terraform rejects stale state at apply. A failed validation requires a new reviewed plan; there is no automatic re-plan during apply.

Plan/apply/rollback share `inventory-dev` concurrency and never cancel running operations. GitHub may replace a pending run when multiple runs queue; avoid dispatching several operations at once. Do not make local applies while a workflow owns the environment.

## Rollback exercise

Deploy release A, change visible UI text, build/deploy B, then run **Roll back application image** with A's successful apply run ID. Expected: `/version` returns A's SHA; inventory data remains. **Hint:** rollback changes the image, not Terraform configuration. **Solution:** the helper reads an immutable success marker and deploys A's digest against the current infrastructure.

A failed image rollout leaves the workflow red; inspect SSM output and CloudWatch before choosing rollback. It does not claim automatic rollback. `init-db` creates missing tables only; destructive or incompatible database migrations are outside this version's release contract.

## Destroy and troubleshooting

For teardown, dispatch plan with `operation=destroy` (release SHA unused), review it, then dispatch apply with the same operation. A deploy plan cannot be applied as destroy. Bootstrap and images remain.

OIDC AccessDenied: verify exact repository spelling, main branch, and provider ARN. If GitHub is configured with a custom OIDC subject template, adapt the trust subject to that template. State AccessDenied: verify the fixed dev key and state bucket. Expired/stale plan: generate and review another. Failed SSM command: inspect its command ID; rerunning a successful Terraform apply plan may be stale, so make a fresh no-change plan to retry the image deployment.

## Checkpoint

Demonstrate PR checks, a successful main build, a reviewed deployment, and rollback with retained data. Explain the difference between an image tag and digest, and why a saved plan cannot be silently regenerated after review.
