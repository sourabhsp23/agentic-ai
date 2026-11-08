variable "region" {
  type    = string
  default = "us-east-1"
}

variable "project" {
  type    = string
  default = "insightpilot"
}

variable "github_repo" {
  description = "owner/repo allowed to assume the CI role"
  type        = string
  default     = "sourabhsp23/agentic-ai"
}

variable "create_github_oidc_provider" {
  description = "Set false if this AWS account already has the GitHub OIDC provider (only one is allowed per account)"
  type        = bool
  default     = true
}

variable "bedrock_profile_ids" {
  description = "Cross-region inference profiles the app may call"
  type        = list(string)
  default     = ["us.amazon.nova-lite-v1:0", "us.amazon.nova-micro-v1:0", "us.amazon.nova-pro-v1:0"]
}

variable "embedding_model_id" {
  type    = string
  default = "amazon.titan-embed-text-v2:0"
}
