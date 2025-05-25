"""
Routes for processing webhooks into alerts
"""

from fastapi import APIRouter, HTTPException
import uuid
from datetime import datetime
from .. import db
from ..webhook_processor import process_pending_webhooks, is_aws_sns_alert, extract_alert_info

router = APIRouter(prefix="/api/process", tags=["process"])

@router.post("/webhook/{webhook_id}")
async def process_webhook(webhook_id: str):
    """Process a webhook and create alerts based on its content"""
    try:
        # Get webhook data
        dynamodb = db.get_dynamodb_client()
        webhook_table = dynamodb.Table('webhook_queue')
        response = webhook_table.get_item(Key={'id': webhook_id})
        
        if 'Item' not in response:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        webhook = response['Item']
        raw_data = webhook.get('raw_data', {})
        
        # Check if this is an AWS SNS alert
        if not is_aws_sns_alert(raw_data):
            # Not an AWS alert, mark as discarded
            db.update_webhook_status(webhook_id, "discarded")
            return {
                "status": "success",
                "message": "Webhook discarded - not an AWS alert",
                "webhook_id": webhook_id
            }
        
        # Extract alert information
        alert_info = extract_alert_info(raw_data)
        
        # Skip alerts with Unknown service
        if alert_info['service'] == 'Unknown':
            # Mark as discarded
            db.update_webhook_status(webhook_id, "discarded", "Service is Unknown")
            return {
                "status": "success",
                "message": "Webhook discarded - Unknown service",
                "webhook_id": webhook_id
            }
        
        # Generate alert ID
        alert_id = str(uuid.uuid4())
        
        # Get remediation recommendation
        remediation = db.get_remediation_action(
            alert_info['service'], 
            alert_info['alert_type'], 
            alert_info['severity']
        )
        
        # Create alert item
        alert_item = {
            "id": alert_id,
            "account_id": alert_info['account_id'],
            "service": alert_info['service'],
            "resource_id": alert_info['resource_id'],
            "alert_type": alert_info['alert_type'],
            "severity": alert_info['severity'],
            "timestamp": datetime.now().isoformat(),
            "message": alert_info['message'],
            "region": alert_info['region'],
            "webhook_id": webhook_id,
            "remediation": remediation
        }
        
        # Check if alerts table exists, create if not
        existing_tables = [table.name for table in dynamodb.tables.all()]
        if 'alerts' not in existing_tables:
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
        
        # Save alert to DynamoDB
        alerts_table = dynamodb.Table('alerts')
        alerts_table.put_item(Item=alert_item)
        
        # Add agent interpretation to the webhook data
        agent_interpretation = {
            "alert_id": alert_id,
            "interpreted_service": alert_info['service'],
            "interpreted_resource_id": alert_info['resource_id'],
            "interpreted_alert_type": alert_info['alert_type'],
            "interpreted_severity": alert_info['severity'],
            "interpreted_region": alert_info['region'],
            "interpreted_account_id": alert_info['account_id'],
            "interpreted_message": alert_info['message'],
            "ai_recommendation": remediation
        }
        
        # Update webhook with processed information
        dynamodb = db.get_dynamodb_client()
        webhook_table = dynamodb.Table('webhook_queue')
        webhook_table.update_item(
            Key={'id': webhook_id},
            UpdateExpression="SET #status = :status, processed_at = :processed_at, agent_interpretation = :agent_interpretation",
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': 'processed',
                ':processed_at': datetime.now().isoformat(),
                ':agent_interpretation': agent_interpretation
            }
        )
        
        return {
            "status": "success",
            "message": "Webhook processed successfully",
            "alert_id": alert_id
        }
    except Exception as e:
        # Update status to error
        try:
            db.update_webhook_status(webhook_id, "error", str(e))
        except:
            pass
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/all")
async def process_all_webhooks():
    """Process all pending webhooks"""
    try:
        # Process all pending webhooks
        result = process_pending_webhooks()
        
        # Return the results
        return {
            "status": "success", 
            "message": f"Processed {result['processed']} webhooks, discarded {result['discarded']}, errors: {result['error']}",
            "details": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))