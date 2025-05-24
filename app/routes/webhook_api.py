"""
API routes for webhook queue management
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
import uuid
import json
import random
from .. import db

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

@router.get("/queue")
async def get_queue_items(status: str = None, date: str = None, limit: int = 50):
    """Get webhook queue items, optionally filtered by status and date"""
    try:
        print(f"API: Getting webhook queue items with status={status}, date={date}, limit={limit}")
        
        # Validate parameters
        valid_status = status if status and status != "all" else None
        valid_date = date if date and len(date) > 0 else None
        
        # Get items with validated filters
        items = db.get_webhook_queue_items(valid_status, valid_date, limit)
        print(f"API: Found {len(items)} webhook queue items")
        
        # For debugging, print the first item if available
        if items:
            print(f"API: First item: {items[0]}")
            return items
        else:
            print("API: No items found, returning empty list")
            return []
        
    except Exception as e:
        print(f"API Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/queue/{webhook_id}")
async def get_queue_item(webhook_id: str):
    """Get a specific webhook queue item by ID"""
    try:
        # Get all items and filter by ID
        # This is inefficient but works for our simple example
        items = db.get_webhook_queue_items()
        for item in items:
            if item['id'] == webhook_id:
                return item
        
        raise HTTPException(status_code=404, detail="Webhook not found")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/data/{webhook_id}")
async def get_webhook_data(webhook_id: str):
    """Get the raw data for a specific webhook"""
    try:
        # Get from webhook_queue table
        dynamodb = db.get_dynamodb_client()
        table = dynamodb.Table('webhook_queue')
        response = table.get_item(Key={'id': webhook_id})
        
        if 'Item' not in response:
            raise HTTPException(status_code=404, detail="Webhook data not found")
        
        # Return the item with raw_data field
        if 'raw_data' not in response['Item']:
            return {"id": webhook_id, "raw_data": {"message": "No raw data available"}}
        
        return {"id": webhook_id, "raw_data": response['Item']['raw_data']}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/queue/{webhook_id}/reprocess")
async def reprocess_webhook(webhook_id: str):
    """Mark a webhook for reprocessing"""
    try:
        # Get the webhook item first
        items = db.get_webhook_queue_items()
        webhook_item = None
        for item in items:
            if item['id'] == webhook_id:
                webhook_item = item
                break
        
        if not webhook_item:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        # Update status to pending for reprocessing
        success = db.update_webhook_status(webhook_id, 'pending')
        if success:
            return {"status": "success", "message": f"Webhook {webhook_id} marked for reprocessing"}
        else:
            raise HTTPException(status_code=500, detail="Failed to update webhook status")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_webhook_stats(date: str = None):
    """Get webhook queue statistics, optionally filtered by date"""
    try:
        stats = db.get_webhook_stats(date)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/load-samples")
async def load_sample_webhooks():
    """Load sample webhook data"""
    try:
        # Generate sample webhook data
        sample_data = []
        now = datetime.now()
        
        # Clear existing data first
        dynamodb = db.get_dynamodb_client()
        queue_table = dynamodb.Table('webhook_queue')
        
        # Check if table exists and create it if it doesn't
        existing_tables = [table.name for table in dynamodb.tables.all()]
        if 'webhook_queue' not in existing_tables:
            print("Creating webhook_queue table as it doesn't exist")
            queue_table = dynamodb.create_table(
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
            queue_table.meta.client.get_waiter('table_exists').wait(TableName='webhook_queue')
            print("webhook_queue table created successfully")
            queue_table = dynamodb.Table('webhook_queue')
        
        # Scan and delete existing items
        queue_items = queue_table.scan().get('Items', [])
        
        # Delete all items from webhook_queue
        with queue_table.batch_writer() as batch:
            for item in queue_items:
                batch.delete_item(Key={'id': item['id']})
        
        print(f"Cleared {len(queue_items)} existing webhook items")
        
        # Generate 20 sample webhooks
        for i in range(20):
            webhook_id = str(uuid.uuid4())
            
            # Use current date for all webhooks to ensure they show up
            date_str = now.strftime("%Y-%m-%d")
            
            # Random status
            status = random.choice(["pending", "processed", "error"])
            
            # Create sample email data similar to Postmark webhook
            email_data = {
                "Date": now.strftime("%a, %d %b %Y %H:%M:%S +0000"),
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
                "MessageID": f"message-{random.randint(10000, 99999)}",
                "Status": random.choice(["Delivered", "Bounced", "Opened", "Clicked"]),
                "TextBody": f"This is a sample webhook message body for {date_str}.",
                "HtmlBody": f"<html><body><p>This is a sample webhook message body for {date_str}.</p></body></html>",
                "Tag": random.choice(["welcome", "notification", "password-reset", "newsletter"]),
                "MessageStream": "outbound",
                "Attachments": [],
                "Headers": [{"Name": "X-Test-Header", "Value": "test-value"}]
            }
            
            # Create webhook queue item with raw data included
            webhook_item = {
                "id": webhook_id,
                "timestamp": now.isoformat(),
                "date": date_str,
                "status": status,
                "source": "sample",
                "raw_data": email_data  # Include raw data directly in the queue item
            }
            
            # Add processed_at if status is not pending
            if status != "pending":
                processed_time = now + timedelta(minutes=random.randint(1, 60))
                webhook_item["processed_at"] = processed_time.isoformat()
            
            # Add error message if status is error
            if status == "error":
                webhook_item["error_message"] = random.choice([
                    "Connection timeout",
                    "Invalid payload format",
                    "Authentication failed",
                    "Resource not found",
                    "Internal server error"
                ])
            
            sample_data.append(webhook_item)
            
            # Save to DynamoDB
            queue_table.put_item(Item=webhook_item)
            print(f"Created webhook item {i+1}: {webhook_id} with status {status}")
        
        # Verify data was added
        verification = queue_table.scan(Limit=5)
        items = verification.get('Items', [])
        if items:
            print(f"Verification: Found {len(items)} items in webhook_queue table")
            print(f"First item: {items[0]}")
        else:
            print("WARNING: No items found in webhook_queue table after adding sample data!")
        
        return {"status": "success", "message": f"Loaded {len(sample_data)} sample webhooks"}
    except Exception as e:
        print(f"Error loading sample webhooks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process")
async def process_webhooks():
    """Process pending webhooks"""
    try:
        # Get all pending webhooks
        dynamodb = db.get_dynamodb_client()
        table = dynamodb.Table('webhook_queue')
        
        response = table.scan(
            FilterExpression="#status = :status",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={":status": "pending"}
        )
        
        pending_webhooks = response.get('Items', [])
        
        # Process each webhook
        processed_count = 0
        for webhook in pending_webhooks:
            webhook_id = webhook['id']
            
            # Simulate processing (80% success, 20% error)
            if random.random() < 0.8:
                db.update_webhook_status(webhook_id, "processed")
            else:
                error_message = random.choice([
                    "Processing timeout",
                    "Invalid data format",
                    "Resource unavailable",
                    "Dependency failure"
                ])
                db.update_webhook_status(webhook_id, "error", error_message)
            
            processed_count += 1
        
        return {"status": "success", "message": f"Processed {processed_count} webhooks"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clear")
async def clear_webhooks():
    """Clear all webhook data"""
    try:
        dynamodb = db.get_dynamodb_client()
        queue_table = dynamodb.Table('webhook_queue')
        
        # Scan all items from the table
        queue_items = queue_table.scan().get('Items', [])
        
        # Delete all items from webhook_queue
        with queue_table.batch_writer() as batch:
            for item in queue_items:
                batch.delete_item(Key={'id': item['id']})
        
        return {"status": "success", "message": f"Cleared {len(queue_items)} webhooks"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))