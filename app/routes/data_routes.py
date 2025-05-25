"""
API routes for sample data management
"""

from fastapi import APIRouter, HTTPException
import logging
import boto3
import os
import sys
from pathlib import Path
import uuid
from datetime import datetime, timedelta
import random

# Add the parent directory to sys.path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import seed_data functions
from app.seed_data import generate_sample_data

router = APIRouter(prefix="/api/data", tags=["data"])
logger = logging.getLogger(__name__)

# Connect to DynamoDB
dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url=os.environ.get("AWS_ENDPOINT_URL", "http://localhost:8001"),
    region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", "fakeAccessKeyId"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", "fakeSecretAccessKey")
)

@router.post("/seed/alerts")
async def seed_alert_data():
    """Seed sample alert data"""
    try:
        table = dynamodb.Table('alerts')
        
        # Clear existing data
        scan = table.scan()
        with table.batch_writer() as batch:
            for item in scan['Items']:
                batch.delete_item(Key={'id': item['id']})
        
        # Generate and insert new data
        alerts = generate_sample_data()
        
        with table.batch_writer() as batch:
            for alert in alerts:
                batch.put_item(Item=alert)
        
        return {
            "status": "success",
            "message": f"Inserted {len(alerts)} sample alerts",
            "count": len(alerts)
        }
    except Exception as e:
        logger.error(f"Error seeding alert data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clear/alerts")
async def clear_alert_data():
    """Clear all alert data"""
    try:
        table = dynamodb.Table('alerts')
        
        # Count items before clearing
        count = table.scan(Select='COUNT')['Count']
        
        # Clear existing data
        scan = table.scan()
        with table.batch_writer() as batch:
            for item in scan['Items']:
                batch.delete_item(Key={'id': item['id']})
        
        return {
            "status": "success",
            "message": f"Cleared {count} alerts",
            "count": count
        }
    except Exception as e:
        logger.error(f"Error clearing alert data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/seed/webhooks")
async def seed_webhook_data():
    """Seed sample webhook data"""
    try:
        webhook_queue = dynamodb.Table('webhook_queue')
        postmark_data = dynamodb.Table('postmark_data')
        
        # Clear existing data
        for table in [webhook_queue, postmark_data]:
            scan = table.scan()
            with table.batch_writer() as batch:
                for item in scan['Items']:
                    batch.delete_item(Key={'id': item['id']})
        
        # Generate sample webhook data
        now = datetime.now()
        statuses = ["pending", "processed", "error"]
        status_weights = [0.4, 0.4, 0.2]  # 40% pending, 40% processed, 20% error
        
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
        for queue_item, postmark_item in sample_data:
            webhook_queue.put_item(Item=queue_item)
            postmark_data.put_item(Item=postmark_item)
        
        return {
            "status": "success",
            "message": f"Inserted {len(sample_data)} sample webhooks",
            "count": len(sample_data)
        }
    except Exception as e:
        logger.error(f"Error seeding webhook data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clear/webhooks")
async def clear_webhook_data():
    """Clear all webhook data"""
    try:
        webhook_queue = dynamodb.Table('webhook_queue')
        postmark_data = dynamodb.Table('postmark_data')
        
        # Count items before clearing
        queue_count = webhook_queue.scan(Select='COUNT')['Count']
        data_count = postmark_data.scan(Select='COUNT')['Count']
        
        # Clear existing data
        for table in [webhook_queue, postmark_data]:
            scan = table.scan()
            with table.batch_writer() as batch:
                for item in scan['Items']:
                    batch.delete_item(Key={'id': item['id']})
        
        return {
            "status": "success",
            "message": f"Cleared {queue_count} webhook queue items and {data_count} postmark data items",
            "queue_count": queue_count,
            "data_count": data_count
        }
    except Exception as e:
        logger.error(f"Error clearing webhook data: {e}")
        raise HTTPException(status_code=500, detail=str(e))