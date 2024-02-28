# OpenTelemetry POC project

This project demonstrates the use of OpenTelemetry for instrumenting AWS Lambda and Amazon SQS to collect tracing data and metrics, which are forwarded to New Relic. The primary goal is to identify the best approach to instrumenting these services, providing deep insights into their interactions and real-time performance.

## List of Metrics and Traces

### Metrics:
* **SQS**:
    * `sqs_messages_received`: Number of messages received from SQS.
    * `sqs_messages_processed`: Number of messages processed from SQS.
* **Lambda**:
    * `incoming_requests`: Number of incoming requests to Lambda.
    * `successful_requests`: Number of successfully processed requests.
    * `failed_requests`: Number of failed requests.
    * `request_latency`: Processing time of a Lambda request.
    * `request_size`: Size of the incoming request to Lambda.
    * `response_size`: Size of the outgoing response from Lambda.
    * `dependencies_latency`: Latency of calls to external dependencies (e.g., DynamoDB, SQS).

### Traces:
* `Handle Lambda Event`: Tracing the main Lambda event handler.
* `Receive Messages from SQS`: Tracing the process of receiving messages from SQS.
* `Process Message`: Tracing the processing of each individual message.
* `Put Item to DynamoDB`: Tracing the saving of data to DynamoDB.
* `Delete Message from SQS`: Tracing the deletion of a message from SQS after processing.

## Configuration

You will need to specify the `NEWRELIC_API_KEY` (INGEST-LICENSE) for integration with New Relic. This key should be added as an environment variable in the Terraform configuration.
- `messages.sh`: Script for generating random messages and sending them to SQS.

This demo project serves as a foundation for understanding and implementing instrumentation using OpenTelemetry in AWS Lambda and SQS projects, with further integration with New Relic for monitoring and analysis.
