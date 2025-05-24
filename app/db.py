import os
import boto3
import uuid
from datetime import datetime
from typing import List, Dict, Any
from .models import Alert, SeverityLevel

# DynamoDB setup
def get_dynamodb_client():
    """Get DynamoDB client - use local or AWS based on environment"""
    if os.environ.get("AWS_ENDPOINT_URL"):
        return boto3.resource(
            'dynamodb',
            endpoint_url=os.environ.get("AWS_ENDPOINT_URL", "http://localhost:8001"),
            region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", "fakeAccessKeyId"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", "fakeSecretAccessKey")
        )
    return boto3.resource('dynamodb')

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
            "account_id": "111111111111",
            "service": "EC2",
            "resource_id": "i-08abcd12345ef6789",
            "alert_type": "CPU",
            "severity": "high",
            "timestamp": datetime.now().isoformat(),
            "message": "High CPU utilization detected"
        },
        {
            "id": str(uuid.uuid4()),
            "account_id": "111111111111",
            "service": "EC2",
            "resource_id": "i-08abcd12345ef6789",
            "alert_type": "Memory",
            "severity": "critical",
            "timestamp": datetime.now().isoformat(),
            "message": "Memory pressure detected"
        },
        {
            "id": str(uuid.uuid4()),
            "account_id": "111111111111",
            "service": "RDS",
            "resource_id": "db-instance-1",
            "alert_type": "Disk",
            "severity": "medium",
            "timestamp": datetime.now().isoformat(),
            "message": "Disk space running low"
        },
        {
            "id": str(uuid.uuid4()),
            "account_id": "222222222222",
            "service": "Lambda",
            "resource_id": "function-alerts",
            "alert_type": "Timeout",
            "severity": "high",
            "timestamp": datetime.now().isoformat(),
            "message": "Function timeout detected"
        },
        {
            "id": str(uuid.uuid4()),
            "account_id": "222222222222",
            "service": "EC2",
            "resource_id": "i-09efgh67890ab1234",
            "alert_type": "CPU",
            "severity": "medium",
            "timestamp": datetime.now().isoformat(),
            "message": "Moderate CPU utilization"
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
    
    response = table.scan()
    items = response['Items']
    
    # Process items to create summary
    summary = {}
    for item in items:
        key = (item['account_id'], item['service'])
        if key not in summary:
            summary[key] = {
                'account_id': item['account_id'],
                'service': item['service'],
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

def get_service_resources(account_id: str, service: str):
    """Get resources for a specific account and service with alert counts"""
    dynamodb = get_dynamodb_client()
    table = dynamodb.Table('alerts')
    
    response = table.scan(
        FilterExpression="account_id = :account_id AND service = :service",
        ExpressionAttributeValues={
            ':account_id': account_id,
            ':service': service
        }
    )
    
    items = response['Items']
    
    # Process items to create resource summary
    summary = {}
    for item in items:
        resource_id = item['resource_id']
        if resource_id not in summary:
            summary[resource_id] = {
                'resource_id': resource_id,
                'service': service,
                'total_alerts': 0,
                'medium_alerts': 0,
                'high_alerts': 0,
                'critical_alerts': 0
            }
        
        summary[resource_id]['total_alerts'] += 1
        severity = item.get('severity', 'medium')
        if severity == 'medium':
            summary[resource_id]['medium_alerts'] += 1
        elif severity == 'high':
            summary[resource_id]['high_alerts'] += 1
        elif severity == 'critical':
            summary[resource_id]['critical_alerts'] += 1
    
    return list(summary.values())

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