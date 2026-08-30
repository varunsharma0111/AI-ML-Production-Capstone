variable "aws_region" {
  description = "AWS region for staging deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment identifier"
  type        = string
  default     = "staging"
}

variable "db_password" {
  description = "Master database password"
  type        = string
  sensitive   = true
}
