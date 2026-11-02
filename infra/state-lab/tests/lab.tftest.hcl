mock_provider "aws" {}
variables { lab_id = "test-learner" }
run "isolation" {
  command = plan
  assert {
    condition     = aws_ssm_parameter.marker.name == "/inventory-state-lab/test-learner/marker" && aws_ssm_parameter.marker.type == "String"
    error_message = "Drills must use an isolated parameter with no secret data."
  }
}
