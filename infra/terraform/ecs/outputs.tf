output "url" {
  value = "http://${aws_lb.main.dns_name}"
}

output "cluster" {
  value = aws_ecs_cluster.main.name
}

output "service" {
  value = aws_ecs_service.app.name
}

output "log_group" {
  value = aws_cloudwatch_log_group.app.name
}

output "tail_logs" {
  value = "aws logs tail ${aws_cloudwatch_log_group.app.name} --follow --region ${var.region}"
}
