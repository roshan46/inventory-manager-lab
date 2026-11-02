terraform {
  required_version = ">= 1.10, < 2.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
}
provider "aws" {
  region = var.aws_region
  default_tags { tags = { Project = var.project_name, Component = "bootstrap" } }
}
data "aws_caller_identity" "current" {}
locals {
  account     = data.aws_caller_identity.current.account_id
  prefix      = "${var.project_name}-dev"
  buckets     = { state = var.state_bucket_name, artifacts = var.artifact_bucket_name }
  state_key   = "dev/inventory-manager/terraform.tfstate"
  oidc        = var.existing_github_oidc_provider_arn != null ? var.existing_github_oidc_provider_arn : aws_iam_openid_connect_provider.github[0].arn
  app_role    = "arn:aws:iam::${local.account}:role/${var.project_name}/application/${local.prefix}-app"
  app_profile = "arn:aws:iam::${local.account}:instance-profile/${var.project_name}/application/${local.prefix}-app"
}
resource "aws_s3_bucket" "storage" {
  for_each      = local.buckets
  bucket        = each.value
  force_destroy = false
  lifecycle { prevent_destroy = true }
}
resource "aws_s3_bucket_public_access_block" "storage" {
  for_each                = local.buckets
  bucket                  = aws_s3_bucket.storage[each.key].id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_versioning" "storage" {
  for_each = local.buckets
  bucket   = aws_s3_bucket.storage[each.key].id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_server_side_encryption_configuration" "storage" {
  for_each = local.buckets
  bucket   = aws_s3_bucket.storage[each.key].id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}
resource "aws_s3_bucket_policy" "tls" {
  for_each = local.buckets
  bucket   = aws_s3_bucket.storage[each.key].id
  policy   = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Deny", Principal = "*", Action = "s3:*", Resource = [aws_s3_bucket.storage[each.key].arn, "${aws_s3_bucket.storage[each.key].arn}/*"], Condition = { Bool = { "aws:SecureTransport" = "false" } } }] })
}
resource "aws_ecr_repository" "app" {
  name                 = var.project_name
  image_tag_mutability = "IMMUTABLE"
  force_delete         = false
  image_scanning_configuration { scan_on_push = true }
  lifecycle { prevent_destroy = true }
}
resource "aws_iam_openid_connect_provider" "github" {
  count          = var.existing_github_oidc_provider_arn == null ? 1 : 0
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}
resource "aws_iam_role" "github" {
  for_each = toset(["build", "plan", "deploy"])
  name     = "${var.project_name}-github-${each.key}"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Action = "sts:AssumeRoleWithWebIdentity", Principal = { Federated = local.oidc }, Condition = { StringEquals = {
    "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
    "token.actions.githubusercontent.com:sub" = "repo:${var.github_repository}:ref:refs/heads/main"
  } } }] })
}
resource "aws_iam_role_policy" "state" {
  for_each = toset(["plan", "deploy"])
  role     = aws_iam_role.github[each.key].id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["s3:ListBucket"], Resource = aws_s3_bucket.storage["state"].arn },
    { Effect = "Allow", Action = each.key == "deploy" ? ["s3:GetObject", "s3:PutObject"] : ["s3:GetObject"], Resource = "${aws_s3_bucket.storage["state"].arn}/${local.state_key}" },
    { Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"], Resource = "${aws_s3_bucket.storage["state"].arn}/${local.state_key}.tflock" }
  ] })
}
resource "aws_iam_role_policy" "artifacts" {
  for_each = toset(["build", "plan", "deploy"])
  role     = aws_iam_role.github[each.key].id
  policy = jsonencode({ Version = "2012-10-17", Statement = concat(
    each.key == "build" ? [] : [{ Effect = "Allow", Action = ["s3:GetObject"], Resource = each.key == "plan" ? ["${aws_s3_bucket.storage["artifacts"].arn}/releases/*"] : ["${aws_s3_bucket.storage["artifacts"].arn}/releases/*", "${aws_s3_bucket.storage["artifacts"].arn}/plans/*", "${aws_s3_bucket.storage["artifacts"].arn}/successful/*"] }],
  [{ Effect = "Allow", Action = ["s3:PutObject"], Resource = "${aws_s3_bucket.storage["artifacts"].arn}/${each.key == "build" ? "releases" : each.key == "plan" ? "plans" : "successful"}/*" }]) })
}
resource "aws_iam_role_policy" "build" {
  role = aws_iam_role.github["build"].id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["ecr:GetAuthorizationToken"], Resource = "*" },
    { Effect = "Allow", Action = ["ecr:BatchGetImage", "ecr:DescribeImages", "ecr:BatchCheckLayerAvailability", "ecr:InitiateLayerUpload", "ecr:UploadLayerPart", "ecr:CompleteLayerUpload", "ecr:PutImage"], Resource = aws_ecr_repository.app.arn }
  ] })
}
# Limits what a deployment-created instance role can ever receive.
resource "aws_iam_policy" "runtime_boundary" {
  name = "${var.project_name}-runtime-boundary"
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["ssm:DescribeAssociation", "ssm:GetDeployablePatchSnapshotForInstance", "ssm:GetDocument", "ssm:DescribeDocument", "ssm:GetManifest", "ssm:ListAssociations", "ssm:ListInstanceAssociations", "ssm:PutInventory", "ssm:PutComplianceItems", "ssm:PutConfigurePackageResult", "ssm:UpdateAssociationStatus", "ssm:UpdateInstanceAssociationStatus", "ssm:UpdateInstanceInformation", "ssmmessages:CreateControlChannel", "ssmmessages:CreateDataChannel", "ssmmessages:OpenControlChannel", "ssmmessages:OpenDataChannel", "ec2messages:AcknowledgeMessage", "ec2messages:DeleteMessage", "ec2messages:FailMessage", "ec2messages:GetEndpoint", "ec2messages:GetMessages", "ec2messages:SendReply", "ecr:GetAuthorizationToken"], Resource = "*" },
    { Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = "arn:aws:secretsmanager:${var.aws_region}:${local.account}:secret:rds!db-*" },
    { Effect = "Allow", Action = ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer", "ecr:BatchCheckLayerAvailability"], Resource = aws_ecr_repository.app.arn },
    { Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"], Resource = "arn:aws:logs:${var.aws_region}:${local.account}:log-group:/inventory-manager/dev/app:*" }
  ] })
}
