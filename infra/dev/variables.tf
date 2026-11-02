variable "aws_region" {
  type    = string
  default = "us-east-2"
}
variable "project_name" {
  type    = string
  default = "inventory-manager"
}
variable "learner_cidr" {
  type = string
  validation {
    condition     = can(cidrnetmask(var.learner_cidr)) && can(regex("/32$", var.learner_cidr))
    error_message = "Use your public IPv4 address with /32."
  }
}
variable "ami_id" {
  type        = string
  description = "Pinned Amazon Linux 2023 x86_64 AMI in aws_region."
}
variable "availability_zones" {
  type    = list(string)
  default = ["us-east-2a", "us-east-2b"]
  validation {
    condition     = length(var.availability_zones) == 2 && length(distinct(var.availability_zones)) == 2
    error_message = "Provide two distinct availability zones."
  }
}
variable "db_engine_version" {
  type    = string
  default = "17"
}
variable "db_instance_class" {
  type    = string
  default = "db.t3.micro"
}
variable "db_skip_final_snapshot" {
  type    = bool
  default = true
}
variable "db_final_snapshot_identifier" {
  type    = string
  default = null
  validation {
    condition     = var.db_final_snapshot_identifier == null ? true : startswith(var.db_final_snapshot_identifier, "${var.project_name}-dev-")
    error_message = "Use a unique snapshot name starting with the project's dev prefix to match deployment IAM permissions."
  }
}
