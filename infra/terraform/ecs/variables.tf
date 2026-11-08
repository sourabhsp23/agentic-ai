variable "region" {
  type    = string
  default = "us-east-1"
}

variable "project" {
  type    = string
  default = "insightpilot"
}

variable "image_tag" {
  description = "Initial image tag. Later deploys come from CI (new task definition revisions)."
  type        = string
  default     = "latest"
}

variable "bedrock_model_id" {
  type    = string
  default = "us.amazon.nova-lite-v1:0"
}

variable "enable_rds" {
  description = "Create RDS Postgres (pgvector) for run history + RAG. false = SQLite inside the task (cheaper, not persistent)."
  type        = bool
  default     = true
}

variable "desired_count" {
  type    = number
  default = 1
}

variable "max_count" {
  type    = number
  default = 3
}
