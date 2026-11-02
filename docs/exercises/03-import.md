# Drill 3 — Import an existing object and recover forgotten state

## Prerequisites

Use the exercise root and baseline backup. Confirm the parameter name belongs to your lab ID.

## Break

First practice genuine adoption: review and apply a destroy plan for this disposable parameter, then create the same object with AWS CLI:

```powershell
terraform -chdir=infra/state-lab plan -destroy -out=adoption.tfplan
terraform -chdir=infra/state-lab apply adoption.tfplan
aws ssm put-parameter --name $ParameterName --type String --value baseline
terraform -chdir=infra/state-lab plan
```

## Observe

Terraform proposes creation because its state is empty, even though AWS already has the object. Applying would collide with the existing name. Do not delete the object just to silence the collision.

## Hint

The resource address and AWS identity are different things. Import links them; it does not generate a complete desired configuration.

## Recover

```powershell
terraform -chdir=infra/state-lab import aws_ssm_parameter.marker $ParameterName
terraform -chdir=infra/state-lab plan
terraform -chdir=infra/state-lab apply
```

Expected: import succeeds; the first plan may add the configured tags. Review/apply that reconciliation, then see no changes.

Now simulate accidental forgetting without deleting AWS data:

```powershell
terraform -chdir=infra/state-lab state rm aws_ssm_parameter.marker
aws ssm get-parameter --name $ParameterName --query Parameter.Value --output text
terraform -chdir=infra/state-lab plan
terraform -chdir=infra/state-lab import aws_ssm_parameter.marker $ParameterName
```

Expected: the AWS parameter remains, Terraform initially proposes creation, and import repairs the mapping. A declarative `import` block is an alternative for code-reviewed adoption; remove it once the migration is no longer needed.

## Reset

Ensure `marker = "baseline"`; apply any tag/value reconciliation. Finish with one address and a clean plan. Never remove/re-import resources from the application or bootstrap root for this drill.

## Checkpoint

Explain why `state rm` did not destroy anything and why import still needs a normal plan afterward.
