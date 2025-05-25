# Alert Insight Hub

A FastAPI application that displays a dashboard for AWS cloud alert insights. The dashboard provides hierarchical visualization of alert data grouped by AWS account, service, and resource.

## Features

- Summary view of alerts by AWS account and service
- Drill-down to view resources affected by alerts
- Further drill-down to view alert types for specific resources
- Classification of alerts by severity (medium, high, critical)
- Local development with DynamoDB Local

## Tech Stack

- FastAPI for backend API
- DynamoDB (local or AWS) for storing alert data
- Pydantic models for schema validation
- Simple HTML/JS frontend for visualization

## Design Architecture

![AlertinsightHubDesignOverview](https://github.com/user-attachments/assets/fbf3a26c-e334-4c42-9175-e5c129231fba)


## Getting Started

### Prerequisites

- Python 3.10+
- Docker (for DynamoDB Local)

### Running the Application

1. Start the devcontainer in VS Code

2. Start the FastAPI application:
   ```
   cd /workspaces/AlertInsightHub
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

3. Access the application:
   - Dashboard: http://localhost:8000/
   - API docs: http://localhost:8000/docs

### API Endpoints

- `/api/summary` - Returns aggregated data by account and service
- `/api/service/{account_id}/{service}` - Returns resources with alert count
- `/api/resource/{resource_id}` - Returns alert types and count

## Sample Data

The application is pre-loaded with sample alert data for demonstration purposes.

## Future Enhancements

- AI integration for automatic grouping and classification of alerts
- Advanced filtering and search capabilities
- User authentication and authorization
- Custom alert thresholds and notifications
