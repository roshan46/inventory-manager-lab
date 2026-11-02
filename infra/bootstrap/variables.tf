variable "aws_region" {
  type    = string
  default = "us-east-2"
}
variable "project_name" {
  type    = string
  default = "inventory-manager"
}
variable "state_bucket_name" { type = string }
variable "artifact_bucket_name" { type = string }
variable "github_repository" {
  type = string
  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repository))
    error_message = "Use OWNER/REPO."
  }
}
variable "existing_github_oidc_provider_arn" {
  type    = string
  default = null
}
