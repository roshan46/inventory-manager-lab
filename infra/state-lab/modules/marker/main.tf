variable "lab_id" { type = string }
variable "marker" { type = string }
resource "aws_ssm_parameter" "this" {
  name  = "/inventory-state-lab/${var.lab_id}/marker"
  type  = "String"
  value = var.marker
  tags  = { Project = "inventory-state-lab", Exercise = "baseline" }
}
output "name" { value = aws_ssm_parameter.this.name }
