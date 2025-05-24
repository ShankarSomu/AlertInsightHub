from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import logging
import os
from . import db
from .models import AlertSummary, ResourceSummary, AlertTypeSummary

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Alert Insight Hub",
    description="Dashboard for AWS cloud alert insights",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    logger.info("Initializing database...")
    try:
        db.create_tables()
        db.seed_sample_data()
        logger.info("Database initialization complete")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        # Continue anyway - might be using AWS DynamoDB

# API Routes
@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Return the dashboard HTML page"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Alert Insight Hub</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
            h1 { color: #333; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
            tr:hover { background-color: #f5f5f5; }
            .medium { color: #ff9900; }
            .high { color: #ff6600; }
            .critical { color: #cc0000; }
            #details, #resource-details { margin-top: 20px; display: none; }
        </style>
    </head>
    <body>
        <h1>AWS Alert Insight Hub</h1>
        
        <h2>Account & Service Summary</h2>
        <table id="summary-table">
            <thead>
                <tr>
                    <th>Account ID</th>
                    <th>Service</th>
                    <th>Total Alerts</th>
                    <th>Medium</th>
                    <th>High</th>
                    <th>Critical</th>
                </tr>
            </thead>
            <tbody id="summary-body"></tbody>
        </table>
        
        <div id="details">
            <h2 id="service-title">Resources</h2>
            <table id="resources-table">
                <thead>
                    <tr>
                        <th>Resource ID</th>
                        <th>Total Alerts</th>
                        <th>Medium</th>
                        <th>High</th>
                        <th>Critical</th>
                    </tr>
                </thead>
                <tbody id="resources-body"></tbody>
            </table>
        </div>
        
        <div id="resource-details">
            <h2 id="resource-title">Alert Types</h2>
            <table id="alerts-table">
                <thead>
                    <tr>
                        <th>Alert Type</th>
                        <th>Total Alerts</th>
                        <th>Medium</th>
                        <th>High</th>
                        <th>Critical</th>
                    </tr>
                </thead>
                <tbody id="alerts-body"></tbody>
            </table>
        </div>
        
        <script>
            // Load summary data
            fetch('/api/summary')
                .then(response => response.json())
                .then(data => {
                    const tbody = document.getElementById('summary-body');
                    data.forEach(item => {
                        const row = document.createElement('tr');
                        row.innerHTML = `
                            <td>${item.account_id}</td>
                            <td><a href="#" class="service-link" data-account="${item.account_id}" data-service="${item.service}">${item.service}</a></td>
                            <td>${item.total_alerts}</td>
                            <td class="medium">${item.medium_alerts}</td>
                            <td class="high">${item.high_alerts}</td>
                            <td class="critical">${item.critical_alerts}</td>
                        `;
                        tbody.appendChild(row);
                    });
                    
                    // Add event listeners to service links
                    document.querySelectorAll('.service-link').forEach(link => {
                        link.addEventListener('click', function(e) {
                            e.preventDefault();
                            const accountId = this.getAttribute('data-account');
                            const service = this.getAttribute('data-service');
                            loadResourceData(accountId, service);
                        });
                    });
                });
                
            // Load resource data for a service
            function loadResourceData(accountId, service) {
                document.getElementById('details').style.display = 'block';
                document.getElementById('resource-details').style.display = 'none';
                document.getElementById('service-title').textContent = `${service} Resources for Account ${accountId}`;
                
                fetch(`/api/service/${accountId}/${service}`)
                    .then(response => response.json())
                    .then(data => {
                        const tbody = document.getElementById('resources-body');
                        tbody.innerHTML = '';
                        data.forEach(item => {
                            const row = document.createElement('tr');
                            row.innerHTML = `
                                <td><a href="#" class="resource-link" data-resource="${item.resource_id}">${item.resource_id}</a></td>
                                <td>${item.total_alerts}</td>
                                <td class="medium">${item.medium_alerts}</td>
                                <td class="high">${item.high_alerts}</td>
                                <td class="critical">${item.critical_alerts}</td>
                            `;
                            tbody.appendChild(row);
                        });
                        
                        // Add event listeners to resource links
                        document.querySelectorAll('.resource-link').forEach(link => {
                            link.addEventListener('click', function(e) {
                                e.preventDefault();
                                const resourceId = this.getAttribute('data-resource');
                                loadAlertData(resourceId);
                            });
                        });
                    });
            }
            
            // Load alert data for a resource
            function loadAlertData(resourceId) {
                document.getElementById('resource-details').style.display = 'block';
                document.getElementById('resource-title').textContent = `Alert Types for Resource ${resourceId}`;
                
                fetch(`/api/resource/${resourceId}`)
                    .then(response => response.json())
                    .then(data => {
                        const tbody = document.getElementById('alerts-body');
                        tbody.innerHTML = '';
                        data.forEach(item => {
                            const row = document.createElement('tr');
                            row.innerHTML = `
                                <td>${item.alert_type}</td>
                                <td>${item.total_alerts}</td>
                                <td class="medium">${item.medium_alerts}</td>
                                <td class="high">${item.high_alerts}</td>
                                <td class="critical">${item.critical_alerts}</td>
                            `;
                            tbody.appendChild(row);
                        });
                    });
            }
        </script>
    </body>
    </html>
    """
    return html_content

@app.get("/api/summary", response_model=list[AlertSummary])
async def get_summary():
    """Get summary of alerts by account and service"""
    try:
        logger.info("Fetching account and service summary")
        return db.get_account_service_summary()
    except Exception as e:
        logger.error(f"Error fetching summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/service/{account_id}/{service}", response_model=list[ResourceSummary])
async def get_service_resources(account_id: str, service: str):
    """Get resources for a specific account and service with alert counts"""
    try:
        logger.info(f"Fetching resources for account {account_id}, service {service}")
        return db.get_service_resources(account_id, service)
    except Exception as e:
        logger.error(f"Error fetching service resources: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/resource/{resource_id}", response_model=list[AlertTypeSummary])
async def get_resource_alerts(resource_id: str):
    """Get alert types and counts for a specific resource"""
    try:
        logger.info(f"Fetching alerts for resource {resource_id}")
        return db.get_resource_alerts(resource_id)
    except Exception as e:
        logger.error(f"Error fetching resource alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)