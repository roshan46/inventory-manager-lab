# 4 — Deploy the inventory app to AWS

## Prerequisites and costs

Complete bootstrap and use the same sandbox account, `us-east-2`, and project name `inventory-manager`. Review current costs for EC2 t3.micro, public IPv4, RDS db.t3.micro with 20 GB storage, Secrets Manager, ECR, logs, and backups. These are not promised to be free. This stack has two public subnets and two isolated database subnets, one app instance, and one database instance. There is no NAT gateway.

## Prepare the application plan

```powershell
Copy-Item infra/dev/terraform.tfvars.example infra/dev/terraform.tfvars
Copy-Item infra/dev/backend.s3.tfbackend.example infra/dev/backend.s3.tfbackend
aws ssm get-parameter --region us-east-2 --name /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 --query Parameter.Value --output text
```

Pin the returned AMI in `terraform.tfvars`; the Terraform data source verifies Amazon ownership and the AL2023 x86_64 image family. Set `learner_cidr` to your current public IPv4 followed by `/32`. Set the backend bucket. PostgreSQL major version 17 is requested; RDS selects an available minor for initial creation. Record the resolved minor after deployment if you want a deliberately pinned upgrade exercise.

```powershell
terraform -chdir=infra/dev init -backend-config=backend.s3.tfbackend
terraform -chdir=infra/dev plan -out=dev.tfplan
terraform -chdir=infra/dev apply dev.tfplan
terraform -chdir=infra/dev output
```

Expected: private RDS, an EC2 public IP, a database hostname, a managed secret ARN, and a log group. The instance installs Docker and SSM but does not start the app until the image deployment. Database creation can take several minutes. The managed secret's **value** is never requested by Terraform.

## Build and deploy

Continue with [GitHub delivery](05-github.md) to build/push the image, then select it in a reviewed plan and deploy. A no-change infrastructure plan is valid when only the application release changes.

The deployment helper waits for SSM and cloud-init, logs into ECR, pulls by digest, initializes missing tables, starts a non-root read-only container, and tests readiness/version from the instance. Existing tables and inventory data are retained. The container retrieves the RDS secret at startup using its instance role and verifies the database's TLS certificate against the RDS CA bundle. IMDSv2 is required; hop limit 2 permits access from Docker's bridge network.

## Exercises, hints, and solutions

- **Trace network access:** why can EC2 reach RDS while your laptop cannot? **Hint:** inspect database route tables and ingress rules. **Solution:** database subnets have no internet default route; port 5432 accepts only the app security group.
- **Trace identity:** why does the container need no embedded AWS key? **Hint:** inspect the instance profile. **Solution:** the SDK obtains temporary credentials from IMDSv2; its inline policy permits only this database secret.
- **Inspect cloud-init:** if SSM is online but deployment fails, inspect `/var/log/cloud-init-output.log` through SSM. **Solution:** fix package/network errors, then rerun deployment after reviewing current state; do not open SSH to debug.

## Troubleshooting and checkpoint

If browser access fails but SSM smoke tests pass, check your current public IP against `learner_cidr`. If Docker cannot fetch credentials, check hop limit, instance profile, and metadata settings. If RDS returns authentication failures after rotation, restart through a new deployment so workers fetch fresh credentials. If the account has no RDS service-linked role, the deploy policy permits its creation.

Checkpoint: add a product through the EC2 URL and see `/version` match your chosen commit. App logs arrive in `/inventory-manager/dev/app`; RDS logs have seven-day retention. A replacement EC2 instance retains database data because RDS is separate. Cleanup is described in [operations](07-operations.md).
