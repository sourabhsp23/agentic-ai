output "account_id" {
  value = local.account_id
}

output "ecr_registry" {
  value = split("/", aws_ecr_repository.app["api"].repository_url)[0]
}

output "ecr_api_repository" {
  value = aws_ecr_repository.app["api"].repository_url
}

output "ecr_web_repository" {
  value = aws_ecr_repository.app["web"].repository_url
}

output "datasets_bucket" {
  value = aws_s3_bucket.datasets.bucket
}

output "app_policy_arn" {
  value = aws_iam_policy.app.arn
}

output "ci_role_arn" {
  description = "Set as the GitHub repository variable AWS_ROLE_ARN"
  value       = aws_iam_role.ci.arn
}
