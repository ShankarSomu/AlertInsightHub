from fastapi import FastAPI
import boto3

app = FastAPI()

dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url='http://localhost:8001',
    region_name='us-west-2',
    aws_access_key_id='dummy',
    aws_secret_access_key='dummy'
)

@app.get("/")
def read_root():
    return {"message": "API is live"}

@app.get("/tables")
def list_tables():
    return {"tables": list(dynamodb.tables.all())}
