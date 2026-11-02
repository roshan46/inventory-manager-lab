# Drill 1 — Lock contention and abandoned ownership

## Prerequisites

Use the [state-drill setup](../06-state-drills.md), remote exercise backend, and two terminals in the project root. Both terminals use the same AWS profile. No app/dev commands belong here.

## Break

```powershell
Copy-Item infra/state-lab/hold.tf.example infra/state-lab/hold.tf
terraform -chdir=infra/state-lab apply
```

Approve the one `terraform_data.hold` addition in terminal A. While its provisioner sleeps 90 seconds, run in terminal B:

```powershell
terraform -chdir=infra/state-lab plan -lock-timeout=5s
```

## Observe

Terminal B fails to acquire the lock and reports lock ID, owner, operation, and creation time. The lock protects bookkeeping, not the AWS service itself. Let terminal A finish normally first; terminal B can then plan.

## Hint

A failed lock acquisition is usually evidence another operation is doing its job. It is not evidence of a broken lock.

## Recover

Normal case: wait for A, then retry B. For an optional abandoned-lock simulation, first reset/remove the hold fixture and apply, copy it again, and repeat. In a dedicated third terminal, identify **the exact Terraform process running the exercise apply**, then force-stop only that PID while it sleeps. This may leave a lock; if it does not, report that cleanup succeeded rather than manufacturing a lock file.

Confirm the owner process is gone, its child sleeper has finished, no CI run is active, and the lock is for the exercise key. Only then use the lock ID reported by a fresh failed plan:

```powershell
terraform -chdir=infra/state-lab force-unlock LOCK-ID-FROM-ERROR
terraform -chdir=infra/state-lab plan
```

Read and answer the unlock prompt after checking the ID. Never unlock terminal A while it is alive. An interrupted operation may already have changed resources; inspect the fresh plan and state before applying again.

## Reset

```powershell
Remove-Item -LiteralPath infra/state-lab/hold.tf
terraform -chdir=infra/state-lab apply
terraform -chdir=infra/state-lab plan
```

Approve removal of the local bookkeeping resource only. The marker parameter stays.

## Checkpoint

Explain the lock owner evidence and why `-lock=false` would bypass coordination. Finish with one marker address and no changes.
