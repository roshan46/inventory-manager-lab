mock_provider "aws" {
  mock_data "aws_caller_identity" {
    defaults = { account_id = "123456789012" }
  }
}
variables {
  state_bucket_name    = "inventory-state-test"
  artifact_bucket_name = "inventory-artifacts-test"
  github_repository    = "owner/repo"
}
run "bootstrap" {
  command = apply
  assert {
    condition     = alltrue([for config in aws_s3_bucket_versioning.storage : config.versioning_configuration[0].status == "Enabled"])
    error_message = "Both state and reviewed artifacts need versioning."
  }
  assert {
    condition     = alltrue([for config in aws_s3_bucket_public_access_block.storage : config.block_public_policy && config.restrict_public_buckets])
    error_message = "Bootstrap storage must be private."
  }
  assert {
    condition     = aws_ecr_repository.app.image_tag_mutability == "IMMUTABLE"
    error_message = "Release tags must be immutable."
  }
  assert {
    condition     = length(aws_iam_role.github) == 3 && strcontains(aws_iam_role.github["deploy"].assume_role_policy, "repo:owner/repo:ref:refs/heads/main")
    error_message = "Separate build/plan/deploy roles must be restricted to main."
  }
  assert {
    condition     = !strcontains(aws_iam_role_policy.artifacts["build"].policy, "s3:GetObject") && !contains(keys(aws_iam_role_policy.state), "build")
    error_message = "Image builds must not read saved plans or Terraform state."
  }
}

run "custom_oidc_subject" {
  command = plan
  variables {
    github_oidc_subject = "repo:owner@123/repo@456:ref:refs/heads/main"
  }
  assert {
    condition     = strcontains(aws_iam_role.github["build"].assume_role_policy, "repo:owner@123/repo@456:ref:refs/heads/main")
    error_message = "A configured custom GitHub OIDC subject must be used verbatim."
  }
}
