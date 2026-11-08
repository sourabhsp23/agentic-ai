# ECS Fargate deployment:
#   Internet -> ALB :80 -> task [ web (nginx :80) -> api (FastAPI :8000) ] -> RDS Postgres + Bedrock + S3
#
# web and api run as two containers in ONE task (sidecar pattern), so nginx reaches the API on
# localhost. Tasks sit in public subnets with public IPs, which avoids a NAT gateway (~$32/month);
# the security group only accepts traffic from the ALB.

terraform {
  required_version = ">= 1.6"
  required_providers {
    aws    = { source = "hashicorp/aws", version = "~> 5.80" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = { Project = var.project, ManagedBy = "terraform", Stack = "ecs" }
  }
}

data "aws_caller_identity" "current" {}
data "aws_availability_zones" "available" { state = "available" }
data "aws_ecr_repository" "api" { name = "${var.project}-api" }
data "aws_ecr_repository" "web" { name = "${var.project}-web" }
data "aws_iam_policy" "app" { name = "${var.project}-app" }

locals {
  azs             = slice(data.aws_availability_zones.available.names, 0, 2)
  datasets_bucket = "${var.project}-datasets-${data.aws_caller_identity.current.account_id}"
}

# ================================================================ Network
resource "aws_vpc" "main" {
  cidr_block           = "10.20.0.0/16"
  enable_dns_hostnames = true
  tags                 = { Name = var.project }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
}

resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index)
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = true
  tags                    = { Name = "${var.project}-public-${local.azs[count.index]}" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
}

resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# ================================================================ Security groups
resource "aws_security_group" "alb" {
  name   = "${var.project}-alb"
  vpc_id = aws_vpc.main.id
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "tasks" {
  name   = "${var.project}-tasks"
  vpc_id = aws_vpc.main.id
  ingress {
    description     = "Only the load balancer may reach the tasks"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "db" {
  count  = var.enable_rds ? 1 : 0
  name   = "${var.project}-db"
  vpc_id = aws_vpc.main.id
  ingress {
    description     = "Postgres from tasks only"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.tasks.id]
  }
}

# ================================================================ Load balancer
resource "aws_lb" "main" {
  name               = var.project
  load_balancer_type = "application"
  subnets            = aws_subnet.public[*].id
  security_groups    = [aws_security_group.alb.id]
}

resource "aws_lb_target_group" "web" {
  name                 = "${var.project}-web"
  port                 = 80
  protocol             = "HTTP"
  target_type          = "ip" # required for Fargate (awsvpc networking)
  vpc_id               = aws_vpc.main.id
  deregistration_delay = 15
  health_check {
    path                = "/nginx-health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 15
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web.arn
  }
}

# ================================================================ Database (optional)
resource "random_password" "db" {
  count   = var.enable_rds ? 1 : 0
  length  = 32
  special = false # keeps the connection URL free of characters that need escaping
}

resource "aws_db_subnet_group" "main" {
  count      = var.enable_rds ? 1 : 0
  name       = var.project
  subnet_ids = aws_subnet.public[*].id
}

resource "aws_db_instance" "main" {
  count                   = var.enable_rds ? 1 : 0
  identifier              = var.project
  engine                  = "postgres"
  engine_version          = "16"
  instance_class          = "db.t4g.micro"
  allocated_storage       = 20
  storage_type            = "gp3"
  storage_encrypted       = true
  db_name                 = "insightpilot"
  username                = "insightpilot"
  password                = random_password.db[0].result
  db_subnet_group_name    = aws_db_subnet_group.main[0].name
  vpc_security_group_ids  = [aws_security_group.db[0].id]
  publicly_accessible     = false
  backup_retention_period = 1
  skip_final_snapshot     = true # practice environment: destroy without a snapshot
  deletion_protection     = false
  apply_immediately       = true
}

resource "aws_secretsmanager_secret" "database_url" {
  count                   = var.enable_rds ? 1 : 0
  name                    = "${var.project}/database-url"
  recovery_window_in_days = 0 # allow immediate re-create after destroy
}

resource "aws_secretsmanager_secret_version" "database_url" {
  count         = var.enable_rds ? 1 : 0
  secret_id     = aws_secretsmanager_secret.database_url[0].id
  secret_string = "postgresql+psycopg://insightpilot:${random_password.db[0].result}@${aws_db_instance.main[0].endpoint}/insightpilot"
}

# ================================================================ IAM
data "aws_iam_policy_document" "ecs_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

# Execution role: used by the ECS agent to pull images, write logs and read secrets.
resource "aws_iam_role" "execution" {
  name               = "${var.project}-ecs-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_trust.json
}

resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "execution_secrets" {
  count = var.enable_rds ? 1 : 0
  name  = "read-database-url"
  role  = aws_iam_role.execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "secretsmanager:GetSecretValue"
      Resource = aws_secretsmanager_secret.database_url[0].arn
    }]
  })
}

