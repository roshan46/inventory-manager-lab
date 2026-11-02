mock_provider "aws" {
  mock_data "aws_caller_identity" {
    defaults = { account_id = "123456789012" }
  }
  mock_data "aws_ami" {
    defaults = { id = "ami-0123456789abcdef0" }
  }
  mock_resource "aws_db_instance" {
    defaults = { master_user_secret = [{ secret_arn = "arn:aws:secretsmanager:us-east-2:123456789012:secret:rds!db-demo", secret_status = "active", kms_key_id = "test" }] }
  }
}
variables {
  learner_cidr = "203.0.113.1/32"
  ami_id       = "ami-0123456789abcdef0"
}
run "foundation" {
  command = apply
  assert {
    condition     = !aws_db_instance.main.publicly_accessible && aws_db_instance.main.storage_encrypted && aws_db_instance.main.manage_master_user_password
    error_message = "Database must be private, encrypted, and use managed credentials."
  }
  assert {
    condition     = aws_vpc_security_group_ingress_rule.postgres.referenced_security_group_id == aws_security_group.app.id
    error_message = "PostgreSQL must accept only the application security group."
  }
  assert {
    condition     = aws_vpc_security_group_ingress_rule.app_http.cidr_ipv4 == "203.0.113.1/32"
    error_message = "HTTP must be learner-only."
  }
  assert {
    condition     = aws_instance.app.metadata_options[0].http_tokens == "required" && aws_instance.app.metadata_options[0].http_put_response_hop_limit == 2
    error_message = "Require IMDSv2 while permitting Docker credential retrieval."
  }
  assert {
    condition     = endswith(aws_iam_role.app.permissions_boundary, "inventory-manager-runtime-boundary")
    error_message = "The instance role must retain its permissions boundary."
  }
}
run "reject_public_ingress" {
  command = plan
  variables { learner_cidr = "0.0.0.0/0" }
  expect_failures = [var.learner_cidr]
}
