import os
import boto3
import uuid
from datetime import datetime
from typing import List, Dict, Any
from .models import Alert, SeverityLevel

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
    
    return list(summary.values())

def get_service_resources(account_id: str, service: str, region: str = None):
    """Get resources for a specific account and service with alert counts"""
    dynamodb = get_dynamodb_client()
    table = dynamodb.Table('alerts')
    
    # Build filter expression based on whether region is provided
    if region and region != 'all':
        filter_expr = "account_id = :account_id AND service = :service AND region = :region"
        expr_values = {
            ':account_id': account_id,
            ':service': service,
            ':region': region
        }
    else:
        filter_expr = "account_id = :account_id AND service = :service"
        expr_values = {
            ':account_id': account_id,
            ':service': service
        }
    
    response = table.scan(
        FilterExpression=filter_expr,
        ExpressionAttributeValues=expr_values
    )
    
    items = response['Items']
    
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
    
    # Filter by resource_id, alert_type and severity
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

def get_remediation_action(service: str, alert_type: str, severity: str):
    """Get remediation recommendations based on service, alert type and severity"""
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
            },
            "Disk": {
                "medium": "Clean up unnecessary files or consider increasing storage.",
                "high": "Increase EBS volume size or add additional volumes.",
                "critical": "Immediately increase storage and implement better disk management."
            },
            "Network": {
                "medium": "Monitor network traffic patterns for optimization.",
                "high": "Optimize network-intensive operations or increase bandwidth.",
                "critical": "Investigate potential DDoS attack or network bottlenecks."
            }
        },
        "RDS": {
            "CPU": {
                "medium": "Review and optimize database queries.",
                "high": "Scale up your database instance or implement read replicas.",
                "critical": "Immediately scale up your instance and optimize critical queries."
            },
            "Memory": {
                "medium": "Review database configuration for memory settings.",
                "high": "Increase instance memory or optimize memory-intensive queries.",
                "critical": "Immediately increase instance memory and fix memory leaks."
            },
            "Storage": {
                "medium": "Clean up old data or implement archiving strategy.",
                "high": "Increase storage capacity or implement data partitioning.",
                "critical": "Immediately increase storage and implement emergency cleanup."
            },
            "IOPS": {
                "medium": "Review I/O intensive queries and optimize.",
                "high": "Increase provisioned IOPS or implement caching.",
                "critical": "Immediately increase provisioned IOPS and fix I/O bottlenecks."
            },
            "Connections": {
                "medium": "Review connection pooling configuration.",
                "high": "Implement better connection management or increase max connections.",
                "critical": "Immediately fix connection leaks and optimize connection usage."
            }
        },
        "Lambda": {
            "Timeout": {
                "medium": "Review function logic for optimization opportunities.",
                "high": "Increase timeout setting or break function into smaller parts.",
                "critical": "Immediately refactor function to handle workload appropriately."
            },
            "Error": {
                "medium": "Review error logs and implement better error handling.",
                "high": "Fix critical errors and implement retry mechanisms.",
                "critical": "Immediately fix function errors and implement circuit breakers."
            },
            "Throttle": {
                "medium": "Review concurrency settings and usage patterns.",
                "high": "Increase concurrency limits or implement backoff strategies.",
                "critical": "Immediately increase concurrency limits and optimize invocation patterns."
            },
            "Memory": {
                "medium": "Review memory usage and optimize function code.",
                "high": "Increase allocated memory or optimize memory-intensive operations.",
                "critical": "Immediately increase memory allocation and fix memory leaks."
            }
        }
    }
    
    # Get default remediation if specific one is not found
    default_remediation = f"Investigate the {severity} {alert_type} alert for your {service} resource."
    
    # Try to get specific remediation
    service_remediation = remediation_map.get(service, {})
    alert_type_remediation = service_remediation.get(alert_type, {})
    specific_remediation = alert_type_remediation.get(severity, default_remediation)
    
    return specific_remediation