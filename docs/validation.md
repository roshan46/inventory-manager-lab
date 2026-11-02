# Validation status

This file records implementation checks, not an AWS deployment claim.

## Local checks

Verified on November 1, 2026:

- **19 Python tests passed** with SQLite, covering inventory validation/history, concurrent deductions, idempotent initialization, runtime secret configuration, release identity, expired/mismatched manifests, tampered plans, and stale-state rejection without redeploying or silently re-planning.
- **9 application tests passed against PostgreSQL 17**, including concurrent deductions and persistence through schema initialization. The database was disposable and removed after testing.
- **All three Terraform roots validated** with AWS provider 6.71.0; **four mocked Terraform test runs passed** (two dev, one bootstrap, one state lab). These require no AWS credentials and create no AWS resources.
- Terraform recursive formatting check passed. Provider lockfiles were generated from the signed registry checksums.
- **Real Docker lifecycle smoke passed**, including image build, fresh startup, UID 10001, read-only root filesystem, product persistence after container recreation, database outage (readiness 503 while liveness stays 200), and recovery. Test containers and volumes were removed.
- **Actionlint 1.7.7 passed** for all five workflows. Pinned third-party action commits were verified against their upstream repositories.
- Local lesson links, eight exercise structures, YAML, and HCL parsed successfully.

Local Python tests used Python 3.14.6; the built Docker app ran Python 3.13.17. CI pins Python 3.13 and Terraform 1.16.1. Windows test temporary directories were placed under `.scratch` to avoid local temp-folder permissions; PostgreSQL host tests used explicit IPv4. No local AWS credentials were used to provision resources.

## Learner cloud acceptance

AWS provisioning, state incident execution against AWS, and hosted GitHub workflow runs require your sandbox account/repository and have not been executed during project creation.

Before calling your cloud setup complete, verify:

1. Bootstrap and exercise state migration retain identities and produce clean plans.
2. PR checks run without AWS credentials; main builds publish immutable ECR digests.
3. Manual deployment uses its reviewed plan; stale/wrong-operation plans are rejected.
4. EC2 is SSM-managed; the learner CIDR is the only app ingress; RDS is private and accepts only the app security group.
5. UI stock/history work and version matches the chosen image; logs arrive in CloudWatch.
6. A second release and manual rollback preserve inventory data.
7. Each state drill completes its recovery/reset, ending in a clean plan.
8. Destroy leaves dev/exercise states empty and actual resources removed; bootstrap is retained.
