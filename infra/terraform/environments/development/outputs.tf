output "cluster_endpoint" {
  description = "Development EKS Cluster Endpoint"
  value       = module.kubernetes_cluster.cluster_endpoint
}

output "db_endpoint" {
  description = "Development PostgreSQL Endpoint"
  value       = module.database.db_endpoint
}
