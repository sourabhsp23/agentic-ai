# Single EC2 host running the full stack with docker compose.
# Lessons: AMIs, security groups, instance profiles (no keys on the box), IMDSv2, user_data,
# and SSM Session Manager / Run Command instead of SSH.

terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.80" }
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = { Project = var.project, ManagedBy = "terraform", Stack = "ec2" }
  }
}

# --- Look up resources created by the shared stack
data "aws_ecr_repository" "api" { name = "${var.project}-api" }
data "aws_ecr_repository" "web" { name = "${var.project}-web" }
data "aws_iam_policy" "app" { name = "${var.project}-app" }
data "aws_caller_identity" "current" {}

# --- Network: the account's default VPC keeps this lesson simple
data "aws_vpc" "default" { default = true }

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  filter {
    name   = "default-for-az"
    values = ["true"]
  }
}

# Latest Amazon Linux 2023, resolved at plan time (never hard-code AMI IDs)
data "aws_ssm_parameter" "al2023" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

resource "aws_security_group" "app" {
  name        = "${var.project}-ec2"
  description = "HTTP in, everything out. No SSH: use SSM Session Manager."
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidrs
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# --- Instance profile: the app's AWS identity
data "aws_iam_policy_document" "ec2_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "app" {
  name               = "${var.project}-ec2"
  assume_role_policy = data.aws_iam_policy_document.ec2_trust.json
}

resource "aws_iam_role_policy_attachment" "app" {
  for_each = {
    app = data.aws_iam_policy.app.arn                                  # Bedrock + S3
    ssm = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"       # Session Manager + Run Command
    ecr = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly" # pull images
  }
  role       = aws_iam_role.app.name
  policy_arn = each.value
}

resource "aws_iam_instance_profile" "app" {
  name = "${var.project}-ec2"
  role = aws_iam_role.app.name
}

resource "aws_instance" "app" {
  ami                    = data.aws_ssm_parameter.al2023.value
  instance_type          = var.instance_type
  subnet_id              = data.aws_subnets.default.ids[0]
  vpc_security_group_ids = [aws_security_group.app.id]
  iam_instance_profile   = aws_iam_instance_profile.app.name

  user_data = templatefile("${path.module}/user_data.sh.tftpl", {
    compose_file     = file("${path.module}/../../ec2/docker-compose.prod.yml")
    api_image        = data.aws_ecr_repository.api.repository_url
    web_image        = data.aws_ecr_repository.web.repository_url
    region           = var.region
    bedrock_model_id = var.bedrock_model_id
    datasets_bucket  = "${var.project}-datasets-${data.aws_caller_identity.current.account_id}"
  })
  user_data_replace_on_change = true

  metadata_options {
    http_tokens                 = "required" # IMDSv2 only
    http_put_response_hop_limit = 2          # +1 hop so containers can reach IMDS for credentials
  }

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
    encrypted   = true
  }

  tags = { Name = "${var.project}-app" }
}
