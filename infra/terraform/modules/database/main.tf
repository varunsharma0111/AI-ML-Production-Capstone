# Managed PostgreSQL Database Module
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

resource "aws_db_subnet_group" "main" {
  name       = "capstone-db-subnet-group-${var.environment}"
  subnet_ids = var.subnet_ids

  tags = {
    Name        = "capstone-db-subnet-group-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_security_group" "db" {
  name        = "capstone-db-sg-${var.environment}"
  description = "Restrict access to PostgreSQL database port 5432"
  vpc_id      = var.vpc_id

  ingress {
    description = "Allow PostgreSQL access from within VPC subnets"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "capstone-db-sg-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_db_instance" "main" {
  identifier             = "capstone-db-${var.environment}"
  engine                 = "postgres"
  engine_version         = "16"
  instance_class         = var.instance_class
  allocated_storage      = var.allocated_storage
  storage_type           = "gp3"
  storage_encrypted      = true
  db_name                = var.db_name
  username               = var.db_username
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]
  skip_final_snapshot    = var.environment == "development" ? true : false

  tags = {
    Name        = "capstone-db-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
