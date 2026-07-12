output "lambda_function_name" {
  description = "Name of the deployed Lambda function"
  value       = aws_lambda_function.cost_optimizer.function_name
}

output "lambda_function_arn" {
  description = "ARN of the deployed Lambda function"
  value       = aws_lambda_function.cost_optimizer.arn
}

output "api_gateway_url" {
  description = "API Gateway invoke URL (use this in future remote dashboard)"
  value       = "${aws_api_gateway_stage.prod.invoke_url}/optimize"
}

output "cloudwatch_log_group" {
  description = "CloudWatch Log Group for Lambda logs"
  value       = aws_cloudwatch_log_group.lambda_logs.name
}

output "iam_role_arn" {
  description = "IAM Role ARN for the Lambda execution role"
  value       = aws_iam_role.lambda_role.arn
}
