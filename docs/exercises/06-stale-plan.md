# Drill 6 — A saved plan becomes stale

## Prerequisites

Clean exercise baseline, remote backend, no concurrent operation. Use only demo parameter values.

## Break

```powershell
terraform -chdir=infra/state-lab plan -var=marker=reviewed-value -out=reviewed.tfplan
terraform -chdir=infra/state-lab plan -var=marker=intervening-value -out=intervening.tfplan
terraform -chdir=infra/state-lab apply intervening.tfplan
terraform -chdir=infra/state-lab apply reviewed.tfplan
```

## Observe

The last command fails because state changed after the reviewed plan was created. Terraform protects the relationship between a plan and its state snapshot.

## Hint

The plan being valid when reviewed does not make it valid forever. A plan file is not a reusable deployment script.

## Recover

```powershell
terraform -chdir=infra/state-lab plan -var=marker=reviewed-value -out=fresh.tfplan
terraform -chdir=infra/state-lab show fresh.tfplan
terraform -chdir=infra/state-lab apply fresh.tfplan
```

Review the new plan before applying. Do not modify serial numbers, force state writes, or silently generate another plan inside an approved apply workflow. The GitHub helper also rejects plans older than 24 hours or from a different infrastructure commit/target.

## Reset

```powershell
terraform -chdir=infra/state-lab apply
terraform -chdir=infra/state-lab plan
Remove-Item -LiteralPath infra/state-lab/reviewed.tfplan,infra/state-lab/intervening.tfplan,infra/state-lab/fresh.tfplan
```

With baseline tfvars, this restores the parameter. Saved plan files can contain sensitive values; keep them out of source control.

## Checkpoint

Show the stale-plan failure, a separately reviewed successful plan, and a clean baseline.
