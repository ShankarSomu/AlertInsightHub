import os
import boto3
import uuid
from datetime import datetime
from typing import List, Dict, Any
from .models import Alert, SeverityLevel
import requests

# DynamoDB setup
def get_dynamodb_client():
    """Get DynamoDB client - use local or AWS based on environment"""
    # Always use these defaults for local development if not explicitly set
    return boto3.resource(
        'dynamodb',
        endpoint_url=os.environ.get("AWS_ENDPOINT_URL", "http://localhost:8001"),
        region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", "fakeAccessKeyId"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", "fakeSecretAccessKey")
    )

def create_tables():
    """Create DynamoDB tables if they don't exist"""
    dynamodb = get_dynamodb_client()
    
    # Check if table exists
    existing_tables = [table.name for table in dynamodb.tables.all()]
    
    if 'alerts' not in existing_tables:
        table = dynamodb.create_table(
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
        print("Table created:", table.table_name)

def seed_sample_data():
    """Seed sample alert data"""
    dynamodb = get_dynamodb_client()
    table = dynamodb.Table('alerts')
    
    # Check if data already exists
    if table.scan(Limit=1)['Items']:
        print("Data already exists, skipping seed")
        return
    
    sample_data = [
        {
            "id": str(uuid.uuid4()),
            "account_id": "123456789012",
            "service": "EC2",
            "resource_id": "i-08abcd12345ef6789",
            "alert_type": "CPU",
            "severity": "high",
            "timestamp": datetime.now().isoformat(),
            "message": "High CPU utilization detected"
        },
        {
            "id": str(uuid.uuid4()),
            "account_id": "123456789012",
            "service": "EC2",
            "resource_id": "i-08abcd12345ef6789",
            "alert_type": "Memory",
            "severity": "critical",
            "timestamp": datetime.now().isoformat(),
            "message": "Memory pressure detected"
        },
        {
            "id": str(uuid.uuid4()),
            "account_id": "123456789012",
            "service": "RDS",
            "resource_id": "db-instance-1",
            "alert_type": "Disk",
            "severity": "medium",
            "timestamp": datetime.now().isoformat(),
            "message": "Disk space running low"
        },
        {
            "id": str(uuid.uuid4()),
            "account_id": "987654321098",
            "service": "Lambda",
            "resource_id": "function-alerts",
            "alert_type": "Timeout",
            "severity": "high",
            "timestamp": datetime.now().isoformat(),
            "message": "Function timeout detected"
        },
        {
            "id": str(uuid.uuid4()),
            "account_id": "987654321098",
            "service": "EC2",
            "resource_id": "i-09efgh67890ab1234",
            "alert_type": "CPU",
            "severity": "medium",
            "timestamp": datetime.now().isoformat(),
            "message": "Moderate CPU utilization"
        },
        {
            "id": str(uuid.uuid4()),
            "account_id": "456789012345",
            "service": "DynamoDB",
            "resource_id": "users-table",
            "alert_type": "Capacity",
            "severity": "high",
            "timestamp": datetime.now().isoformat(),
            "message": "Provisioned capacity exceeded"
        },
        {
            "id": str(uuid.uuid4()),
            "account_id": "456789012345",
            "service": "S3",
            "resource_id": "data-bucket",
            "alert_type": "Size",
            "severity": "medium",
            "timestamp": datetime.now().isoformat(),
            "message": "Bucket size growing rapidly"
        }
    ]
    
    with table.batch_writer() as batch:
        for item in sample_data:
            batch.put_item(Item=item)
    
    print(f"Seeded {len(sample_data)} sample alerts")

# Data access functions
def get_account_service_summary():
    """Get summary of alerts by account and service"""
    dynamodb = get_dynamodb_client()
    table = dynamodb.Table('alerts')
    
    try:
        response = table.scan()
        items = response['Items']
        
        print(f"Retrieved {len(items)} items from DynamoDB")
        
        # Process items to create summary
        summary = {}
        for item in items:
            # Include region in the key
            region = item.get('region', 'us-east-1')
            key = (item['account_id'], item['service'], region)
            if key not in summary:
                summary[key] = {
                    'account_id': item['account_id'],
                    'service': item['service'],
                    'region': region,
                    'total_alerts': 0,
                    'medium_alerts': 0,
                    'high_alerts': 0,
                    'critical_alerts': 0
                }
            
            summary[key]['total_alerts'] += 1
            severity = item.get('severity', 'medium')
            if severity == 'medium':
                summary[key]['medium_alerts'] += 1
            elif severity == 'high':
                summary[key]['high_alerts'] += 1
            elif severity == 'critical':
                summary[key]['critical_alerts'] += 1
        
        result = list(summary.values())
        print(f"Returning {len(result)} summary records")
        return result
    except Exception as e:
        print(f"Error in get_account_service_summary: {e}")
        # Return empty list instead of raising exception
        return []

def get_service_resources(account_id: str, service: str, region: str = None):
    """Get resources for a specific account and service with alert counts"""
    dynamodb = get_dynamodb_client()
    table = dynamodb.Table('alerts')
    
    try:
        # Build filter expression based on whether region is provided
        if region and region != 'all':
            # Use ExpressionAttributeNames for reserved keyword 'region'
            filter_expr = "account_id = :account_id AND service = :service AND #r = :region"
            expr_values = {
                ':account_id': account_id,
                ':service': service,
                ':region': region
            }
            expr_names = {'#r': 'region'}
        else:
            filter_expr = "account_id = :account_id AND service = :service"
            expr_values = {
                ':account_id': account_id,
                ':service': service
            }
            expr_names = {}
        
        response = table.scan(
            FilterExpression=filter_expr,
            ExpressionAttributeValues=expr_values,
            ExpressionAttributeNames=expr_names if expr_names else None
        )
        
        items = response['Items']
        
        # If no items found, return a default item to avoid undefined values
        if not items:
            return [{
                'resource_id': f"no-resources-found-{service}",
                'service': service,
                'region': region or 'us-east-1',
                'total_alerts': 0,
                'medium_alerts': 0,
                'high_alerts': 0,
                'critical_alerts': 0
            }]
        
        # Process items to create resource summary
        summary = {}
        for item in items:
            resource_id = item['resource_id']
            item_region = item.get('region', 'us-east-1')
            key = (resource_id, item_region)
            
            if key not in summary:
                summary[key] = {
                    'resource_id': resource_id,
                    'service': service,
                    'region': item_region,
                    'total_alerts': 0,
                    'medium_alerts': 0,
                    'high_alerts': 0,
                    'critical_alerts': 0
                }
            
            summary[key]['total_alerts'] += 1
            severity = item.get('severity', 'medium')
            if severity == 'medium':
                summary[key]['medium_alerts'] += 1
            elif severity == 'high':
                summary[key]['high_alerts'] += 1
            elif severity == 'critical':
                summary[key]['critical_alerts'] += 1
        
        return list(summary.values())
    except Exception as e:
        print(f"Error in get_service_resources: {e}")
        # Return a default item in case of error
        return [{
            'resource_id': f"error-{service}",
            'service': service,
            'region': region or 'us-east-1',
            'total_alerts': 0,
            'medium_alerts': 0,
            'high_alerts': 0,
            'critical_alerts': 0
        }]

def get_resource_alerts(resource_id: str):
    """Get alert types and counts for a specific resource"""
    dynamodb = get_dynamodb_client()
    table = dynamodb.Table('alerts')
    
    response = table.scan(
        FilterExpression="resource_id = :resource_id",
        ExpressionAttributeValues={
            ':resource_id': resource_id
        }
    )
    
    items = response['Items']
    
    # Process items to create alert type summary
    summary = {}
    for item in items:
        alert_type = item['alert_type']
        if alert_type not in summary:
            summary[alert_type] = {
                'alert_type': alert_type,
                'total_alerts': 0,
                'medium_alerts': 0,
                'high_alerts': 0,
                'critical_alerts': 0
            }
        
        summary[alert_type]['total_alerts'] += 1
        severity = item.get('severity', 'medium')
        if severity == 'medium':
            summary[alert_type]['medium_alerts'] += 1
        elif severity == 'high':
            summary[alert_type]['high_alerts'] += 1
        elif severity == 'critical':
            summary[alert_type]['critical_alerts'] += 1
    
    return list(summary.values())

def get_alert_details(resource_id: str, alert_type: str, severity: str):
    """Get detailed information about specific alerts"""
    dynamodb = get_dynamodb_client()
    table = dynamodb.Table('alerts')
    
    # Filter by resource_id, alert_type and severity - ensure we only get alerts of the specified severity
    response = table.scan(
        FilterExpression="resource_id = :resource_id AND alert_type = :alert_type AND severity = :severity",
        ExpressionAttributeValues={
            ':resource_id': resource_id,
            ':alert_type': alert_type,
            ':severity': severity
        }
    )
    
    items = response['Items']
    
    # Add remediation recommendations based on alert type and severity
    for item in items:
        item['remediation'] = get_remediation_action(item['service'], item['alert_type'], item['severity'])
    
    return items

def get_alerts_by_severity(severity: str):
    """Get all alerts of a specific severity across all accounts and services"""
    dynamodb = get_dynamodb_client()
    table = dynamodb.Table('alerts')
    
    # Filter by severity
    response = table.scan(
        FilterExpression="severity = :severity",
        ExpressionAttributeValues={
            ':severity': severity
        }
    )
    
    items = response['Items']
    
    # Add remediation recommendations
    for item in items:
        item['remediation'] = get_remediation_action(item['service'], item['alert_type'], item['severity'])
    
    return items

def get_filtered_alerts(account_id: str, service: str, region: str, severity: str):
    """Get alerts filtered by account, service, region and severity"""
    dynamodb = get_dynamodb_client()
    table = dynamodb.Table('alerts')
    
    try:
        # Build filter expression
        filter_expr = "account_id = :account_id AND service = :service AND severity = :severity"
        expr_values = {
            ':account_id': account_id,
            ':service': service,
            ':severity': severity
        }
        expr_names = {}
        
        # Add region filter if provided
        if region and region != 'all':
            filter_expr += " AND #r = :region"
            expr_values[':region'] = region
            expr_names['#r'] = 'region'
        
        # Execute the query
        response = table.scan(
            FilterExpression=filter_expr,
            ExpressionAttributeValues=expr_values,
            ExpressionAttributeNames=expr_names if expr_names else None
        )
        
        items = response['Items']
        
        # Add remediation recommendations
        for item in items:
            item['remediation'] = get_remediation_action(item['service'], item['alert_type'], item['severity'])
        
        return items
    except Exception as e:
        print(f"Error in get_filtered_alerts: {e}")
        return []

def get_webhook_queue_items(status=None, date=None, limit=50):
    """Get webhook queue items, optionally filtered by status and/or date"""
    dynamodb = get_dynamodb_client()
    
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
    
    table = dynamodb.Table('webhook_queue')
    
    try:
        # For debugging
        print(f"Getting webhook queue items with status={status}, date={date}, limit={limit}")
        
        # Use scan instead of query for simplicity and to avoid index issues
        if status and date and isinstance(date, str):
            # Filter by both status and date
            response = table.scan(
                FilterExpression='#status = :status AND #date = :date',
                ExpressionAttributeNames={'#status': 'status', '#date': 'date'},
                ExpressionAttributeValues={':status': status, ':date': date},
                Limit=limit
            )
        elif status:
            # Filter by status only
            response = table.scan(
                FilterExpression='#status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':status': status},
                Limit=limit
            )
        elif date and isinstance(date, str):
            # Filter by date only
            response = table.scan(
                FilterExpression='#date = :date',
                ExpressionAttributeNames={'#date': 'date'},
                ExpressionAttributeValues={':date': date},
                Limit=limit
            )
        else:
            # Scan all items
            response = table.scan(Limit=limit)
        
        items = response.get('Items', [])
        print(f"Found {len(items)} webhook queue items")
        
        # For debugging, print the first item if available
        if items:
            print(f"First item: {items[0]}")
        
        return items
    except Exception as e:
        print(f"Error in get_webhook_queue_items: {e}")
        return []

def update_webhook_status(webhook_id, status, error_message=None):
    """Update the status of a webhook queue item"""
    dynamodb = get_dynamodb_client()
    table = dynamodb.Table('webhook_queue')
    
    try:
        update_expr = "SET #status = :status, processed_at = :processed_at"
        expr_attr_values = {
            ':status': status,
            ':processed_at': datetime.now().isoformat()
        }
        
        if error_message:
            update_expr += ", error_message = :error"
            expr_attr_values[':error'] = error_message
        
        table.update_item(
            Key={'id': webhook_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues=expr_attr_values
        )
        
        return True
    except Exception as e:
        print(f"Error updating webhook status: {e}")
        return False

def get_webhook_stats(date=None):
    """Get webhook queue statistics, optionally filtered by date"""
    dynamodb = get_dynamodb_client()
    
    # Check if table exists first
    existing_tables = [table.name for table in dynamodb.tables.all()]
    if 'webhook_queue' not in existing_tables:
        print("webhook_queue table doesn't exist for stats")
        return {
            'total': 0,
            'pending': 0,
            'processed': 0,
            'error': 0,
            'dates': {}
        }
    
    table = dynamodb.Table('webhook_queue')
    
    try:
        # Use scan instead of query for simplicity
        if date:
            response = table.scan(
                FilterExpression='#date = :date',
                ExpressionAttributeNames={'#date': 'date'},
                ExpressionAttributeValues={':date': date}
            )
        else:
            # Scan all items
            response = table.scan()
        
        items = response['Items']
        
        # Calculate statistics
        stats = {
            'total': len(items),
            'pending': 0,
            'processed': 0,
            'error': 0,
            'dates': {}
        }
        
        for item in items:
            status = item.get('status', 'unknown')
            item_date = item.get('date', 'unknown')
            
            # Update overall counts
            if status == 'pending':
                stats['pending'] += 1
            elif status == 'processed':
                stats['processed'] += 1
            elif status == 'error':
                stats['error'] += 1
            
            # Update date-specific counts
            if item_date not in stats['dates']:
                stats['dates'][item_date] = {
                    'total': 0,
                    'pending': 0,
                    'processed': 0,
                    'error': 0
                }
            
            stats['dates'][item_date]['total'] += 1
            if status == 'pending':
                stats['dates'][item_date]['pending'] += 1
            elif status == 'processed':
                stats['dates'][item_date]['processed'] += 1
            elif status == 'error':
                stats['dates'][item_date]['error'] += 1
        
        return stats
    except Exception as e:
        print(f"Error in get_webhook_stats: {e}")
        return {
            'total': 0,
            'pending': 0,
            'processed': 0,
            'error': 0,
            'dates': {}
        }

def get_gorqcloud_api_key():
    """Get the Groq API key from settings"""
    dynamodb = get_dynamodb_client()
    
    # Check if settings table exists
    existing_tables = [table.name for table in dynamodb.tables.all()]
    if 'settings' not in existing_tables:
        return None
    
    table = dynamodb.Table('settings')
    response = table.get_item(Key={'setting_name': 'gorqcloud_api_key'})
    
    if 'Item' in response:
        return response['Item'].get('setting_value')
    
    return None

def get_agent_settings():
    """Get the agent role and description from settings"""
    dynamodb = get_dynamodb_client()
    
    # Check if settings table exists
    existing_tables = [table.name for table in dynamodb.tables.all()]
    if 'settings' not in existing_tables:
        return None, None
    
    table = dynamodb.Table('settings')
    
    # Get agent role
    role_response = table.get_item(Key={'setting_name': 'agent_role'})
    role = role_response.get('Item', {}).get('setting_value', 'AWS Cloud Expert')
    
    # Get agent description
    desc_response = table.get_item(Key={'setting_name': 'agent_description'})
    description = desc_response.get('Item', {}).get('setting_value', 
        'You are an AWS cloud expert specializing in monitoring and resolving alerts. Provide concise, actionable recommendations.')
    
    return role, description

def get_remediation_action(service: str, alert_type: str, severity: str):
    """Get remediation recommendations using Groq LLM if available, otherwise use default"""
    # Try to get API key
    api_key = get_gorqcloud_api_key()
    use_ai = False
    
    # Check if AI recommendations are enabled
    dynamodb = get_dynamodb_client()
    existing_tables = [table.name for table in dynamodb.tables.all()]
    if 'settings' in existing_tables:
        table = dynamodb.Table('settings')
        response = table.get_item(Key={'setting_name': 'use_ai_recommendations'})
        if 'Item' in response and response['Item'].get('setting_value') == 'true':
            use_ai = True
    
    if api_key and use_ai:
        try:
            # Use the Groq client to get a recommendation
            from groq import Groq
            import os
            
            # Get agent role and description
            agent_role, agent_description = get_agent_settings()
            
            # Set the API key for the Groq client
            os.environ["GROQ_API_KEY"] = api_key
            
            # Initialize the Groq client
            client = Groq(api_key=api_key)
            
            # Create the system message with the agent role and description
            system_message = f"You are a {agent_role}. {agent_description}"
            
            # Create the user prompt for the recommendation
            user_prompt = f"Provide a concise recommendation for addressing a {severity} severity {alert_type} alert on an AWS {service} resource. Keep it under 100 words."
            
            # Make the API call
            completion = client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[
                    {
                        "role": "system",
                        "content": system_message
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                temperature=0.7,
                max_completion_tokens=100,
                top_p=1,
                stream=False
            )
            
            # Extract the recommendation from the response
            if completion.choices and len(completion.choices) > 0:
                ai_recommendation = completion.choices[0].message.content.strip()
                # Store the recommendation in the database for future use
                store_recommendation(service, alert_type, severity, ai_recommendation)
                return ai_recommendation
                
        except Exception as e:
            print(f"Error calling Groq API: {e}")
    
    # Fallback to default recommendations if API call fails or no API key
    default_remediation = f"Investigate the {severity} {alert_type} alert for your {service} resource."
    
    # Check if we already have a recommendation in the database
    if 'alert_recommendations' in existing_tables:
        table = dynamodb.Table('alert_recommendations')
        response = table.get_item(
            Key={
                'service': service,
                'alert_type_severity': f"{alert_type}_{severity}"
            }
        )
        
        if 'Item' in response:
            return response['Item'].get('recommendation', default_remediation)
    
    # Default hardcoded recommendations as fallback
    remediation_map = {
        "EC2": {
            "CPU": {
                "medium": "Consider scaling your instance or optimizing your application.",
                "high": "Scale up your instance type or implement auto-scaling.",
                "critical": "Immediately scale up your instance and investigate the root cause."
            },
            "Memory": {
                "medium": "Monitor memory usage and consider application optimization.",
                "high": "Increase instance memory or optimize memory-intensive processes.",
                "critical": "Immediately increase instance memory and investigate memory leaks."
            }
        },
        "RDS": {
            "CPU": {
                "medium": "Review and optimize database queries.",
                "high": "Scale up your database instance or implement read replicas.",
                "critical": "Immediately scale up your instance and optimize critical queries."
            }
        }
    }
    
    # Try to get specific remediation
    service_remediation = remediation_map.get(service, {})
    alert_type_remediation = service_remediation.get(alert_type, {})
    specific_remediation = alert_type_remediation.get(severity, default_remediation)
    
    return specific_remediation

def store_recommendation(service, alert_type, severity, recommendation):
    """Store a recommendation in the database"""
    dynamodb = get_dynamodb_client()
    
    # Check if recommendations table exists
    existing_tables = [table.name for table in dynamodb.tables.all()]
    if 'alert_recommendations' not in existing_tables:
        # Create recommendations table
        recommendations_table = dynamodb.create_table(
            TableName='alert_recommendations',
            KeySchema=[
                {'AttributeName': 'service', 'KeyType': 'HASH'},
                {'AttributeName': 'alert_type_severity', 'KeyType': 'RANGE'},
            ],
            AttributeDefinitions=[
                {'AttributeName': 'service', 'AttributeType': 'S'},
                {'AttributeName': 'alert_type_severity', 'AttributeType': 'S'},
            ],
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        # Wait for table to be created
        recommendations_table.meta.client.get_waiter('table_exists').wait(TableName='alert_recommendations')
        table = dynamodb.Table('alert_recommendations')
    else:
        table = dynamodb.Table('alert_recommendations')
    
    # Save recommendation
    table.put_item(
        Item={
            'service': service,
            'alert_type_severity': f"{alert_type}_{severity}",
            'recommendation': recommendation,
            'created_at': datetime.now().isoformat()
        }
    )