terraform {
  required_version = ">= 1.10, < 2.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
  backend "s3" {}
}
provider "aws" {
  region = var.aws_region
  default_tags {
    tags = { Project = var.project_name, Environment = "dev", ManagedBy = "Terraform" }
  }
}
locals {
  name_prefix = "${var.project_name}-dev"
}
data "aws_caller_identity" "current" {}
