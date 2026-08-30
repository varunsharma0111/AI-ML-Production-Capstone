output "cluster_endpoint" {
  description = "Staging EKS Cluster Endpoint"
  value       = module.kubernetes_cluster.cluster_endpoint
}

output "db_endpoint" {
  description = "Staging PostgreSQL Endpoint"
  value       = module.database.db_endpoint
}
