# Drill 8 — Recover a deleted state object

## Prerequisites

Complete all resets. The exercise state must contain only your marker parameter and use `exercises/<lab-id>/terraform.tfstate`. Stop all Terraform operations for this key. Confirm S3 versioning is enabled and take a fresh baseline backup using the shared setup. Record its lineage and serial. Never run this drill against bootstrap/dev or a shared environment.

## Break

Record the current object version, then add a delete marker by deleting **only the current exercise object**:

```powershell
$VersionId = aws s3api head-object --bucket $StateBucket --key $StateKey --query VersionId --output text
aws s3api delete-object --bucket $StateBucket --key $StateKey
terraform -chdir=infra/state-lab plan
```

## Observe

Terraform sees no current state and proposes recreating an object that still exists. Do not apply. AWS S3 retains older versions because versioning is enabled. Deleting state did not delete the parameter.

## Hint

Recover the most recent known-good state, not an arbitrary old file. A newer serial or different lineage is a reason to investigate, not to force an overwrite.

## Recover

```powershell
aws s3api list-object-versions --bucket $StateBucket --prefix $StateKey
aws s3api get-object --bucket $StateBucket --key $StateKey --version-id $VersionId .scratch/recovered.tfstate
$Recovered = Get-Content .scratch/recovered.tfstate -Raw | ConvertFrom-Json
$Before = Get-Content .scratch/before.tfstate -Raw | ConvertFrom-Json
if ($Recovered.lineage -ne $Before.lineage -or $Recovered.serial -ne $Before.serial) { throw 'Backup identity mismatch: investigate, do not push' }
Get-FileHash .scratch/before.tfstate,.scratch/recovered.tfstate
aws ssm get-parameter --name $ParameterName --query Parameter.Value --output text
$RecoveryPath = (Resolve-Path .scratch/recovered.tfstate).Path
terraform -chdir=infra/state-lab state push $RecoveryPath
terraform -chdir=infra/state-lab state list
terraform -chdir=infra/state-lab plan -refresh-only
terraform -chdir=infra/state-lab plan
```

Before the push, verify the two hashes match, the version is the exact pre-delete version, no operation has written new state since deletion, and the AWS parameter identity/value still match. `state push` uses backend locking and normal serial/lineage protections. Do not use `-force`. If Terraform rejects the push, stop and inspect both states; never bypass safeguards merely to finish the drill.

The refresh-only plan compares state to actual remote objects. The normal plan also compares configuration. Investigate unexpected differences; do not blindly apply a recovered old view of the world. Recovery repairs bookkeeping only: it does **not** recreate deleted infrastructure or restore database rows.

## Reset

The successful recovery is the reset: one marker address and a clean normal plan. Keep the private backups until satisfied, then remove only the exercise backup files. Historical S3 versions/delete markers can remain for learning and later deliberate storage cleanup.

## Checkpoint

Record version ID, lineage, serial, matching hashes, remote-object verification, and the final no-change plan. Explain how you would stop concurrent writers before attempting this in a real incident.
