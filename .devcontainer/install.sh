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
nohup java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -sharedDb -port 8001 -inMemory > ~/dynamodb.log 2>&1 &

# Set environment variable for DynamoDB Local
export AWS_ENDPOINT_URL=http://localhost:8001

# Create a simple test script to verify connectivity
cat > ~/test-connectivity.sh << 'EOL'
#!/bin/bash
echo "Testing connectivity..."
echo "DynamoDB Local:"
curl -s http://localhost:8001 || echo "Failed to connect to DynamoDB Local"
echo ""
echo "FastAPI:"
curl -s http://localhost:8000 || echo "Failed to connect to FastAPI"
EOL

chmod +x ~/test-connectivity.sh

echo "DynamoDB Local started on port 8001"
echo "FastAPI will start automatically in the terminal"
echo ""
echo "To test connectivity, run: ~/test-connectivity.sh"
echo ""
echo "Services:"
echo "- DynamoDB Local: http://localhost:8001"
echo "- FastAPI Dashboard: http://localhost:8000"
echo "- API Documentation: http://localhost:8000/docs"