@echo off
REM Set AWS environment variables for DynamoDB Local
set AWS_ENDPOINT_URL=http://localhost:8001
set AWS_DEFAULT_REGION=us-east-1
set AWS_ACCESS_KEY_ID=fakeAccessKeyId
set AWS_SECRET_ACCESS_KEY=fakeSecretAccessKey

echo Starting FastAPI application...
cd /d %~dp0
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload