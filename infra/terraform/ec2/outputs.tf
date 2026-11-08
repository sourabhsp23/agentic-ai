output "instance_id" {
  value = aws_instance.app.id
}

output "public_ip" {
  value = aws_instance.app.public_ip
}

output "url" {
  value = "http://${aws_instance.app.public_dns}"
}

output "shell" {
  description = "Open a shell on the box without SSH keys"
  value       = "aws ssm start-session --target ${aws_instance.app.id} --region ${var.region}"
}
