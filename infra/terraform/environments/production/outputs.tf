output "cluster_endpoint" {
  description = "Production EKS Cluster Endpoint"
  value       = module.kubernetes_cluster.cluster_endpoint
}

output "db_endpoint" {
  description = "Production PostgreSQL Endpoint"
  value       = module.database.db_endpoint
}
