# Production Infrastructure Environment
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

module "vpc" {
  source              = "../../modules/vpc"
  environment         = var.environment
  vpc_cidr            = "10.30.0.0/16"
  public_subnet_cidrs = ["10.30.1.0/24", "10.30.2.0/24", "10.30.3.0/24"]
  private_subnet_cidrs = ["10.30.10.0/24", "10.30.11.0/24", "10.30.12.0/24"]
  availability_zones  = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

module "kubernetes_cluster" {
  source              = "../../modules/kubernetes_cluster"
  cluster_name        = "capstone-eks-prod"
  environment         = var.environment
  vpc_id              = module.vpc.vpc_id
  subnet_ids          = module.vpc.private_subnet_ids
  node_instance_types = ["t3.large", "m5.large"]
  desired_nodes       = 3
  min_nodes           = 3
  max_nodes           = 10
}

module "database" {
  source            = "../../modules/database"
  environment       = var.environment
  vpc_id            = module.vpc.vpc_id
  subnet_ids        = module.vpc.private_subnet_ids
  allocated_storage = 100
  instance_class    = "db.m6g.large"
  db_password       = var.db_password
}
