"""
API routes for application settings
"""

from fastapi import APIRouter, HTTPException, Body
from .. import db
import boto3

router = APIRouter(prefix="/api/settings", tags=["settings"])

@router.get("/")
async def get_settings():
    """Get all application settings"""
    try:
        # Get settings from DynamoDB
        dynamodb = db.get_dynamodb_client()
        
        # Check if settings table exists
        existing_tables = [table.name for table in dynamodb.tables.all()]
        if 'settings' not in existing_tables:
            # Create settings table
            table = dynamodb.create_table(
                TableName='settings',
                KeySchema=[
                    {'AttributeName': 'setting_name', 'KeyType': 'HASH'},
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'setting_name', 'AttributeType': 'S'},
                ],
                ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
            )
            # Wait for table to be created
            table.meta.client.get_waiter('table_exists').wait(TableName='settings')
            return {}
        
        # Get all settings
        table = dynamodb.Table('settings')
        response = table.scan()
        
        # Convert to dictionary
        settings = {}
        for item in response.get('Items', []):
            # Mask API key for security
            if item['setting_name'] == 'gorqcloud_api_key' and item.get('setting_value'):
                masked_key = item['setting_value'][:4] + '*' * (len(item['setting_value']) - 8) + item['setting_value'][-4:]
                settings[item['setting_name']] = masked_key
            else:
                settings[item['setting_name']] = item.get('setting_value')
        
        return settings
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
async def update_settings(settings: dict = Body(...)):
    """Update application settings"""
    try:
        dynamodb = db.get_dynamodb_client()
        
        # Check if settings table exists
        existing_tables = [table.name for table in dynamodb.tables.all()]
        if 'settings' not in existing_tables:
            # Create settings table
            table = dynamodb.create_table(
                TableName='settings',
                KeySchema=[
                    {'AttributeName': 'setting_name', 'KeyType': 'HASH'},
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'setting_name', 'AttributeType': 'S'},
                ],
                ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
            )
            # Wait for table to be created
            table.meta.client.get_waiter('table_exists').wait(TableName='settings')
        
        # Update settings
        table = dynamodb.Table('settings')
        for key, value in settings.items():
            table.put_item(
                Item={
                    'setting_name': key,
                    'setting_value': value
                }
            )
        
        return {"status": "success", "message": "Settings updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/test-gorqcloud")
async def test_gorqcloud_api():
    """Test the Groq API connection"""
    try:
        from groq import Groq
        import os
        
        # Get API key
        api_key = db.get_gorqcloud_api_key()
        
        if not api_key:
            return {"status": "error", "message": "Groq API key not configured"}
        
        # Set the API key for the Groq client
        os.environ["GROQ_API_KEY"] = api_key
        
        # Initialize the Groq client
        client = Groq(api_key=api_key)
        
        # Make a simple test request
        completion = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "user",
                    "content": "Say hello in one word"
                }
            ],
            temperature=1,
            max_completion_tokens=10,
            top_p=1,
            stream=False
        )
        
        # If we get here, the API call was successful
        return {"status": "success", "message": "Groq API connection successful"}
    except Exception as e:
        return {"status": "error", "message": f"Error testing Groq API: {str(e)}"}