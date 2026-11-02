output "state_bucket" { value = aws_s3_bucket.storage["state"].id }
output "artifact_bucket" { value = aws_s3_bucket.storage["artifacts"].id }
output "ecr_repository" { value = aws_ecr_repository.app.repository_url }
output "github_roles" { value = { for k, v in aws_iam_role.github : k => v.arn } }
