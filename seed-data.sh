#!/bin/bash
# Set AWS environment variables for DynamoDB Local
export AWS_ENDPOINT_URL=http://localhost:8001
export AWS_DEFAULT_REGION=us-east-1
export AWS_ACCESS_KEY_ID=fakeAccessKeyId
export AWS_SECRET_ACCESS_KEY=fakeSecretAccessKey

cd /workspaces/AlertInsightHub
python -m app.seed_data