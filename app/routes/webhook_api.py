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
        
        # Check if alerts table exists and create if needed
        if 'alerts' not in existing_tables:
            print("Creating alerts table as it doesn't exist")
            alerts_table = dynamodb.create_table(
                TableName='alerts',
                KeySchema=[
                    {'AttributeName': 'id', 'KeyType': 'HASH'},
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'id', 'AttributeType': 'S'},
                    {'AttributeName': 'account_id', 'AttributeType': 'S'},
                    {'AttributeName': 'service', 'AttributeType': 'S'},
                    {'AttributeName': 'resource_id', 'AttributeType': 'S'},
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'account-service-index',
                        'KeySchema': [
                            {'AttributeName': 'account_id', 'KeyType': 'HASH'},
                            {'AttributeName': 'service', 'KeyType': 'RANGE'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                    },
                    {
                        'IndexName': 'resource-index',
                        'KeySchema': [
                            {'AttributeName': 'resource_id', 'KeyType': 'HASH'},
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                    }
                ],
                ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
            )
            # Wait for table to be created
            alerts_table.meta.client.get_waiter('table_exists').wait(TableName='alerts')
            print("alerts table created successfully")
        else:
            alerts_table = dynamodb.Table('alerts')
            
        # Clear existing alerts
        alert_items = alerts_table.scan().get('Items', [])
        with alerts_table.batch_writer() as batch:
            for item in alert_items:
                batch.delete_item(Key={'id': item['id']})
        
        print(f"Cleared {len(alert_items)} existing alert items")
        
        # Generate 20 sample webhooks
        for i in range(20):
            webhook_id = str(uuid.uuid4())
            
            # Use current date for all webhooks to ensure they show up
            date_str = now.strftime("%Y-%m-%d")
            
            # All sample webhooks should be pending for processing
            status = "pending"
            
            # Create AWS SNS-like message
            accounts = ["123456789012", "987654321098", "456789012345"]
            account_id = random.choice(accounts)
            
            aws_services = ["EC2", "RDS", "S3", "Lambda", "CloudWatch"]
            service = random.choice(aws_services)
            
            alert_types = {
                "EC2": ["CPU", "Memory", "Disk", "Network"],
                "RDS": ["CPU", "Memory", "Storage", "IOPS", "Connections"],
                "S3": ["Storage", "Access", "Replication"],
                "Lambda": ["Error", "Timeout", "Throttle", "Memory"],
                "CloudWatch": ["Alarm", "Event", "Log"]
            }
            
            alert_type = random.choice(alert_types.get(service, ["Alert"]))
            severity_levels = ["medium", "high", "critical"]
            severity = random.choice(severity_levels)
            
            regions = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]
            region = random.choice(regions)
            
            # Create AWS SNS-like message
            subject = f"AWS {service} {alert_type} {severity.upper()} Alert"
            
            # Generate resource ID based on service
            resource_id = ""
            if service == "EC2":
                resource_id = f"i-{uuid.uuid4().hex[:8]}"
            elif service == "RDS":
                resource_id = f"db-instance-{uuid.uuid4().hex[:8]}"
            elif service == "S3":
                resource_id = f"my-bucket-{uuid.uuid4().hex[:8]}"
            elif service == "Lambda":
                resource_id = f"function-{uuid.uuid4().hex[:8]}"
            else:
                resource_id = f"resource-{uuid.uuid4().hex[:8]}"
            
            # Create message body
            message_body = {
                "Type": "Notification",
                "MessageId": f"message-{uuid.uuid4().hex}",
                "TopicArn": f"arn:aws:sns:{region}:{account_id}:aws-alerts",
                "Subject": subject,
                "Message": f"AWS {service} resource {resource_id} has a {severity} {alert_type} alert. Please investigate immediately.",
                "Timestamp": now.isoformat(),
                "SignatureVersion": "1",
                "Signature": "EXAMPLE",
                "SigningCertURL": "EXAMPLE",
                "UnsubscribeURL": "EXAMPLE",
                "MessageAttributes": {
                    "Service": {"Type": "String", "Value": service},
                    "ResourceId": {"Type": "String", "Value": resource_id},
                    "AlertType": {"Type": "String", "Value": alert_type},
                    "Severity": {"Type": "String", "Value": severity},
                    "Region": {"Type": "String", "Value": region},
                    "AccountId": {"Type": "String", "Value": account_id}
                }
            }
            
            # Create webhook queue item with raw data included
            webhook_item = {
                "id": webhook_id,
                "timestamp": now.isoformat(),
                "date": date_str,
                "status": status,
                "source": "sample",
                "raw_data": message_body
            }
            
            sample_data.append(webhook_item)
            
            # Save to DynamoDB
            queue_table.put_item(Item=webhook_item)
            
            # Create corresponding alert directly (matching the format in seed_data.py)
            alert_id = str(uuid.uuid4())
            alert_item = {
                "id": alert_id,
                "account_id": account_id,
                "service": service,
                "resource_id": resource_id,
                "alert_type": alert_type,
                "severity": severity,
                "timestamp": now.isoformat(),
                "message": f"{severity.capitalize()} {alert_type} alert for {service} resource {resource_id}",
                "region": region,
                "webhook_id": webhook_id,  # Reference to the webhook queue item
                "remediation": db.get_remediation_action(service, alert_type, severity)
            }
            
            # Save alert directly to alerts table
            alerts_table.put_item(Item=alert_item)
            
            # Update webhook status to processed
            queue_table.update_item(
                Key={"id": webhook_id},
                UpdateExpression="SET #status = :status, processed_at = :processed_at, alert_id = :alert_id",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":status": "processed",
                    ":processed_at": now.isoformat(),
                    ":alert_id": alert_id
                }
            )
            
            print(f"Created webhook item {i+1}: {webhook_id} with status 'processed' and alert {alert_id}")
        
        return {"status": "success", "message": f"Loaded {len(sample_data)} sample webhooks and created matching alerts"}
    except Exception as e:
        print(f"Error loading sample webhooks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process")
async def process_webhooks():
    """Process pending webhooks"""
    try:
        # Import the webhook processor
        from ..webhook_processor import process_pending_webhooks
        
        # Process all pending webhooks
        result = process_pending_webhooks()
        
        # Return the results
        return {
            "status": "success", 
            "message": f"Processed {result['processed']} webhooks, discarded {result['discarded']}, errors: {result['error']}",
            "details": result
        }
    except Exception as e:
        print(f"Error processing webhooks: {str(e)}")
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