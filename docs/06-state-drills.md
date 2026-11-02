# 6 — Terraform state incident practice

## Prerequisites and isolation

Complete the fundamentals and migration lessons. Work only with the disposable `infra/state-lab` root and its `exercises/<lab-id>/terraform.tfstate` backend key. The app and bootstrap remain untouched. Use your local sandbox profile; GitHub roles intentionally cannot access exercise state. Disable any other process working on this exercise key before recovery.

Run commands from the project root unless told otherwise. In a PowerShell terminal, set these values to match your state-lab tfvars/backend:

```powershell
$LabId = 'alex-20261101'
$StateBucket = 'YOUR-REAL-STATE-BUCKET'
$StateKey = "exercises/$LabId/terraform.tfstate"
$ParameterName = "/inventory-state-lab/$LabId/marker"
$env:AWS_DEFAULT_REGION = 'us-east-2'
New-Item -ItemType Directory -Force .scratch | Out-Null
terraform -chdir=infra/state-lab workspace show
terraform -chdir=infra/state-lab state list
terraform -chdir=infra/state-lab plan
```

Expected: workspace `default`, one `aws_ssm_parameter.marker`, clean plan. **Stop if any key or address refers to bootstrap/dev.** Commands that remove state do not delete remote objects, and remote deletions do not remove Terraform configuration.

Before each drill, download a private baseline backup and record metadata without printing state contents:

```powershell
aws s3api get-object --bucket $StateBucket --key $StateKey .scratch/before.tfstate
$Before = Get-Content .scratch/before.tfstate -Raw | ConvertFrom-Json
$Before | Select-Object lineage,serial
```

State and plan files may contain secrets even when outputs are marked sensitive. Keep `.scratch` private and ignored. These fixtures use only demo strings.

## Exercises

| Drill | Failure | Recovery skill |
| --- | --- | --- |
| [1. Lock contention](exercises/01-locks.md) | Concurrent operation or abandoned lock | Identify owner before unlocking |
| [2. Drift](exercises/02-drift.md) | Someone changes AWS directly | Restore configuration or deliberately accept drift |
| [3. Import and forgotten state](exercises/03-import.md) | Existing object missing from state | Adopt without recreation |
| [4. Refactor](exercises/04-refactor.md) | Rename/module move proposes delete/create | Use moved blocks and preserve identity |
| [5. Backend confusion](exercises/05-backend.md) | Wrong key or workspace appears empty | Reconnect without duplicating infrastructure |
| [6. Stale saved plan](exercises/06-stale-plan.md) | State changes after review | Re-plan and review again |
| [7. Partial apply](exercises/07-partial-apply.md) | One resource fails after another succeeds | Reconcile partial progress |
| [8. Lost state](exercises/08-recovery.md) | Current state object deleted | Recover version, verify lineage/serial, reconcile |

## Checkpoint and cleanup

Complete drills in order, including each reset. Record the symptom, evidence, recovery, and final plan result. Never make `-lock=false`, `state push -force`, or manual JSON editing your default response.

At the end, review and apply an exercise destroy plan, then confirm the parameter is gone. Keep the backend and historical versions until you have finished studying recovery; they are not live infrastructure. See [operations](07-operations.md) for final cleanup.
