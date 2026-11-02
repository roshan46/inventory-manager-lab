data "aws_ami" "app" {
  owners = ["amazon"]
  filter {
    name   = "image-id"
    values = [var.ami_id]
  }
  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }
}
resource "aws_cloudwatch_log_group" "app" {
  name              = "/inventory-manager/dev/app"
  retention_in_days = 7
}
resource "aws_iam_role" "app" {
  name                 = "${local.name_prefix}-app"
  path                 = "/${var.project_name}/application/"
  permissions_boundary = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/${var.project_name}-runtime-boundary"
  assume_role_policy   = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Action = "sts:AssumeRole", Principal = { Service = "ec2.amazonaws.com" } }] })
}
resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.app.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}
resource "aws_iam_role_policy" "app" {
  name = "runtime"
  role = aws_iam_role.app.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = [aws_db_instance.main.master_user_secret[0].secret_arn] },
    { Effect = "Allow", Action = ["ecr:GetAuthorizationToken"], Resource = "*" },
    { Effect = "Allow", Action = ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer", "ecr:BatchCheckLayerAvailability"], Resource = "arn:aws:ecr:${var.aws_region}:${data.aws_caller_identity.current.account_id}:repository/${var.project_name}" },
    { Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"], Resource = "${aws_cloudwatch_log_group.app.arn}:*" }
  ] })
}
resource "aws_iam_instance_profile" "app" {
  name = "${local.name_prefix}-app"
  path = "/${var.project_name}/application/"
  role = aws_iam_role.app.name
}
resource "aws_instance" "app" {
  ami                         = data.aws_ami.app.id
  instance_type               = "t3.micro"
  subnet_id                   = aws_subnet.public["a"].id
  associate_public_ip_address = true
  vpc_security_group_ids      = [aws_security_group.app.id]
  iam_instance_profile        = aws_iam_instance_profile.app.name
  user_data                   = file("${path.module}/user-data.sh")
  user_data_replace_on_change = true
  metadata_options {
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
  }
  root_block_device {
    encrypted   = true
    volume_size = 20
    volume_type = "gp3"
  }
  credit_specification {
    cpu_credits = "standard"
  }
  tags       = { Name = "${local.name_prefix}-app" }
  depends_on = [aws_route.internet, aws_route_table_association.public, aws_vpc_security_group_egress_rule.app_web, aws_iam_role_policy_attachment.ssm]
}
