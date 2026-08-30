output "db_endpoint" {
  description = "PostgreSQL DB Endpoint"
  value       = aws_db_instance.main.endpoint
}

output "db_host" {
  description = "PostgreSQL DB Address"
  value       = aws_db_instance.main.address
}

output "db_name" {
  description = "PostgreSQL Database Name"
  value       = aws_db_instance.main.db_name
}
