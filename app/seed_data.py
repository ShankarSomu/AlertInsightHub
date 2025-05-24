import boto3
import uuid
from datetime import datetime, timedelta
import random
import os

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

# Create table if it doesn't exist
def create_table():
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
    else:
        print("Table 'alerts' already exists")

# Generate sample data
def generate_sample_data():
    # Sample data configuration
    accounts = ["123456789012", "987654321098", "456789012345"]
    services = ["EC2", "RDS", "Lambda", "S3", "DynamoDB"]
    regions = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]
    
    resources = {
        "EC2": ["i-08abcd12345ef6789", "i-09efgh67890ab1234", "i-07ijkl56789mn0123"],
        "RDS": ["db-instance-1", "db-instance-2", "db-instance-3"],
        "Lambda": ["function-alerts", "function-processing", "function-backup"],
        "S3": ["data-bucket", "logs-bucket", "backup-bucket"],
        "DynamoDB": ["users-table", "products-table", "orders-table"]
    }
    
    alert_types = {
        "EC2": ["CPU", "Memory", "Disk", "Network"],
        "RDS": ["CPU", "Memory", "Storage", "IOPS", "Connections"],
        "Lambda": ["Timeout", "Error", "Throttle", "Memory"],
        "S3": ["Size", "Objects", "Requests", "Errors"],
        "DynamoDB": ["Throttle", "Latency", "Capacity", "Error"]
    }
    
    severities = ["medium", "high", "critical"]
    
    # Generate alerts
    alerts = []
    now = datetime.now()
    
    for account in accounts:
        for service in services:
            # Generate different number of alerts for each service
            num_alerts = random.randint(5, 15)
            
            for _ in range(num_alerts):
                resource = random.choice(resources[service])
                alert_type = random.choice(alert_types[service])
                severity = random.choice(severities)
                region = random.choice(regions)
                
                # Generate a random timestamp within the last 7 days
                random_days = random.randint(0, 7)
                random_hours = random.randint(0, 23)
                random_minutes = random.randint(0, 59)
                timestamp = now - timedelta(days=random_days, hours=random_hours, minutes=random_minutes)
                
                alert = {
                    "id": str(uuid.uuid4()),
                    "account_id": account,
                    "service": service,
                    "resource_id": resource,
                    "alert_type": alert_type,
                    "severity": severity,
                    "timestamp": timestamp.isoformat(),
                    "message": f"{severity.capitalize()} {alert_type} alert for {service} resource {resource}",
                    "region": region
                }
                
                alerts.append(alert)
    
    return alerts

# Insert data into DynamoDB
def seed_data():
    table = dynamodb.Table('alerts')
    
    # Check if data already exists
    if table.scan(Limit=1)['Items']:
        print("Data already exists in the table. Clearing existing data...")
        
        # Clear existing data
        scan = table.scan()
        with table.batch_writer() as batch:
            for item in scan['Items']:
                batch.delete_item(Key={'id': item['id']})
    
    # Generate and insert new data
    alerts = generate_sample_data()
    
    print(f"Inserting {len(alerts)} sample alerts...")
    with table.batch_writer() as batch:
        for alert in alerts:
            batch.put_item(Item=alert)
    
    print("Sample data inserted successfully")

if __name__ == "__main__":
    create_table()
    seed_data()
    print("Done! You can now access the dashboard at http://localhost:8000/")