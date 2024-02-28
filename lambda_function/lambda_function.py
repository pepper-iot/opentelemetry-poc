import os
import boto3
import json
import logging
import time
import opentelemetry
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.metrics import MeterProvider

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NEWRELIC_API_KEY = os.environ['NEWRELIC_API_KEY']
DYNAMODB_TABLE_NAME = os.environ['DB_TABLE_NAME']
SQS_QUEUE_URL = os.environ['SQS_URL']

#OpenTelemetry tracing settings
resource = Resource(attributes={
    "service.name": "OTel-POC-project"
})

provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(OTLPSpanExporter(
        endpoint="https://otlp.nr-data.net:4317/v1/traces", # New Relicк tracer Endpoint
        headers={"api-key": NEWRELIC_API_KEY},    
))
provider.add_span_processor(processor)

trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

#OpenTelemetry metrics settings
metric_exporter = OTLPMetricExporter(
    endpoint="https://otlp.nr-data.net:4317/v1/metrics",  # New Relicк metrics Endpoint
    headers={"api-key": NEWRELIC_API_KEY}
    )
metric_reader = PeriodicExportingMetricReader(metric_exporter)
meter_provider = MeterProvider(metric_readers=[metric_reader], resource=resource)
metrics.set_meter_provider(meter_provider)

#Get Meter
meter = metrics.get_meter(__name__, "0.1")

#AWS resources initializasion
dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs') 

#Createing SQS metrics
sqs_messages_received_counter = meter.create_counter(
    name="sqs_messages_received",
    description="Number of SQS messages received",
    unit="1",
)

sqs_messages_processed_counter = meter.create_counter(
    name="sqs_messages_processed",
    description="Number of SQS messages processed",
    unit="1",
)
#Creating Lambda metrics
incoming_requests = meter.create_counter(
    name="incoming_requests",
    description="Count of incoming Lambda requests",
    unit="1",
)

successful_requests = meter.create_counter(
    name="successful_requests",
    description="Count of successful Lambda requests",
    unit="1",
)

failed_requests = meter.create_counter(
    name="failed_requests",
    description="Count of failed Lambda requests",
    unit="1",
)

request_latency = meter.create_histogram(
    name="request_latency",
    description="Latency of Lambda request processing",
    unit="ms",
)

request_size = meter.create_histogram(
    name="request_size",
    description="Size of Lambda request payloads",
    unit="bytes",
)

response_size = meter.create_histogram(
    name="response_size",
    description="Size of Lambda response payloads",
    unit="bytes",
)

dependencies_latency = meter.create_histogram(
    name="dependencies_latency",
    description="Latency of calls to dependencies from Lambda",
    unit="ms",
)

lambda_invocations_counter = meter.create_counter(
    name="aws.lambda.invocations",
    description="Number of AWS Lambda invocations",
    unit="1",
)

def lambda_handler(event, context):
    incoming_requests.add(1)
    lambda_invocations_counter.add(1)
    start_time = time.time()
    
    logger.info("Lambda handler started")
    with tracer.start_as_current_span("Handle Lambda Event") as span:
        logger.info("Starting 'Handle Lambda Event' span")
        try:
            messages = receive_messages_from_sqs()
            if messages:
                sqs_messages_received_counter.add(len(messages))
                for message in messages:
                    process_message(message)
                    message_size = len(json.dumps(message))
                    request_size.record(message_size)
                sqs_messages_processed_counter.add(len(messages)) 
                successful_requests.add(len(messages))
                
            else:
                print("No messages to process")
                logger.info("No messages to process")
                successful_requests.add(1)
            logger.info("Lambda handler finished")      
            
            span.set_attribute("aws.lambda.function_name", "ote-poc-v3")
        
        except Exception as e:
            failed_requests.add(1)
            raise e
            
        finally:
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000
            request_latency.record(latency_ms)
            dependencies_latency.record(latency_ms, {"dependency": "Lambda function"})

def receive_messages_from_sqs():
    start_time = time.time()
    logger.info("Starting to receive messages from SQS")
    with tracer.start_as_current_span("Receive Messages from SQS") as span:
        try:
            messages = sqs.receive_message(
                QueueUrl=SQS_QUEUE_URL,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=0
            )

            span.set_attribute("sqs.queue_url", SQS_QUEUE_URL)
            message_count = len(messages.get('Messages', []))
            span.set_attribute("sqs.message_count", message_count)
            logger.info(f"Received {message_count} messages from SQS")

            return messages.get('Messages', [])
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise
        finally:
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000
            dependencies_latency.record(latency_ms, {"dependency": "SQS"})
            logger.info("Finished processing message")            

def process_message(message):
    start_time = time.time()
    logger.info("Starting to process message")
    with tracer.start_as_current_span("Process Message") as span:
        try:
            data = json.loads(message['Body'])
            span.set_attribute("dynamodb.table_name", DYNAMODB_TABLE_NAME)
            
            # Saving data in  DynamoDB
            table = dynamodb.Table(DYNAMODB_TABLE_NAME)
            with tracer.start_as_current_span("Put Item to DynamoDB"):
                logger.info("Putting item to DynamoDB")
                table.put_item(Item=data)

            # Deleting messages from SQS
            with tracer.start_as_current_span("Delete Message from SQS"):
                logger.info("Deleting message from SQS")
                sqs.delete_message(
                    QueueUrl=SQS_QUEUE_URL,
                    ReceiptHandle=message['ReceiptHandle']
                )
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise
        finally:
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000
            dependencies_latency.record(latency_ms, {"dependency": "DynamoDB"})            
            logger.info("Finished processing message")
