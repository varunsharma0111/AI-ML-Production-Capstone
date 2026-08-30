# Development Infrastructure Environment
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
  vpc_cidr            = "10.10.0.0/16"
  public_subnet_cidrs = ["10.10.1.0/24", "10.10.2.0/24"]
  private_subnet_cidrs = ["10.10.10.0/24", "10.10.11.0/24"]
}

module "kubernetes_cluster" {
  source              = "../../modules/kubernetes_cluster"
  cluster_name        = "capstone-eks-dev"
  environment         = var.environment
  vpc_id              = module.vpc.vpc_id
  subnet_ids          = module.vpc.private_subnet_ids
  node_instance_types = ["t3.medium"]
  desired_nodes       = 1
  min_nodes           = 1
  max_nodes           = 3
}

module "database" {
  source            = "../../modules/database"
  environment       = var.environment
  vpc_id            = module.vpc.vpc_id
  subnet_ids        = module.vpc.private_subnet_ids
  allocated_storage = 20
  instance_class    = "db.t4g.small"
  db_password       = var.db_password
}
