"""
Webhook processor for handling incoming webhooks
"""

import json
import uuid
from datetime import datetime
import re
import logging
from . import db

logger = logging.getLogger(__name__)

def is_aws_sns_alert(webhook_data):
    """Check if the webhook data is from AWS SNS"""
    # Check for common SNS fields
    if isinstance(webhook_data, dict):
        # Check for SNS message structure
        if 'Type' in webhook_data and webhook_data.get('Type') == 'Notification':
            return True
        
        # Check for SNS in headers or message content
        if 'Subject' in webhook_data and 'AWS' in webhook_data.get('Subject', ''):
            return True
            
        # Check message content for AWS references
        message = webhook_data.get('TextBody', '') or webhook_data.get('Message', '')
        if isinstance(message, str) and ('AWS' in message or 'Amazon' in message):
            return True
            
        # Check for AWS service names in the content
        aws_services = ['EC2', 'RDS', 'S3', 'Lambda', 'CloudWatch', 'DynamoDB', 'ECS', 'EKS']
        for service in aws_services:
            if service in str(webhook_data):
                return True
    
    return False

def extract_alert_info(webhook_data):
    """Extract alert information from webhook data"""
    alert_info = {
        'service': 'Unknown',
        'resource_id': 'Unknown',
        'alert_type': 'Unknown',
        'severity': 'medium',  # Default severity
        'message': 'Unknown alert',
        'region': 'us-east-1',  # Default region
        'account_id': '000000000000'  # Default account ID
    }
    
    # Try to extract information from the webhook data
    if isinstance(webhook_data, dict):
        # Extract from subject
        subject = webhook_data.get('Subject', '')
        if subject:
            # Try to identify service
            for service in ['EC2', 'RDS', 'S3', 'Lambda', 'CloudWatch', 'DynamoDB', 'ECS', 'EKS']:
                if service in subject:
                    alert_info['service'] = service
                    break
            
            # Try to identify severity
            if 'critical' in subject.lower():
                alert_info['severity'] = 'critical'
            elif 'high' in subject.lower() or 'warning' in subject.lower():
                alert_info['severity'] = 'high'
            
            # Use subject as message if available
            alert_info['message'] = subject
        
        # Extract from message body
        message = webhook_data.get('TextBody', '') or webhook_data.get('Message', '')
        if isinstance(message, str):
            # Try to parse JSON if the message is a JSON string
            try:
                message_json = json.loads(message)
                if isinstance(message_json, dict):
                    # Extract resource ID
                    resource_patterns = [
                        r'(i-[0-9a-f]{8,17})',  # EC2 instance ID
                        r'(vol-[0-9a-f]{8,17})',  # EBS volume ID
                        r'(arn:aws:[a-zA-Z0-9-]+:[a-zA-Z0-9-]+:[0-9]{12}:[a-zA-Z0-9-]+/[a-zA-Z0-9-]+)',  # ARN
                        r'([a-zA-Z0-9-]+\.[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+)'  # RDS instance ID
                    ]
                    
                    for pattern in resource_patterns:
                        match = re.search(pattern, str(message_json))
                        if match:
                            alert_info['resource_id'] = match.group(1)
                            break
                    
                    # Extract region
                    region_match = re.search(r'([a-z]{2}-[a-z]+-[0-9])', str(message_json))
                    if region_match:
                        alert_info['region'] = region_match.group(1)
                    
                    # Extract account ID
                    account_match = re.search(r'([0-9]{12})', str(message_json))
                    if account_match:
                        alert_info['account_id'] = account_match.group(1)
                    
                    # Extract alert type
                    if 'CPU' in str(message_json):
                        alert_info['alert_type'] = 'CPU'
                    elif 'Memory' in str(message_json):
                        alert_info['alert_type'] = 'Memory'
                    elif 'Disk' in str(message_json) or 'Storage' in str(message_json):
                        alert_info['alert_type'] = 'Disk'
                    elif 'Network' in str(message_json):
                        alert_info['alert_type'] = 'Network'
                    elif 'Error' in str(message_json):
                        alert_info['alert_type'] = 'Error'
            except:
                # If JSON parsing fails, try to extract from the raw message
                # Extract resource ID
                resource_patterns = [
                    r'(i-[0-9a-f]{8,17})',  # EC2 instance ID
                    r'(vol-[0-9a-f]{8,17})',  # EBS volume ID
                    r'(arn:aws:[a-zA-Z0-9-]+:[a-zA-Z0-9-]+:[0-9]{12}:[a-zA-Z0-9-]+/[a-zA-Z0-9-]+)',  # ARN
                    r'([a-zA-Z0-9-]+\.[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+)'  # RDS instance ID
                ]
                
                for pattern in resource_patterns:
                    match = re.search(pattern, message)
                    if match:
                        alert_info['resource_id'] = match.group(1)
                        break
                
                # Extract region
                region_match = re.search(r'([a-z]{2}-[a-z]+-[0-9])', message)
                if region_match:
                    alert_info['region'] = region_match.group(1)
                
                # Extract account ID
                account_match = re.search(r'([0-9]{12})', message)
                if account_match:
                    alert_info['account_id'] = account_match.group(1)
                
                # Use message as alert message if no subject
                if not alert_info['message'] or alert_info['message'] == 'Unknown alert':
                    # Truncate long messages
                    alert_info['message'] = message[:200] + ('...' if len(message) > 200 else '')
    
    return alert_info

def process_pending_webhooks():
    """Process all pending webhooks"""
    # Get all pending webhooks
    dynamodb = db.get_dynamodb_client()
    webhook_table = dynamodb.Table('webhook_queue')
    
    # Query for pending webhooks
    response = webhook_table.scan(
        FilterExpression="#status = :status",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={":status": "pending"}
    )
    
    pending_webhooks = response.get('Items', [])
    logger.info(f"Found {len(pending_webhooks)} pending webhooks to process")
    
    # Check if alerts table exists, create if not
    existing_tables = [table.name for table in dynamodb.tables.all()]
    if 'alerts' not in existing_tables:
        logger.info("Creating alerts table")
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
        logger.info("Alerts table created successfully")
    
    alerts_table = dynamodb.Table('alerts')
    
    processed_count = 0
    discarded_count = 0
    error_count = 0
    
    for webhook in pending_webhooks:
        webhook_id = webhook['id']
        raw_data = webhook.get('raw_data', {})
        
        try:
            # Check if this is an AWS SNS alert
            if is_aws_sns_alert(raw_data):
                # Extract alert information
                alert_info = extract_alert_info(raw_data)
                
                # Skip alerts with Unknown service
                if alert_info['service'] == 'Unknown':
                    # Mark as discarded
                    db.update_webhook_status(webhook_id, "discarded", "Service is Unknown")
                    discarded_count += 1
                    logger.info(f"Discarded webhook {webhook_id} with Unknown service")
                    continue
                
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
                
                # Save alert to DynamoDB
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
                
                processed_count += 1
                logger.info(f"Processed webhook {webhook_id} as alert {alert_id}")
            else:
                # Not an AWS alert, mark as discarded
                db.update_webhook_status(webhook_id, "discarded")
                discarded_count += 1
                logger.info(f"Discarded non-AWS webhook {webhook_id}")
        except Exception as e:
            # Update webhook status to error
            error_message = str(e)
            db.update_webhook_status(webhook_id, "error", error_message)
            error_count += 1
            logger.error(f"Error processing webhook {webhook_id}: {error_message}")
    
    return {
        "processed": processed_count,
        "discarded": discarded_count,
        "error": error_count,
        "total": len(pending_webhooks)
    }