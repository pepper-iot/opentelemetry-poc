provider "aws" {
  region = "us-east-1"
  access_key = var.access_key
  secret_key = var.secret_key 
}

resource "aws_iam_role" "otel_poc_lambda_role" {
  name = "otel_poc_lambda_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      },
    ]
  })
}

resource "aws_iam_policy" "otel_poc_policy" {
  name        = "otel_poc_policy"
  path        = "/"
  description = "Policy that grants full access to Lambda, DynamoDB, and SQS"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:*",
          "dynamodb:*",
          "sqs:*"
        ]
        Resource = "*"
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "my_policy_attachment" {
  role       = aws_iam_role.otel_poc_lambda_role.name
  policy_arn = aws_iam_policy.otel_poc_policy.arn
}

data "archive_file" "lambdas_code" {
 type        = "zip"
 output_path = "./lambda_function.zip"
 source_dir  = "./lambda_function/"
}

resource "aws_lambda_layer_version" "otel_lambda_layer" {
  filename   = "./layer/python.zip"
  layer_name = "otel_lambda_layer"

  compatible_runtimes = ["python3.12"]
}
  

resource "aws_lambda_function" "otel_poc-proj" {
 function_name = "otel_poc-proj"
 filename         = data.archive_file.lambdas_code.output_path
 role    = aws_iam_role.otel_poc_lambda_role.arn
 layers = [aws_lambda_layer_version.otel_lambda_layer.arn]
 handler = "lambda_function.lambda_handler"
 runtime = "python3.12"
 timeout = 600
  environment {
   variables = {
     SQS_URL = aws_sqs_queue.otel_poc_sqs.id
     DB_TABLE_NAME = aws_dynamodb_table.otel_poc_table.name
     NEWRELIC_API_KEY = var.newrelic_api_key
         
   }
 }
}

##SQS
resource "aws_sqs_queue" "otel_poc_sqs" {
 name = "otel_poc-proj-queue"
}

##DynamoDB
resource "aws_dynamodb_table" "otel_poc_table" {
 name           = "otel_poc_proj-table"
 billing_mode   = "PAY_PER_REQUEST"
# read_capacity  = 20
# write_capacity = 20
 hash_key       = "id"
 attribute {
   name = "id"
   type = "N"
 }
}

