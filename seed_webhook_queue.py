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
    # Check if tables exist
    existing_tables = [table.name for table in dynamodb.tables.all()]
    if 'webhook_queue' not in existing_tables or 'postmark_data' not in existing_tables:
        print("Required tables don't exist. Please run the main app first to create them.")
        return
    
    webhook_queue = dynamodb.Table('webhook_queue')
    postmark_data = dynamodb.Table('postmark_data')
    
    # Check if data already exists
    if webhook_queue.scan(Limit=1)['Items']:
        print("Data already exists in webhook_queue table. Clearing existing data...")
        scan = webhook_queue.scan()
        with webhook_queue.batch_writer() as batch:
            for item in scan['Items']:
                batch.delete_item(Key={'id': item['id']})
    
    if postmark_data.scan(Limit=1)['Items']:
        print("Data already exists in postmark_data table. Clearing existing data...")
        scan = postmark_data.scan()
        with postmark_data.batch_writer() as batch:
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
            
            # Create webhook queue item
            queue_item = {
                "id": webhook_id,
                "timestamp": timestamp_iso,
                "date": date_str,
                "status": status,
                "source": "postmark",
                "processed_at": timestamp_iso if status != "pending" else None
            }
            
            # Add error message for error status
            if status == "error":
                queue_item["error_message"] = random.choice([
                    "Invalid payload format",
                    "Missing required fields",
                    "Processing timeout",
                    "Database connection error"
                ])
            
            # Create postmark data item with sample payload
            payload = {
                "MessageID": f"message-{webhook_id[:8]}",
                "Subject": random.choice([
                    "System notification",
                    "Critical alert detected",
                    "High CPU usage warning",
                    "Database backup completed",
                    "Security alert",
                    "Scheduled maintenance"
                ]),
                "MessageStream": "outbound",
                "Tag": random.choice(["alert", "notification", "system", "security"]),
                "ServerID": random.randint(1000, 9999)
            }
            
            postmark_item = {
                "id": webhook_id,
                "timestamp": timestamp_iso,
                "date": date_str,
                "raw_data": payload
            }
            
            sample_data.append((queue_item, postmark_item))
    
    # Insert data into tables
    print(f"Inserting {len(sample_data)} sample webhook items...")
    
    for queue_item, postmark_item in sample_data:
        webhook_queue.put_item(Item=queue_item)
        postmark_data.put_item(Item=postmark_item)
    
    print("Sample webhook data inserted successfully")

if __name__ == "__main__":
    seed_webhook_data()
    print("Done! You can now view the webhook queue dashboard at http://localhost:8000/queue")