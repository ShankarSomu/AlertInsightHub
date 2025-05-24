#!/bin/bash
set -e

# Install Python deps
pip install --upgrade pip
pip install -r /workspace/requirements.txt

# Install DynamoDB Local
echo "Installing DynamoDB Local..."
mkdir -p ~/dynamodb-local
cd ~/dynamodb-local

if [ ! -f DynamoDBLocal.jar ]; then
  wget https://s3.us-west-2.amazonaws.com/dynamodb-local/dynamodb_local_latest.zip
  unzip dynamodb_local_latest.zip
  rm dynamodb_local_latest.zip
fi

# Start DynamoDB Local on port 8001
echo "Starting DynamoDB Local on port 8001..."
nohup java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -sharedDb -port 8001 > dynamodb.log 2>&1 &

# Set environment variable for DynamoDB Local
export AWS_ENDPOINT_URL=http://localhost:8001

# Start FastAPI app on port 8000
echo "Starting FastAPI app on port 8000..."
cd /workspace
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > fastapi.log 2>&1 &

echo "Services started:"
echo "- DynamoDB Local: http://localhost:8001"
echo "- FastAPI Dashboard: http://localhost:8000"
echo "- API Documentation: http://localhost:8000/docs"