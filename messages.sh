#!/bin/bash

# URL of the SQS queue
QUEUE_URL="https://sqs.us-east-1.amazonaws.com/329295018884/otel_poc-proj-queue"
# random message generation
generate_random_message() {
    local id=$((RANDOM % 1000 + 1))
    local name="Item$((RANDOM % 900 + 100))"
    local value=$((RANDOM % 100 + 1))

    echo "{\"id\": $id, \"name\": \"$name\", \"value\": $value}"
}

# Sending random message to SQS
for i in {1..60}; do
    message=$(generate_random_message)
    echo "Sending message: $message"
    AWS_ACCESS_KEY_ID=YOUR_KEY_ID AWS_SECRET_ACCESS_KEY=YOUR_KEY  aws sqs send-message --queue-url "$QUEUE_URL" --message-body "$message"
done
