#!/usr/bin/env python3
"""
Script to process pending webhook items.
This can be run manually or as a scheduled task.
"""

import os
import logging
import boto3
import uuid
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

def process_pending_webhooks(limit=10):
    """Process pending webhook items"""
    logger.info("Processing pending webhook items...")
    
    # Get tables
    queue_table = dynamodb.Table('webhook_queue')
    postmark_table = dynamodb.Table('postmark_data')
    alerts_table = dynamodb.Table('alerts')
    
    # Get pending items
    response = queue_table.scan(
        FilterExpression='#status = :status',
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues={':status': 'pending'},
        Limit=limit
    )
    
    pending_items = response.get('Items', [])
    logger.info(f"Found {len(pending_items)} pending webhook items")
    
    processed_count = 0
    error_count = 0
    
    for item in pending_items:
        webhook_id = item['id']
        timestamp_iso = item.get('timestamp')
        
        try:
            logger.info(f"Processing webhook: {webhook_id}")
            
            # Get the raw data from postmark_data table
            postmark_response = postmark_table.get_item(Key={'id': webhook_id})
            if 'Item' not in postmark_response:
                raise Exception(f"No postmark data found for webhook ID: {webhook_id}")
            
            postmark_item = postmark_response['Item']
            data = postmark_item.get('raw_data', {})
            
            # Extract relevant information from the webhook payload
            if "MessageID" in data or "Subject" in data:
                subject = data.get("Subject", "No subject")
                message_id = data.get("MessageID", webhook_id)
                
                # Determine severity based on subject (example logic)
                severity = "medium"
                if "critical" in subject.lower():
                    severity = "critical"
                elif "high" in subject.lower() or "urgent" in subject.lower():
                    severity = "high"
                
                # Create an alert from the webhook
                alert = {
                    "id": message_id,
                    "account_id": "postmark-webhook",
                    "service": "Webhook",
                    "resource_id": f"webhook-{webhook_id[:8]}",
                    "alert_type": "Inbound Webhook",
                    "severity": severity,
                    "timestamp": timestamp_iso,
                    "message": subject,
                    "region": "global",
                    "webhook_id": webhook_id  # Reference to the webhook queue item
                }
                
                # Save to alerts table
                alerts_table.put_item(Item=alert)
                
                # Update queue item status to processed
                queue_table.update_item(
                    Key={"id": webhook_id},
                    UpdateExpression="SET #status = :status, processed_at = :processed_at",
                    ExpressionAttributeNames={"#status": "status"},
                    ExpressionAttributeValues={
                        ":status": "processed",
                        ":processed_at": datetime.now().isoformat()
                    }
                )
                
                logger.info(f"Successfully processed webhook: {webhook_id}")
                processed_count += 1
            else:
                # Update queue item status to error
                queue_table.update_item(
                    Key={"id": webhook_id},
                    UpdateExpression="SET #status = :status, processed_at = :processed_at, error_message = :error",
                    ExpressionAttributeNames={"#status": "status"},
                    ExpressionAttributeValues={
                        ":status": "error",
                        ":processed_at": datetime.now().isoformat(),
                        ":error": "Invalid payload format"
                    }
                )
                
                logger.warning(f"Invalid payload format for webhook: {webhook_id}")
                error_count += 1
        except Exception as e:
            # Update queue item status to error
            queue_table.update_item(
                Key={"id": webhook_id},
                UpdateExpression="SET #status = :status, processed_at = :processed_at, error_message = :error",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":status": "error",
                    ":processed_at": datetime.now().isoformat(),
                    ":error": str(e)
                }
            )
            
            logger.error(f"Error processing webhook {webhook_id}: {e}")
            error_count += 1
    
    logger.info(f"Processing complete. Processed: {processed_count}, Errors: {error_count}")
    return {
        "processed": processed_count,
        "errors": error_count,
        "total": len(pending_items)
    }

if __name__ == "__main__":
    process_pending_webhooks()
    print("Done! Webhook processing complete.")