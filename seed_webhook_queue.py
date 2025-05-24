#!/usr/bin/env python3
"""
Script to seed sample data for the webhook queue dashboard.
"""

import os
import uuid
from datetime import datetime, timedelta
import random
import json
import boto3

# Set AWS environment variables for DynamoDB Local
os.environ["AWS_ENDPOINT_URL"] = "http://localhost:8001"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "fakeAccessKeyId"
os.environ["AWS_SECRET_ACCESS_KEY"] = "fakeSecretAccessKey"

# Connect to DynamoDB
dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url=os.environ.get("AWS_ENDPOINT_URL"),
    region_name=os.environ.get("AWS_DEFAULT_REGION"),
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY")
)

def seed_webhook_data():
    """Seed sample webhook data for the queue dashboard"""
    # Check if table exists
    existing_tables = [table.name for table in dynamodb.tables.all()]
    if 'webhook_queue' not in existing_tables:
        print("Creating webhook_queue table...")
        webhook_queue = dynamodb.create_table(
            TableName='webhook_queue',
            KeySchema=[
                {'AttributeName': 'id', 'KeyType': 'HASH'},
            ],
            AttributeDefinitions=[
                {'AttributeName': 'id', 'AttributeType': 'S'},
                {'AttributeName': 'status', 'AttributeType': 'S'},
                {'AttributeName': 'timestamp', 'AttributeType': 'S'},
                {'AttributeName': 'date', 'AttributeType': 'S'},
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'status-timestamp-index',
                    'KeySchema': [
                        {'AttributeName': 'status', 'KeyType': 'HASH'},
                        {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                },
                {
                    'IndexName': 'date-index',
                    'KeySchema': [
                        {'AttributeName': 'date', 'KeyType': 'HASH'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                }
            ],
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        # Wait for table to be created
        webhook_queue.meta.client.get_waiter('table_exists').wait(TableName='webhook_queue')
        print("webhook_queue table created successfully")
    else:
        webhook_queue = dynamodb.Table('webhook_queue')
    
    # Check if data already exists
    if webhook_queue.scan(Limit=1)['Items']:
        print("Data already exists in webhook_queue table. Clearing existing data...")
        scan = webhook_queue.scan()
        with webhook_queue.batch_writer() as batch:
            for item in scan['Items']:
                batch.delete_item(Key={'id': item['id']})
    
    # Generate sample webhook data
    now = datetime.now()
    statuses = ["pending", "processed", "error"]
    status_weights = [0.2, 0.6, 0.2]  # 20% pending, 60% processed, 20% error
    
    # Generate data for the last 7 days
    sample_data = []
    for day in range(7):
        # Generate different number of webhooks for each day
        num_webhooks = random.randint(5, 15)
        
        for _ in range(num_webhooks):
            webhook_id = str(uuid.uuid4())
            
            # Generate a random timestamp for this day
            random_hours = random.randint(0, 23)
            random_minutes = random.randint(0, 59)
            timestamp = now - timedelta(days=day, hours=random_hours, minutes=random_minutes)
            timestamp_iso = timestamp.isoformat()
            date_str = timestamp.strftime("%Y-%m-%d")
            
            # Determine status based on weights
            status = random.choices(statuses, weights=status_weights)[0]
            
            # Create sample email data similar to Postmark webhook
            email_data = {
                "Date": timestamp.strftime("%a, %d %b %Y %H:%M:%S +0000"),
                "From": f"sender{random.randint(1, 100)}@example.com",
                "FromName": f"Sender {random.randint(1, 100)}",
                "To": f"recipient{random.randint(1, 100)}@example.com",
                "Subject": random.choice([
                    "System notification",
                    "Critical alert detected",
                    "High CPU usage warning",
                    "Database backup completed",
                    "Security alert",
                    "Scheduled maintenance"
                ]),
                "MessageID": f"message-{webhook_id[:8]}",
                "TextBody": f"This is a sample webhook message body for {date_str}.",
                "HtmlBody": f"<html><body><p>This is a sample webhook message body for {date_str}.</p></body></html>",
                "Tag": random.choice(["alert", "notification", "system", "security"]),
                "MessageStream": "outbound",
                "Attachments": [],
                "Headers": [{"Name": "X-Test-Header", "Value": "test-value"}]
            }
            
            # Create webhook queue item with raw data included
            queue_item = {
                "id": webhook_id,
                "timestamp": timestamp_iso,
                "date": date_str,
                "status": status,
                "source": "postmark",
                "processed_at": timestamp_iso if status != "pending" else None,
                "raw_data": email_data  # Include raw data directly in the queue item
            }
            
            # Add error message for error status
            if status == "error":
                queue_item["error_message"] = random.choice([
                    "Invalid payload format",
                    "Missing required fields",
                    "Processing timeout",
                    "Database connection error"
                ])
            
            sample_data.append(queue_item)
    
    # Insert data into table
    print(f"Inserting {len(sample_data)} sample webhook items...")
    
    with webhook_queue.batch_writer() as batch:
        for item in sample_data:
            batch.put_item(Item=item)
    
    print("Sample webhook data inserted successfully")

if __name__ == "__main__":
    seed_webhook_data()
    print("Done! You can now view the webhook queue dashboard at http://localhost:8000/queue")