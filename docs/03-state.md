# 3 — Bootstrap and remote state

## Prerequisites and costs

Complete the local Docker lesson and authenticate to a sandbox AWS account. Bootstrap creates S3 storage, ECR, IAM roles, and optionally the account-level GitHub OIDC provider. Storage and registry images can continue costing money after app teardown. Choose globally unique S3 names. Keep the default project and region names.

Create a new GitHub repository named `inventory-manager-lab` yourself, or choose the future `OWNER/REPO` now. Existing GitHub OIDC providers are account-wide: reuse the ARN instead of trying to create a duplicate.

## Bootstrap locally, then migrate

```powershell
Copy-Item infra/bootstrap/terraform.tfvars.example infra/bootstrap/terraform.tfvars
# Edit unique bucket names, OWNER/REPO, and existing provider ARN if applicable.
terraform -chdir=infra/bootstrap init
terraform -chdir=infra/bootstrap plan -out=bootstrap.tfplan
terraform -chdir=infra/bootstrap apply bootstrap.tfplan
terraform -chdir=infra/bootstrap output
Copy-Item infra/bootstrap/backend.tf.example infra/bootstrap/backend.tf
Copy-Item infra/bootstrap/backend.s3.tfbackend.example infra/bootstrap/backend.s3.tfbackend
# Edit the backend bucket to match the newly created state bucket.
terraform -chdir=infra/bootstrap init -migrate-state -backend-config=backend.s3.tfbackend
terraform -chdir=infra/bootstrap state list
terraform -chdir=infra/bootstrap plan
```

Expected: Terraform asks whether to copy existing state. Accept after checking the bucket/key. State addresses remain unchanged and the plan is empty. Keep local backup state secure until verification is complete. Commit `backend.tf`, but not the actual `.tfbackend`, tfvars, state, or plan files.

S3 uses versioning, encryption, public-access blocking, and TLS-only access. Native `use_lockfile=true` creates an adjacent `.tflock` while an operation owns the state. DynamoDB is not used. [HashiCorp documents S3 locking and versioning](https://developer.hashicorp.com/terraform/language/backend/s3).

## Separate responsibilities

| Root | Key | Who writes |
| --- | --- | --- |
| Bootstrap | `bootstrap/inventory-manager/terraform.tfstate` | Local bootstrap administrator |
| App | `dev/inventory-manager/terraform.tfstate` | Local learner or deployment role |
| Exercises | `exercises/<lab-id>/terraform.tfstate` | Local learner only |

The GitHub plan role reads app state and manages its lock; deploy may also write app state. Neither can access bootstrap or exercise state. Build can publish images/releases but cannot access Terraform state. Scoped application IAM permissions include a runtime permissions boundary; EC2/network API actions are region-bounded and still powerful, so use a sandbox account.

## Migrate the disposable parameter

```powershell
Copy-Item infra/state-lab/backend.tf.example infra/state-lab/backend.tf
Copy-Item infra/state-lab/backend.s3.tfbackend.example infra/state-lab/backend.s3.tfbackend
# Set the real state bucket and exercises/<your-lab-id>/terraform.tfstate key.
terraform -chdir=infra/state-lab init -migrate-state -backend-config=backend.s3.tfbackend
terraform -chdir=infra/state-lab plan
```

**Hint:** backend configuration controls where state is stored; it does not rename resources. **Solution:** use `-migrate-state` when moving existing state. Use `-reconfigure` only when deliberately selecting a backend without copying state, such as reconnecting to the correct key after the wrong-key drill.

## Troubleshooting, checkpoint, and reset

AccessDenied may refer to the bucket, state object, or lock object: inspect which API/key failed before changing permissions. A bucket must exist before an S3 backend can initialize. A missing key with existing infrastructure is not permission to recreate the stack.

Checkpoint: both migrated roots show their original addresses and clean plans. Explain why the three roots do not share a key. Bootstrap has `prevent_destroy`; ordinary cleanup destroys dev and exercise resources only. Do not reset this lesson by deleting the state bucket.
