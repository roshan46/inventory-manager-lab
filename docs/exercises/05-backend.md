# Drill 5 — Wrong backend key and workspace confusion

## Prerequisites

Remote exercise backend configured; confirm `$StateKey` has the `exercises/` prefix. Record `terraform workspace show` as `default` and keep the correct backend file untouched.

## Break

Point the root at a separate empty key without copying state:

```powershell
terraform -chdir=infra/state-lab init -reconfigure -backend-config=backend.s3.tfbackend "-backend-config=key=exercises/$LabId/wrong.tfstate"
terraform -chdir=infra/state-lab state list
terraform -chdir=infra/state-lab plan
```

## Observe

State appears empty; Terraform proposes creating the parameter even though AWS still has it. Do not apply and do not migrate the empty backend over the correct state.

## Hint

Verify account, region, bucket, key, and workspace before treating an empty state as lost data. `.terraform` remembers backend settings from the last init.

## Recover

```powershell
terraform -chdir=infra/state-lab init -reconfigure -backend-config=backend.s3.tfbackend
terraform -chdir=infra/state-lab plan
```

Expected: original address and clean plan return. Now demonstrate the workspace variation:

```powershell
terraform -chdir=infra/state-lab workspace new confusion
terraform -chdir=infra/state-lab plan
terraform -chdir=infra/state-lab workspace select default
```

A workspace selects a different state namespace. The fixture's resource name does not include workspace, so applying in `confusion` would collide with the existing parameter. Workspaces do not automatically isolate your AWS names or provide separate security boundaries.

## Reset

```powershell
terraform -chdir=infra/state-lab workspace delete confusion
terraform -chdir=infra/state-lab init -reconfigure -backend-config=backend.s3.tfbackend
terraform -chdir=infra/state-lab plan
```

Do not force-delete a nonempty workspace. If you accidentally applied there, stop and inventory both states and the AWS object before changing ownership.

## Checkpoint

Explain the difference between `-reconfigure` and `-migrate-state`, and why this lab uses separate root directories/keys with the default workspace for dev.
