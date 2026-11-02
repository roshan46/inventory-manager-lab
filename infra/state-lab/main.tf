terraform {
  required_version = ">= 1.10, < 2.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
  # Start local. Copy backend.tf.example only in the remote-state lesson.
}
provider "aws" {
  region = "us-east-2"
}
variable "lab_id" {
  type = string
  validation {
    condition     = can(regex("^[a-z0-9-]{3,24}$", var.lab_id))
    error_message = "Use a unique lowercase lab ID, 3-24 characters."
  }
}
variable "marker" {
  type    = string
  default = "baseline"
}
resource "aws_ssm_parameter" "marker" {
  name  = "/inventory-state-lab/${var.lab_id}/marker"
  type  = "String"
  value = var.marker
  tags  = { Project = "inventory-state-lab", Exercise = "baseline" }
}
output "parameter_name" { value = aws_ssm_parameter.marker.name }