# Task role: the application's own identity (Bedrock + S3).
resource "aws_iam_role" "task" {
  name               = "${var.project}-ecs-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_trust.json
}

resource "aws_iam_role_policy_attachment" "task" {
  role       = aws_iam_role.task.name
  policy_arn = data.aws_iam_policy.app.arn
}

# ================================================================ ECS
resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${var.project}"
  retention_in_days = 7
}

resource "aws_ecs_cluster" "main" {
  name = var.project
}

locals {
  log_config = {
    logDriver = "awslogs"
    options = {
      awslogs-group         = aws_cloudwatch_log_group.app.name
      awslogs-region        = var.region
      awslogs-stream-prefix = "app"
    }
  }

  api_environment = concat(
    [
      { name = "LLM_PROVIDER", value = "bedrock" },
      { name = "EMBEDDING_PROVIDER", value = "bedrock" },
      { name = "AWS_REGION", value = var.region },
      { name = "BEDROCK_MODEL_ID", value = var.bedrock_model_id },
      { name = "STORAGE_BACKEND", value = "s3" },
      { name = "S3_BUCKET", value = local.datasets_bucket },
    ],
    # Without RDS the API falls back to SQLite inside the task (history resets on redeploy).
    var.enable_rds ? [] : [{ name = "DATABASE_URL", value = "sqlite:////tmp/insightpilot.db" }],
  )

  api_secrets = var.enable_rds ? [
    { name = "DATABASE_URL", valueFrom = aws_secretsmanager_secret.database_url[0].arn }
  ] : []
}

resource "aws_ecs_task_definition" "app" {
  family                   = var.project
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([
    {
      name         = "api"
      image        = "${data.aws_ecr_repository.api.repository_url}:${var.image_tag}"
      essential    = true
      portMappings = [{ containerPort = 8000 }]
      environment  = local.api_environment
      secrets      = local.api_secrets
      healthCheck = {
        command     = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/readyz')\""]
        interval    = 15
        timeout     = 5
        retries     = 3
        startPeriod = 40
      }
      logConfiguration = local.log_config
    },
    {
      name             = "web"
      image            = "${data.aws_ecr_repository.web.repository_url}:${var.image_tag}"
      essential        = true
      portMappings     = [{ containerPort = 80 }]
      environment      = [{ name = "API_UPSTREAM", value = "http://localhost:8000" }]
      dependsOn        = [{ containerName = "api", condition = "HEALTHY" }]
      logConfiguration = local.log_config
    },
  ])
}

resource "aws_ecs_service" "app" {
  name                              = var.project
  cluster                           = aws_ecs_cluster.main.id
  task_definition                   = aws_ecs_task_definition.app.arn
  desired_count                     = var.desired_count
  launch_type                       = "FARGATE"
  health_check_grace_period_seconds = 90

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.tasks.id]
    assign_public_ip = true # reach ECR, Bedrock and S3 without a NAT gateway
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.web.arn
    container_name   = "web"
    container_port   = 80
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true # failed deploys roll back automatically
  }

  # CI registers new task definition revisions; autoscaling owns desired_count.
  lifecycle {
    ignore_changes = [task_definition, desired_count]
  }

  depends_on = [aws_lb_listener.http]
}

# ================================================================ Autoscaling
resource "aws_appautoscaling_target" "app" {
  service_namespace  = "ecs"
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.app.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  min_capacity       = var.desired_count
  max_capacity       = var.max_count
}

resource "aws_appautoscaling_policy" "cpu" {
  name               = "cpu-target-60"
  service_namespace  = aws_appautoscaling_target.app.service_namespace
  resource_id        = aws_appautoscaling_target.app.resource_id
  scalable_dimension = aws_appautoscaling_target.app.scalable_dimension
  policy_type        = "TargetTrackingScaling"
  target_tracking_scaling_policy_configuration {
    target_value       = 60
    scale_in_cooldown  = 120
    scale_out_cooldown = 60
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
  }
}
