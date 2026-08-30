variable "environment" {
  description = "Deployment environment name"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where database security group will be created"
  type        = string
}

variable "subnet_ids" {
  description = "Subnet IDs for database subnet group"
  type        = list(string)
}

variable "allocated_storage" {
  description = "Allocated storage in gigabytes"
  type        = number
  default     = 20
}

variable "instance_class" {
  description = "Database instance class"
  type        = string
  default     = "db.t4g.small"
}

variable "db_name" {
  description = "Name of the initial database"
  type        = string
  default     = "capstone"
}

variable "db_username" {
  description = "Master database username"
  type        = string
  default     = "postgres"
}

variable "db_password" {
  description = "Master database password"
  type        = string
  sensitive   = true
}
