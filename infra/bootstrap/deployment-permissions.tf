locals {
  read_actions    = ["ec2:Describe*", "iam:GetRole", "iam:GetRolePolicy", "iam:GetInstanceProfile", "iam:ListRolePolicies", "iam:ListAttachedRolePolicies", "iam:ListInstanceProfilesForRole", "iam:ListRoleTags", "rds:DescribeDBInstances", "rds:DescribeDBParameterGroups", "rds:DescribeDBParameters", "rds:DescribeDBSubnetGroups", "rds:ListTagsForResource", "logs:DescribeLogGroups", "logs:ListTagsForResource", "secretsmanager:DescribeSecret"]
  network_actions = ["ec2:CreateVpc", "ec2:DeleteVpc", "ec2:ModifyVpcAttribute", "ec2:CreateSubnet", "ec2:DeleteSubnet", "ec2:ModifySubnetAttribute", "ec2:CreateInternetGateway", "ec2:DeleteInternetGateway", "ec2:AttachInternetGateway", "ec2:DetachInternetGateway", "ec2:CreateRouteTable", "ec2:DeleteRouteTable", "ec2:CreateRoute", "ec2:ReplaceRoute", "ec2:DeleteRoute", "ec2:AssociateRouteTable", "ec2:DisassociateRouteTable", "ec2:ReplaceRouteTableAssociation", "ec2:CreateSecurityGroup", "ec2:DeleteSecurityGroup", "ec2:AuthorizeSecurityGroupIngress", "ec2:AuthorizeSecurityGroupEgress", "ec2:RevokeSecurityGroupIngress", "ec2:RevokeSecurityGroupEgress", "ec2:CreateTags", "ec2:DeleteTags", "ec2:RunInstances", "ec2:TerminateInstances", "ec2:ModifyInstanceAttribute", "ec2:ModifyInstanceCreditSpecification"]
}
resource "aws_iam_role_policy" "read" {
  for_each = toset(["plan", "deploy"])
  role     = aws_iam_role.github[each.key].id
  policy   = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Action = local.read_actions, Resource = "*" }] })
}
resource "aws_iam_role_policy" "compute" {
  role = aws_iam_role.github["deploy"].id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = local.network_actions, Resource = "*", Condition = { StringEquals = { "aws:RequestedRegion" = var.aws_region } } },
    { Effect = "Allow", Action = ["ssm:SendCommand"], Resource = "arn:aws:ssm:${var.aws_region}::document/AWS-RunShellScript" },
    { Effect = "Allow", Action = ["ssm:SendCommand"], Resource = "arn:aws:ec2:${var.aws_region}:${local.account}:instance/*", Condition = { StringEquals = { "ssm:resourceTag/Project" = var.project_name } } },
    { Effect = "Allow", Action = ["ssm:GetCommandInvocation", "ssm:DescribeInstanceInformation"], Resource = "*" }
  ] })
}
resource "aws_iam_role_policy" "identity" {
  role = aws_iam_role.github["deploy"].id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["iam:CreateRole"], Resource = local.app_role, Condition = { StringEquals = { "iam:PermissionsBoundary" = aws_iam_policy.runtime_boundary.arn } } },
    { Effect = "Allow", Action = ["iam:DeleteRole", "iam:PutRolePolicy", "iam:DeleteRolePolicy", "iam:TagRole", "iam:UntagRole", "iam:UpdateAssumeRolePolicy"], Resource = local.app_role },
    { Effect = "Allow", Action = ["iam:AttachRolePolicy", "iam:DetachRolePolicy"], Resource = local.app_role, Condition = { ArnEquals = { "iam:PolicyARN" = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore" } } },
    { Effect = "Allow", Action = ["iam:PassRole"], Resource = local.app_role, Condition = { StringEquals = { "iam:PassedToService" = "ec2.amazonaws.com" } } },
    { Effect = "Allow", Action = ["iam:CreateInstanceProfile", "iam:DeleteInstanceProfile", "iam:AddRoleToInstanceProfile", "iam:RemoveRoleFromInstanceProfile", "iam:TagInstanceProfile", "iam:UntagInstanceProfile"], Resource = local.app_profile },
    { Effect = "Allow", Action = ["iam:CreateServiceLinkedRole"], Resource = "arn:aws:iam::${local.account}:role/aws-service-role/rds.amazonaws.com/AWSServiceRoleForRDS", Condition = { StringEquals = { "iam:AWSServiceName" = "rds.amazonaws.com" } } }
  ] })
}
resource "aws_iam_role_policy" "database" {
  role = aws_iam_role.github["deploy"].id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["rds:CreateDBInstance", "rds:DeleteDBInstance", "rds:ModifyDBInstance", "rds:CreateDBParameterGroup", "rds:DeleteDBParameterGroup", "rds:ModifyDBParameterGroup", "rds:CreateDBSubnetGroup", "rds:DeleteDBSubnetGroup", "rds:ModifyDBSubnetGroup", "rds:AddTagsToResource", "rds:RemoveTagsFromResource"], Resource = ["arn:aws:rds:${var.aws_region}:${local.account}:db:${local.prefix}-db", "arn:aws:rds:${var.aws_region}:${local.account}:pg:${local.prefix}-postgres17", "arn:aws:rds:${var.aws_region}:${local.account}:subgrp:${local.prefix}-database", "arn:aws:rds:${var.aws_region}:${local.account}:snapshot:${local.prefix}-*"] },
    { Effect = "Allow", Action = ["secretsmanager:CreateSecret", "secretsmanager:TagResource"], Resource = "arn:aws:secretsmanager:${var.aws_region}:${local.account}:secret:rds!db-*" },
    { Effect = "Allow", Action = ["kms:DescribeKey"], Resource = "arn:aws:kms:${var.aws_region}:${local.account}:key/*" },
    { Effect = "Allow", Action = ["logs:CreateLogGroup", "logs:DeleteLogGroup", "logs:PutRetentionPolicy", "logs:DeleteRetentionPolicy", "logs:TagResource", "logs:UntagResource"], Resource = ["arn:aws:logs:${var.aws_region}:${local.account}:log-group:/inventory-manager/dev/app*", "arn:aws:logs:${var.aws_region}:${local.account}:log-group:/aws/rds/instance/${local.prefix}-db/*"] }
  ] })
}
