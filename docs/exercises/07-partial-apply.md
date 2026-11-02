# Drill 7 — Partial apply does not mean rollback

## Prerequisites

Clean exercise baseline and backup. This drill adds local `terraform_data` resources to the exercise state; it does not intentionally break a cloud service.

## Break

```powershell
Copy-Item infra/state-lab/partial.tf.example infra/state-lab/partial.tf
terraform -chdir=infra/state-lab apply
terraform -chdir=infra/state-lab state list
terraform -chdir=infra/state-lab plan
```

Approve the two additions. The second resource runs a deliberately nonexistent local command.

## Observe

Apply fails after the first resource succeeds. State records partial progress, and the failed provisioner resource may be tainted and proposed for replacement. Terraform does not roll back everything that already succeeded. Provisioners are used here only to reproduce failure deterministically, not as a recommended infrastructure design.

## Hint

Read the resource-level error, inspect state, and compare a new plan. Replaying an old saved plan is not the recovery procedure.

## Recover

Edit `partial.tf` and remove the `provisioner "local-exec"` block from `terraform_data.failure`. Retain the resource and its dependency. Generate and review a new plan, then apply. Expected: Terraform reconciles the incomplete/tainted resource while preserving successful resources. Confirm another plan has no changes.

In a real AWS failure, also inspect remote resources: a service may have completed a request before Terraform received an error. Import an orphan only after verifying ownership and configuration; do not assume every error leaves the world unchanged.

## Reset

```powershell
Remove-Item -LiteralPath infra/state-lab/partial.tf
terraform -chdir=infra/state-lab apply
terraform -chdir=infra/state-lab plan
```

Expected: two bookkeeping resources removed; the parameter remains.

## Checkpoint

Explain what succeeded, what failed, what state recorded, and why a new plan was needed.
