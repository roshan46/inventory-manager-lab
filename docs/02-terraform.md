# 2 — Terraform fundamentals

## Prerequisites

Install Terraform and AWS CLI v2; authenticate to a sandbox AWS account using your normal local profile/SSO. Never put access keys in `.tf` or `.tfvars`. The disposable state lab creates a standard SSM String parameter, not the application stack. Review AWS pricing and use demo strings only.

```powershell
aws sts get-caller-identity
Copy-Item infra/state-lab/terraform.tfvars.example infra/state-lab/terraform.tfvars
```

Edit `lab_id` to a unique lowercase ID such as `alex-20261101`. Use that ID consistently in later lessons. Keep this terminal's AWS profile and region stable.

## The first lifecycle

```powershell
terraform -chdir=infra/state-lab init
terraform -chdir=infra/state-lab fmt -check
terraform -chdir=infra/state-lab validate
terraform -chdir=infra/state-lab plan -out=first.tfplan
terraform -chdir=infra/state-lab show first.tfplan
terraform -chdir=infra/state-lab apply first.tfplan
terraform -chdir=infra/state-lab output
terraform -chdir=infra/state-lab state list
terraform -chdir=infra/state-lab plan
```

Expected: one parameter created, its address in state, then no changes. `init` installs the provider and configures the backend. `validate` checks configuration shape; it cannot prove that your AWS permissions or chosen AMI work. `plan` compares configuration, state, and remote objects. Applying a saved plan executes those reviewed changes; modifying configuration afterward does not rewrite that plan.

The provider speaks the AWS API. `aws_ssm_parameter.marker` is a Terraform resource address; its `/inventory-state-lab/...` name is its AWS identity. Variables supply inputs, outputs expose useful results, and references create dependency edges. State maps addresses to real objects. It is not a database backup.

## Exercises, hints, and solutions

1. Set `marker = "second"` in the state lab's tfvars. Predict the plan. **Hint:** only the parameter value changed. **Solution:** Terraform proposes an in-place update. Apply it, then restore `marker = "baseline"` and apply again.
2. Read `infra/dev/network.tf`. Trace the reference from a subnet to its VPC. **Hint:** resource order in the file is irrelevant. **Solution:** the `vpc_id` expression creates the dependency.
3. Inspect `.terraform.lock.hcl`. **Hint:** it is different from the state lock. **Solution:** it records provider selections and checksums; commit it. Never commit `.terraform/`, state, saved plans, real tfvars, or credentials. Use `init -upgrade` only as a reviewed upgrade.
4. Read `infra/state-lab/modules/marker/main.tf`. **Hint:** a module is a reusable configuration, not automatically separate state. **Solution:** a module's resources belong to the calling root's state. The refactoring drill later moves the address without replacing the parameter.

## Troubleshooting and checkpoint

For missing credentials, run `aws sts get-caller-identity` and refresh SSO. For a name collision, choose a unique lab ID before applying; do not adopt an unknown parameter. For a changed backend error, stop and read the migration lesson rather than adding arbitrary init flags.

Explain the difference between configuration, a saved plan, provider lockfile, backend lock, and state. Keep the parameter for the remote-state lesson, or reset with:

```powershell
terraform -chdir=infra/state-lab plan -destroy -out=cleanup.tfplan
terraform -chdir=infra/state-lab apply cleanup.tfplan
```
