import boto3
import os
import json

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

# List tables
print("DynamoDB Tables:")
tables = list(dynamodb.tables.all())
for table in tables:
    print(f"- {table.name}")

# Check if alerts table exists
if not tables:
    print("\nNo tables found in DynamoDB!")
else:
    # Check alerts table data
    try:
        table = dynamodb.Table('alerts')
        response = table.scan()
        items = response['Items']
        
        print(f"\nFound {len(items)} items in 'alerts' table:")
        for i, item in enumerate(items[:5]):  # Show first 5 items
            print(f"\nItem {i+1}:")
            print(json.dumps(item, indent=2, default=str))
        
        if len(items) > 5:
            print(f"\n... and {len(items) - 5} more items")
            
        if not items:
            print("\nThe 'alerts' table exists but contains no data!")
    except Exception as e:
        print(f"\nError accessing 'alerts' table: {e}")