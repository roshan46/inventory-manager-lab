output "instance_id" { value = aws_instance.app.id }
output "app_url" { value = "http://${aws_instance.app.public_ip}:8000" }
output "db_host" { value = aws_db_instance.main.address }
output "db_secret_arn" { value = aws_db_instance.main.master_user_secret[0].secret_arn }
output "log_group" { value = aws_cloudwatch_log_group.app.name }
