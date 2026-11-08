variable "region" {
  type    = string
  default = "us-east-1"
}

variable "project" {
  type    = string
  default = "insightpilot"
}

variable "instance_type" {
  description = "t3.micro is free-tier eligible on most accounts (1 GB RAM + 2 GB swap). t3.small is smoother."
  type        = string
  default     = "t3.micro"
}

variable "allowed_cidrs" {
  description = "Who may reach port 80. Use [\"<your-ip>/32\"] to keep the demo private."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "bedrock_model_id" {
  type    = string
  default = "us.amazon.nova-lite-v1:0"
}
