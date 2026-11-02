# Drill 2 — Out-of-band drift

## Prerequisites

Use the shared exercise variables and baseline backup. The marker in configuration is `baseline`.

## Break

```powershell
aws ssm put-parameter --name $ParameterName --type String --value changed-outside-terraform --overwrite
terraform -chdir=infra/state-lab plan
```

## Observe

The plan detects the real parameter value and proposes restoring the configured value. State is not the desired configuration; HCL is.

## Hint

Decide whether the external change was a mistake or an intentional new requirement before applying anything.

## Recover

Path A, restore the reference configuration:

```powershell
terraform -chdir=infra/state-lab apply
```

Path B, repeat the break and deliberately accept the external change: set `marker = "changed-outside-terraform"` in `infra/state-lab/terraform.tfvars`, then plan/apply. A `plan -refresh-only` can show bookkeeping updates, but does not update your HCL; refresh-only alone would leave configuration disagreement for the next normal plan.

## Reset

Set `marker = "baseline"` in tfvars and apply. Run a final plan and verify no changes. Do not use `ignore_changes` to hide this exercise.

## Checkpoint

Explain restore-versus-accept and demonstrate a clean plan after each chosen recovery.
