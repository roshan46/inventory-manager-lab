# Drill 4 — Rename and move into a module

## Prerequisites

Use the exercise root with a clean baseline and backup. Make a private copy of `infra/state-lab/main.tf` in `.scratch/main-before-refactor.tf` for reset. Do not copy it into the same root with a `.tf` suffix.

## Break

Rename `resource "aws_ssm_parameter" "marker"` to `resource "aws_ssm_parameter" "renamed"` in the root, and update the output reference to `aws_ssm_parameter.renamed.name`. Run a plan, but **do not apply**.

## Observe

Terraform sees the old address removed and a new address added. The unchanged AWS name is not enough to infer your refactor.

## Hint

A `moved` block explicitly connects old and new addresses while preserving the remote identity.

## Recover

Add this block, plan, and apply only after confirming zero create/destroy actions:

```hcl
moved {
  from = aws_ssm_parameter.marker
  to   = aws_ssm_parameter.renamed
}
```

Next remove the root parameter resource and replace it with the supplied module:

```hcl
module "marker" {
  source = "./modules/marker"
  lab_id = var.lab_id
  marker = var.marker
}
moved {
  from = aws_ssm_parameter.renamed
  to   = module.marker.aws_ssm_parameter.this
}
```

Retain the first moved block as migration history; update the output to `module.marker.name`. Run `terraform -chdir=infra/state-lab init` to load the module, then plan/apply. Expected: address movement only, with the same AWS parameter name/value.

## Reset

Restore the original main file from `.scratch`. Before applying, move the state address back to match it:

```powershell
Copy-Item .scratch/main-before-refactor.tf infra/state-lab/main.tf
terraform -chdir=infra/state-lab state mv 'module.marker.aws_ssm_parameter.this' aws_ssm_parameter.marker
terraform -chdir=infra/state-lab plan
```

If you stopped after only the rename stage, use `aws_ssm_parameter.renamed` as the source instead. Remove any separate temporary `.tf` file containing moved blocks. This reverse state command is a lab reset; real shared refactors should retain migration history until all consumers have upgraded.

## Checkpoint

Show zero resource replacement, the before/after state addresses, and a clean baseline after reset.
