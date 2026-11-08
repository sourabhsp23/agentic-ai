# Shared, long-lived resources used by every deployment target (EC2, ECS, EKS):
#   - ECR repositories for the api and web images
#   - S3 bucket holding the datasets (sample data uploaded automatically)
#   - IAM policy the application runs with (Bedrock + S3, least privilege)
#   - GitHub Actions OIDC provider + CI role (no long-lived AWS keys in GitHub)

terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.80" }
  }
  # Lesson: move state to S3 so a team (and CI) can share it.
  # backend "s3" {
  #   bucket       = "my-tf-state-bucket"
  #   key          = "insightpilot/shared.tfstate"
  #   region       = "us-east-1"
  #   use_lockfile = true
  # }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = { Project = var.project, ManagedBy = "terraform", Stack = "shared" }
  }
}

data "aws_caller_identity" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  repo_root  = "${path.module}/../../.."
}

# ---------------------------------------------------------------- ECR
resource "aws_ecr_repository" "app" {
  for_each             = toset(["api", "web"])
  name                 = "${var.project}-${each.key}"
  image_tag_mutability = "MUTABLE" # CI pushes an immutable git-sha tag plus a moving "latest"
  force_delete         = true      # lets `terraform destroy` remove repos that still hold images

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "app" {
  for_each   = aws_ecr_repository.app
  repository = each.value.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep the 15 most recent images"
      selection    = { tagStatus = "any", countType = "imageCountMoreThan", countNumber = 15 }
      action       = { type = "expire" }
    }]
  })
}

# ---------------------------------------------------------------- S3 datasets
resource "aws_s3_bucket" "datasets" {
  bucket        = "${var.project}-datasets-${local.account_id}"
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "datasets" {
  bucket                  = aws_s3_bucket.datasets.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_object" "sample_data" {
  for_each = fileset("${local.repo_root}/sample_data", "**/*.csv")
  bucket   = aws_s3_bucket.datasets.id
  key      = "datasets/${each.value}"
  source   = "${local.repo_root}/sample_data/${each.value}"
  etag     = filemd5("${local.repo_root}/sample_data/${each.value}")
}

# ---------------------------------------------------------------- App policy
data "aws_iam_policy_document" "app" {
  statement {
    sid     = "InvokeBedrockModels"
    actions = ["bedrock:InvokeModel"]
    resources = concat(
      [for m in var.bedrock_profile_ids : "arn:aws:bedrock:${var.region}:${local.account_id}:inference-profile/${m}"],
      [for m in var.bedrock_profile_ids : "arn:aws:bedrock:*::foundation-model/${trimprefix(m, "us.")}"],
      ["arn:aws:bedrock:${var.region}::foundation-model/${var.embedding_model_id}"],
    )
  }
  statement {
    sid       = "ReadWriteDatasets"
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${aws_s3_bucket.datasets.arn}/datasets/*"]
  }
  statement {
    sid       = "ListDatasets"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.datasets.arn]
    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["datasets/*"]
    }
  }
}

resource "aws_iam_policy" "app" {
  name        = "${var.project}-app"
  description = "Runtime permissions for InsightPilot (Bedrock + datasets bucket)"
  policy      = data.aws_iam_policy_document.app.json
}

# ---------------------------------------------------------------- GitHub OIDC
resource "aws_iam_openid_connect_provider" "github" {
  count           = var.create_github_oidc_provider ? 1 : 0
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

locals {
  github_oidc_arn = var.create_github_oidc_provider ? aws_iam_openid_connect_provider.github[0].arn : "arn:aws:iam::${local.account_id}:oidc-provider/token.actions.githubusercontent.com"
}

data "aws_iam_policy_document" "ci_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [local.github_oidc_arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repo}:ref:refs/heads/main"]
    }
  }
}

resource "aws_iam_role" "ci" {
  name               = "${var.project}-github-ci"
  assume_role_policy = data.aws_iam_policy_document.ci_trust.json
}

data "aws_iam_policy_document" "ci" {
  statement {
    sid       = "EcrLogin"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }
  statement {
    sid = "EcrPush"
    actions = [
      "ecr:BatchCheckLayerAvailability", "ecr:BatchGetImage", "ecr:CompleteLayerUpload",
      "ecr:GetDownloadUrlForLayer", "ecr:InitiateLayerUpload", "ecr:PutImage", "ecr:UploadLayerPart",
    ]
    resources = [for r in aws_ecr_repository.app : r.arn]
  }
  # --- ECS deploys
  statement {
    sid       = "EcsTaskDefinitions"
    actions   = ["ecs:DescribeTaskDefinition", "ecs:RegisterTaskDefinition"]
    resources = ["*"]
  }
  statement {
    sid       = "EcsServices"
    actions   = ["ecs:UpdateService", "ecs:DescribeServices"]
    resources = ["arn:aws:ecs:${var.region}:${local.account_id}:service/${var.project}/*"]
  }
  statement {
    sid       = "PassEcsTaskRoles"
    actions   = ["iam:PassRole"]
    resources = ["arn:aws:iam::${local.account_id}:role/${var.project}-*"]
    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["ecs-tasks.amazonaws.com"]
    }
  }
  # --- EC2 deploys via SSM Run Command (no SSH)
  statement {
    sid       = "FindInstances"
    actions   = ["ec2:DescribeInstances"]
    resources = ["*"]
  }
  statement {
    sid       = "RunShellDocument"
    actions   = ["ssm:SendCommand"]
    resources = ["arn:aws:ssm:${var.region}::document/AWS-RunShellScript"]
  }
  statement {
    sid       = "OnlyProjectInstances"
    actions   = ["ssm:SendCommand"]
    resources = ["arn:aws:ec2:${var.region}:${local.account_id}:instance/*"]
    condition {
      test     = "StringEquals"
      variable = "aws:ResourceTag/Project"
      values   = [var.project]
    }
  }
  statement {
    sid       = "ReadCommandResults"
    actions   = ["ssm:GetCommandInvocation", "ssm:ListCommandInvocations"]
    resources = ["*"]
  }
  # --- EKS deploys (cluster RBAC is granted by an EKS access entry, see infra/eks/cluster.yaml)
  statement {
    sid       = "EksKubeconfig"
    actions   = ["eks:DescribeCluster"]
    resources = ["arn:aws:eks:${var.region}:${local.account_id}:cluster/${var.project}"]
  }
}

resource "aws_iam_role_policy" "ci" {
  name   = "deploy"
  role   = aws_iam_role.ci.id
  policy = data.aws_iam_policy_document.ci.json
}
