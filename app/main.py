from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import logging
import os
import json
import uuid
from datetime import datetime
from . import db
from .models import AlertSummary, ResourceSummary, AlertTypeSummary
# Import routes after fixing the syntax issues
from .routes import webhook_routes, queue_dashboard, webhook_api, process_routes, data_routes

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

# Set up webhook URL
webhook_url = "http://localhost:8000/api/webhook"
logger.info(f"Local webhook URL: {webhook_url}")
logger.info("For external access, use a service like ngrok or configure your server with a public IP")
logger.info("Example: ngrok http 8000 (then use the generated URL + /api/webhook)")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(webhook_routes.router)
app.include_router(queue_dashboard.router)
app.include_router(webhook_api.router)
app.include_router(process_routes.router)
app.include_router(data_routes.router)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    logger.info("Initializing database...")
    try:
        # Set AWS environment variables for DynamoDB Local
        os.environ["AWS_ENDPOINT_URL"] = "http://localhost:8001"
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
        os.environ["AWS_ACCESS_KEY_ID"] = "fakeAccessKeyId"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "fakeSecretAccessKey"
        
        db.create_tables()
        # Comment out the seed_sample_data call if you're using the external seed_data.py script
        # db.seed_sample_data()
        logger.info("Database initialization complete")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        # Continue anyway - might be using AWS DynamoDB

# API Routes
@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Return the dashboard HTML page"""
    global webhook_url
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
            th { background-color: #f2f2f2; cursor: pointer; position: relative; }
            th:hover { background-color: #e0e0e0; }
            th:after { content: ""; position: absolute; right: 8px; top: 50%; transform: translateY(-50%); }
            th.sort-asc:after { content: "▲"; }
            th.sort-desc:after { content: "▼"; }
            tr:hover { background-color: #f5f5f5; }
            .medium { color: #ff9900; text-decoration: underline; }
            .high { color: #ff6600; text-decoration: underline; }
            .critical { color: #cc0000; text-decoration: underline; }
            .summary-alert, .resource-alert, .alert-detail { cursor: pointer; }
            .summary-alert:hover, .resource-alert:hover, .alert-detail:hover { background-color: #f0f0f0; font-weight: bold; }
            .clickable { position: relative; }
            .clickable:after { content: "👆"; font-size: 10px; position: absolute; top: 0; right: 0; opacity: 0.5; }
            #details, #resource-details, #alert-details { margin-top: 20px; display: none; }
            .modal { display: none; position: fixed; z-index: 1; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.4); }
            .modal-content { background-color: #fefefe; margin: 15% auto; padding: 20px; border: 1px solid #888; width: 80%; max-height: 70vh; overflow-y: auto; }
            .close { color: #aaa; float: right; font-size: 28px; font-weight: bold; cursor: pointer; }
            .close:hover { color: black; }
            .remediation { background-color: #f8f8f8; padding: 10px; border-left: 4px solid #4CAF50; margin-top: 10px; }
            .help-text { background-color: #e9f7fe; padding: 10px; border-radius: 4px; margin-bottom: 15px; }
            .filter-controls { display: flex; flex-wrap: wrap; gap: 15px; margin-bottom: 15px; background-color: #f9f9f9; padding: 10px; border-radius: 4px; }
            .filter-group { display: flex; align-items: center; gap: 5px; }
            select { padding: 5px; border-radius: 3px; border: 1px solid #ddd; }
            label { font-weight: bold; }
            .chart-container { display: flex; gap: 20px; margin-bottom: 20px; }
            .chart-box { flex: 1; background-color: #fff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); padding: 15px; height: 300px; }
            .chart-title { font-size: 16px; font-weight: bold; margin-bottom: 10px; }
            .nav-tabs { display: flex; border-bottom: 1px solid #ddd; margin-bottom: 20px; }
            .nav-tab { padding: 10px 15px; cursor: pointer; }
            .nav-tab.active { border: 1px solid #ddd; border-bottom: none; border-radius: 4px 4px 0 0; background-color: #fff; font-weight: bold; }
            .nav-tab:hover:not(.active) { background-color: #f5f5f5; }
            .action-btn { background-color: #0078d7; color: white; border: none; padding: 8px 15px; border-radius: 4px; cursor: pointer; }
            .action-btn:hover { background-color: #005a9e; }
            .action-btn.danger { background-color: #d9534f; }
            .action-btn.danger:hover { background-color: #c9302c; }
            .webhook-url-container { background-color: #f0f7ff; border-left: 4px solid #0078d7; padding: 15px; margin-bottom: 20px; border-radius: 4px; }
            .webhook-url { font-family: monospace; background-color: #fff; padding: 10px; border: 1px solid #ddd; border-radius: 4px; margin: 10px 0; word-break: break-all; }
            .copy-btn { background-color: #0078d7; color: white; border: none; padding: 5px 15px; border-radius: 4px; cursor: pointer; }
            .copy-btn:hover { background-color: #005a9e; }
        </style>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body>
        <h1>AWS Alert Insight Hub</h1>
        
        <div class="nav-tabs">
            <div class="nav-tab active">Main Dashboard</div>
            <div class="nav-tab" onclick="window.location.href='/queue'">Queue Dashboard</div>
            <div style="margin-left: auto; display: flex; gap: 10px;">
                <button onclick="loadSampleAlerts()" class="action-btn">Load Sample Alerts</button>
                <button onclick="clearAlerts()" class="action-btn danger">Clear Alerts</button>
            </div>
        </div>
        
        <script>
            function loadSampleAlerts() {
                if (confirm('Load sample alert data? This will replace any existing alerts.')) {
                    fetch('/api/data/seed/alerts', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    })
                    .then(response => response.json())
                    .then(data => {
                        alert(data.message);
                        // Reload the page to show updated data
                        window.location.reload();
                    })
                    .catch(error => {
                        console.error('Error loading sample data:', error);
                        alert('Error loading sample data');
                    });
                }
            }
            
            function clearAlerts() {
                if (confirm('Are you sure you want to clear all alerts? This cannot be undone.')) {
                    fetch('/api/data/clear/alerts', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    })
                    .then(response => response.json())
                    .then(data => {
                        alert(data.message);
                        // Reload the page to show updated data
                        window.location.reload();
                    })
                    .catch(error => {
                        console.error('Error clearing data:', error);
                        alert('Error clearing data');
                    });
                }
            }
        </script>
        
        <div class="webhook-url-container">
            <h3>Inbound Webhook URL for Postmark Integration:</h3>
            <div class="webhook-url" id="webhook-url">WEBHOOK_URL_PLACEHOLDER</div>
            <button onclick="copyWebhookUrl()" class="copy-btn">Copy URL</button>
            <p style="margin-top: 10px; font-style: italic;">Note: This is a local URL. For external access, use a service like ngrok (e.g., run <code>ngrok http 8000</code> and use the generated URL + /api/webhook)</p>
        </div>
        
        <div class="help-text">
            <p><strong>Tips:</strong> 
                Use the filters to focus on specific accounts, services, or regions.
                Click on column headers to sort the table.
                Click on service names to view resources. 
                Click on alert numbers to view details. 
                Hold <kbd>Shift</kbd> and click on a severity number to see all alerts of that severity.
            </p>
        </div>
        
        <div class="chart-container">
            <div class="chart-box">
                <div class="chart-title">Alerts by Service</div>
                <canvas id="serviceChart"></canvas>
            </div>
            <div class="chart-box">
                <div class="chart-title">Alerts by Severity</div>
                <canvas id="severityChart"></canvas>
            </div>
        </div>
        
        <h2>Account & Service Summary</h2>
        <div class="filter-controls">
            <div class="filter-group">
                <label for="account-filter">Account:</label>
                <select id="account-filter">
                    <option value="all">All Accounts</option>
                </select>
            </div>
            <div class="filter-group">
                <label for="service-filter">Service:</label>
                <select id="service-filter">
                    <option value="all">All Services</option>
                </select>
            </div>
            <div class="filter-group">
                <label for="region-filter">Region:</label>
                <select id="region-filter">
                    <option value="all">All Regions</option>
                </select>
            </div>
        </div>
        <table id="summary-table">
            <thead>
                <tr>
                    <th data-sort="account">Account ID ▲▼</th>
                    <th data-sort="service">Service ▲▼</th>
                    <th data-sort="region">Region ▲▼</th>
                    <th data-sort="total">Total Alerts ▲▼</th>
                    <th data-sort="medium">Medium ▲▼</th>
                    <th data-sort="high">High ▲▼</th>
                    <th data-sort="critical">Critical ▲▼</th>
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
        
        <!-- Alert Details Modal -->
        <div id="alert-modal" class="modal">
            <div class="modal-content">
                <span class="close">&times;</span>
                <h2 id="alert-modal-title">Alert Details</h2>
                <div id="alert-modal-content"></div>
            </div>
        </div>
        
        <script>
            // Global variables to track current context
            let currentResourceId = '';
            let currentAlertType = '';
            
            // Modal elements
            const modal = document.getElementById('alert-modal');
            const modalClose = document.querySelector('.close');
            const modalTitle = document.getElementById('alert-modal-title');
            const modalContent = document.getElementById('alert-modal-content');
            
            // Function to show all alerts of a specific severity
            function showAllSeverityAlerts(severity) {
                fetch(`/api/summary/${severity}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.length === 0) {
                            modalTitle.textContent = 'No Alerts Found';
                            modalContent.innerHTML = '<p>No alerts match the selected severity.</p>';
                        } else {
                            modalTitle.textContent = `All ${severity.charAt(0).toUpperCase() + severity.slice(1)} Severity Alerts`;
                            
                            // Group alerts by service
                            const serviceGroups = {};
                            data.forEach(alert => {
                                if (!serviceGroups[alert.service]) {
                                    serviceGroups[alert.service] = [];
                                }
                                serviceGroups[alert.service].push(alert);
                            });
                            
                            let content = '';
                            Object.keys(serviceGroups).sort().forEach(service => {
                                content += `<h3>${service} Service</h3>`;
                                
                                serviceGroups[service].forEach((alert, index) => {
                                    const timestamp = new Date(alert.timestamp).toLocaleString();
                                    content += `
                                        <div style="margin-bottom: 20px; ${index > 0 ? 'border-top: 1px solid #eee; padding-top: 15px;' : ''}">
                                            <p><strong>Resource:</strong> ${alert.resource_id}</p>
                                            <p><strong>Alert Type:</strong> ${alert.alert_type}</p>
                                            <p><strong>Timestamp:</strong> ${timestamp}</p>
                                            <p><strong>Message:</strong> ${alert.message}</p>
                                            <div class="remediation">
                                                <h4>Recommended Action:</h4>
                                                <p>${alert.remediation}</p>
                                            </div>
                                        </div>
                                    `;
                                });
                            });
                            
                            modalContent.innerHTML = content;
                        }
                        
                        modal.style.display = 'block';
                    })
                    .catch(error => {
                        modalTitle.textContent = 'Error';
                        modalContent.innerHTML = `<p>Failed to load alert details: ${error.message}</p>`;
                        modal.style.display = 'block';
                    });
            }
            
            // Function to show filtered alerts for specific account, service, region and severity
            function showFilteredAlerts(accountId, service, region, severity) {
                fetch(`/api/alerts/filtered?account=${accountId}&service=${service}&region=${region}&severity=${severity}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.length === 0) {
                            modalTitle.textContent = 'No Alerts Found';
                            modalContent.innerHTML = '<p>No alerts match the selected criteria.</p>';
                        } else {
                            modalTitle.textContent = `${severity.charAt(0).toUpperCase() + severity.slice(1)} Alerts for ${service} in ${region}`;
                            
                            let content = '';
                            data.forEach((alert, index) => {
                                const timestamp = new Date(alert.timestamp).toLocaleString();
                                content += `
                                    <div style="margin-bottom: 20px; ${index > 0 ? 'border-top: 1px solid #eee; padding-top: 15px;' : ''}">
                                        <p><strong>Resource:</strong> ${alert.resource_id}</p>
                                        <p><strong>Alert Type:</strong> ${alert.alert_type}</p>
                                        <p><strong>Timestamp:</strong> ${timestamp}</p>
                                        <p><strong>Message:</strong> ${alert.message}</p>
                                        <div class="remediation">
                                            <h4>Recommended Action:</h4>
                                            <p>${alert.remediation}</p>
                                        </div>
                                    </div>
                                `;
                            });
                            
                            modalContent.innerHTML = content;
                        }
                        
                        modal.style.display = 'block';
                    })
                    .catch(error => {
                        modalTitle.textContent = 'Error';
                        modalContent.innerHTML = `<p>Failed to load alert details: ${error.message}</p>`;
                        modal.style.display = 'block';
                    });
            }
            
            // Close modal when clicking X
            modalClose.onclick = function() {
                modal.style.display = 'none';
            }
            
            // Close modal when clicking outside
            window.onclick = function(event) {
                if (event.target == modal) {
                    modal.style.display = 'none';
                }
            }
            
            // Global variables for data and filters
            let summaryData = [];
            let accounts = new Set();
            let services = new Set();
            let regions = new Set();
            let currentSortField = 'account';
            let currentSortOrder = 'asc';
            
            // Function to initialize charts
            function initializeCharts(data) {
                // Process data for charts
                const serviceData = {};
                const severityData = {
                    medium: 0,
                    high: 0,
                    critical: 0
                };
                
                data.forEach(item => {
                    // Aggregate by service
                    if (!serviceData[item.service]) {
                        serviceData[item.service] = 0;
                    }
                    serviceData[item.service] += item.total_alerts;
                    
                    // Aggregate by severity
                    severityData.medium += item.medium_alerts;
                    severityData.high += item.high_alerts;
                    severityData.critical += item.critical_alerts;
                });
                
                // Create service chart
                const serviceCtx = document.getElementById('serviceChart').getContext('2d');
                const serviceChart = new Chart(serviceCtx, {
                    type: 'bar',
                    data: {
                        labels: Object.keys(serviceData),
                        datasets: [{
                            label: 'Total Alerts',
                            data: Object.values(serviceData),
                            backgroundColor: [
                                'rgba(54, 162, 235, 0.6)',
                                'rgba(75, 192, 192, 0.6)',
                                'rgba(153, 102, 255, 0.6)',
                                'rgba(255, 159, 64, 0.6)',
                                'rgba(255, 99, 132, 0.6)'
                            ],
                            borderColor: [
                                'rgba(54, 162, 235, 1)',
                                'rgba(75, 192, 192, 1)',
                                'rgba(153, 102, 255, 1)',
                                'rgba(255, 159, 64, 1)',
                                'rgba(255, 99, 132, 1)'
                            ],
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        aspectRatio: 2,
                        scales: {
                            y: {
                                beginAtZero: true
                            }
                        },
                        onClick: (event, elements) => {
                            if (elements.length > 0) {
                                const index = elements[0].index;
                                const service = Object.keys(serviceData)[index];
                                
                                // Filter the table to show only this service
                                document.getElementById('service-filter').value = service;
                                applyFilters();
                            }
                        }
                    }
                });
                
                // Create severity chart
                const severityCtx = document.getElementById('severityChart').getContext('2d');
                const severityChart = new Chart(severityCtx, {
                    type: 'doughnut',
                    data: {
                        labels: ['Medium', 'High', 'Critical'],
                        datasets: [{
                            data: [severityData.medium, severityData.high, severityData.critical],
                            backgroundColor: [
                                'rgba(255, 206, 86, 0.6)',
                                'rgba(255, 159, 64, 0.6)',
                                'rgba(255, 99, 132, 0.6)'
                            ],
                            borderColor: [
                                'rgba(255, 206, 86, 1)',
                                'rgba(255, 159, 64, 1)',
                                'rgba(255, 99, 132, 1)'
                            ],
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        aspectRatio: 1.5,
                        plugins: {
                            legend: {
                                position: 'right'
                            }
                        },
                        onClick: (event, elements) => {
                            if (elements.length > 0) {
                                const index = elements[0].index;
                                const severities = ['medium', 'high', 'critical'];
                                const severity = severities[index];
                                
                                // Show all alerts of this severity
                                showAllSeverityAlerts(severity);
                            }
                        }
                    }
                });
                
                // Store charts in global variables for later updates
                window.serviceChart = serviceChart;
                window.severityChart = severityChart;
            }
            
            // Function to update charts when filters change
            function updateCharts(data) {
                if (!window.serviceChart || !window.severityChart) {
                    initializeCharts(data);
                    return;
                }
                
                // Process data for charts
                const serviceData = {};
                const severityData = {
                    medium: 0,
                    high: 0,
                    critical: 0
                };
                
                data.forEach(item => {
                    // Aggregate by service
                    if (!serviceData[item.service]) {
                        serviceData[item.service] = 0;
                    }
                    serviceData[item.service] += item.total_alerts;
                    
                    // Aggregate by severity
                    severityData.medium += item.medium_alerts;
                    severityData.high += item.high_alerts;
                    severityData.critical += item.critical_alerts;
                });
                
                // Update service chart
                window.serviceChart.data.labels = Object.keys(serviceData);
                window.serviceChart.data.datasets[0].data = Object.values(serviceData);
                window.serviceChart.update();
                
                // Update severity chart
                window.severityChart.data.datasets[0].data = [
                    severityData.medium,
                    severityData.high,
                    severityData.critical
                ];
                window.severityChart.update();
            }
            
            // Load summary data
            fetch('/api/summary')
                .then(response => response.json())
                .then(data => {
                    console.log("Received data:", data); // Debug log
                    summaryData = data;
                    
                    // Initialize charts
                    initializeCharts(data);
                    
                    // Extract unique accounts, services, and regions for filters
                    data.forEach(item => {
                        accounts.add(item.account_id);
                        services.add(item.service);
                        regions.add(item.region || 'us-east-1');
                    });
                    
                    // Populate filter dropdowns
                    const accountFilter = document.getElementById('account-filter');
                    Array.from(accounts).sort().forEach(account => {
                        const option = document.createElement('option');
                        option.value = account;
                        option.textContent = account;
                        accountFilter.appendChild(option);
                    });
                    
                    const serviceFilter = document.getElementById('service-filter');
                    Array.from(services).sort().forEach(service => {
                        const option = document.createElement('option');
                        option.value = service;
                        option.textContent = service;
                        serviceFilter.appendChild(option);
                    });
                    
                    const regionFilter = document.getElementById('region-filter');
                    Array.from(regions).sort().forEach(region => {
                        const option = document.createElement('option');
                        option.value = region;
                        option.textContent = region;
                        regionFilter.appendChild(option);
                    });
                    
                    // Initial render
                    renderSummaryTable(data);
                    
                    // Set up event listeners for filters
                    document.getElementById('account-filter').addEventListener('change', applyFilters);
                    document.getElementById('service-filter').addEventListener('change', applyFilters);
                    document.getElementById('region-filter').addEventListener('change', applyFilters);
                    
                    // Add click handlers for table headers
                    document.querySelectorAll('#summary-table th[data-sort]').forEach(header => {
                        header.addEventListener('click', function() {
                            const sortField = this.getAttribute('data-sort');
                            if (currentSortField === sortField) {
                                // Toggle sort order if clicking the same header
                                currentSortOrder = currentSortOrder === 'asc' ? 'desc' : 'asc';
                            } else {
                                // Set new sort field
                                currentSortField = sortField;
                                currentSortOrder = 'asc';
                            }
                            
                            // Update header styles
                            document.querySelectorAll('#summary-table th').forEach(th => {
                                th.classList.remove('sort-asc', 'sort-desc');
                            });
                            this.classList.add(currentSortOrder === 'asc' ? 'sort-asc' : 'sort-desc');
                            
                            applyFilters();
                        });
                    });
                });
                
            // Function to render the summary table with filtered and sorted data
            function renderSummaryTable(data) {
                const tbody = document.getElementById('summary-body');
                tbody.innerHTML = '';
                
                console.log("Rendering table with data:", data); // Debug log
                
                // Update sort indicators on headers
                document.querySelectorAll('#summary-table th[data-sort]').forEach(header => {
                    header.classList.remove('sort-asc', 'sort-desc');
                    if (header.getAttribute('data-sort') === currentSortField) {
                        header.classList.add(currentSortOrder === 'asc' ? 'sort-asc' : 'sort-desc');
                    }
                });
                
                // Show a message if no data is available
                if (data.length === 0) {
                    const row = document.createElement('tr');
                    row.innerHTML = `<td colspan="7" style="text-align: center; padding: 20px;">No data available. Please check your DynamoDB connection or seed some sample data.</td>`;
                    tbody.appendChild(row);
                    return;
                }
                
                data.forEach(item => {
                    const row = document.createElement('tr');
                    const region = item.region || 'us-east-1';
                    row.innerHTML = `
                        <td>${item.account_id}</td>
                        <td><a href="#" class="service-link" data-account="${item.account_id}" data-service="${item.service}" data-region="${region}">${item.service}</a></td>
                        <td>${region}</td>
                        <td>${item.total_alerts}</td>
                        <td class="medium summary-alert" data-account="${item.account_id}" data-service="${item.service}" data-region="${region}" data-severity="medium">${item.medium_alerts}</td>
                        <td class="high summary-alert" data-account="${item.account_id}" data-service="${item.service}" data-region="${region}" data-severity="high">${item.high_alerts}</td>
                        <td class="critical summary-alert" data-account="${item.account_id}" data-service="${item.service}" data-region="${region}" data-severity="critical">${item.critical_alerts}</td>
                    `;
                    tbody.appendChild(row);
                });
                
                // Add event listeners to service links
                document.querySelectorAll('.service-link').forEach(link => {
                    link.addEventListener('click', function(e) {
                        e.preventDefault();
                        const accountId = this.getAttribute('data-account');
                        const service = this.getAttribute('data-service');
                        const region = this.getAttribute('data-region');
                        loadResourceData(accountId, service, null, region);
                    });
                });
                
                // Add event listeners to summary alert numbers
                document.querySelectorAll('.summary-alert').forEach(cell => {
                    if (parseInt(cell.textContent) > 0) {
                        cell.style.cursor = 'pointer';
                        cell.addEventListener('click', function(e) {
                            // If Shift key is pressed, show all alerts of this severity
                            if (e.shiftKey) {
                                const severity = this.getAttribute('data-severity');
                                showAllSeverityAlerts(severity);
                            } else {
                                // Normal click - show filtered alerts for this specific combination
                                const accountId = this.getAttribute('data-account');
                                const service = this.getAttribute('data-service');
                                const severity = this.getAttribute('data-severity');
                                const region = this.getAttribute('data-region');
                                
                                // Show modal with filtered alerts
                                showFilteredAlerts(accountId, service, region, severity);
                            }
                        });
                    }
                });
            }
            
            // Function to apply filters and sorting
            function applyFilters() {
                const accountFilter = document.getElementById('account-filter').value;
                const serviceFilter = document.getElementById('service-filter').value;
                const regionFilter = document.getElementById('region-filter').value;
                
                // Filter data
                let filteredData = summaryData.filter(item => {
                    const itemRegion = item.region || 'us-east-1';
                    return (accountFilter === 'all' || item.account_id === accountFilter) &&
                           (serviceFilter === 'all' || item.service === serviceFilter) &&
                           (regionFilter === 'all' || itemRegion === regionFilter);
                });
                
                // Sort data
                filteredData.sort((a, b) => {
                    let valueA, valueB;
                    
                    switch(currentSortField) {
                        case 'account':
                            valueA = a.account_id;
                            valueB = b.account_id;
                            break;
                        case 'service':
                            valueA = a.service;
                            valueB = b.service;
                            break;
                        case 'region':
                            valueA = a.region || 'us-east-1';
                            valueB = b.region || 'us-east-1';
                            break;
                        case 'total':
                            valueA = a.total_alerts;
                            valueB = b.total_alerts;
                            break;
                        case 'medium':
                            valueA = a.medium_alerts;
                            valueB = b.medium_alerts;
                            break;
                        case 'high':
                            valueA = a.high_alerts;
                            valueB = b.high_alerts;
                            break;
                        case 'critical':
                            valueA = a.critical_alerts;
                            valueB = b.critical_alerts;
                            break;
                        default:
                            valueA = a.account_id;
                            valueB = b.account_id;
                    }
                    
                    // For string comparison
                    if (typeof valueA === 'string') {
                        if (currentSortOrder === 'asc') {
                            return valueA.localeCompare(valueB);
                        } else {
                            return valueB.localeCompare(valueA);
                        }
                    } 
                    // For number comparison
                    else {
                        if (currentSortOrder === 'asc') {
                            return valueA - valueB;
                        } else {
                            return valueB - valueA;
                        }
                    }
                });
                
                // Render the filtered and sorted data
                renderSummaryTable(filteredData);
                
                // Update charts with filtered data
                updateCharts(filteredData);
            }
                
            // Load resource data for a service
            function loadResourceData(accountId, service, highlightSeverity = null, region = null) {
                document.getElementById('details').style.display = 'block';
                document.getElementById('resource-details').style.display = 'none';
                
                let title = `${service} Resources for Account ${accountId}`;
                if (region) {
                    title += ` in ${region}`;
                }
                document.getElementById('service-title').textContent = title;
                
                let url = `/api/service/${accountId}/${service}`;
                if (region) {
                    url += `?region=${region}`;
                }
                
                fetch(url)
                    .then(response => response.json())
                    .then(data => {
                        console.log("Resource data:", data);
                        const tbody = document.getElementById('resources-body');
                        tbody.innerHTML = '';
                        
                        // Ensure data is an array and all items have required properties
                        const dataArray = Array.isArray(data) ? data : [data];
                        
                        if (dataArray.length === 0) {
                            const row = document.createElement('tr');
                            row.innerHTML = `<td colspan="5" style="text-align: center; padding: 20px;">No resources found for this service.</td>`;
                            tbody.appendChild(row);
                            return;
                        }
                        
                        dataArray.forEach(item => {
                            // Ensure all required properties exist
                            item = {
                                resource_id: item.resource_id || 'Unknown',
                                total_alerts: item.total_alerts || 0,
                                medium_alerts: item.medium_alerts || 0,
                                high_alerts: item.high_alerts || 0,
                                critical_alerts: item.critical_alerts || 0,
                                ...item
                            };
                            const row = document.createElement('tr');
                            row.innerHTML = `
                                <td><a href="#" class="resource-link" data-resource="${item.resource_id}">${item.resource_id}</a></td>
                                <td>${item.total_alerts}</td>
                                <td class="medium resource-alert" data-resource="${item.resource_id}" data-severity="medium">${item.medium_alerts}</td>
                                <td class="high resource-alert" data-resource="${item.resource_id}" data-severity="high">${item.high_alerts}</td>
                                <td class="critical resource-alert" data-resource="${item.resource_id}" data-severity="critical">${item.critical_alerts}</td>
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
                        
                        // Add event listeners to resource alert numbers
                        document.querySelectorAll('.resource-alert').forEach(cell => {
                            if (parseInt(cell.textContent) > 0) {
                                cell.style.cursor = 'pointer';
                                cell.addEventListener('click', function() {
                                    const resourceId = this.getAttribute('data-resource');
                                    loadAlertData(resourceId, this.getAttribute('data-severity'));
                                });
                            }
                        });
                        
                        // If a specific severity was clicked in the summary, highlight those cells
                        if (highlightSeverity) {
                            document.querySelectorAll(`.resource-alert[data-severity="${highlightSeverity}"]`).forEach(cell => {
                                if (parseInt(cell.textContent) > 0) {
                                    cell.style.backgroundColor = '#fffacd'; // Light yellow highlight
                                }
                            });
                        }
                    });
            }
            
            // Load alert data for a resource
            function loadAlertData(resourceId, highlightSeverity = null) {
                document.getElementById('resource-details').style.display = 'block';
                document.getElementById('resource-title').textContent = `Alert Types for Resource ${resourceId}`;
                currentResourceId = resourceId;
                
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
                                <td class="medium alert-detail" data-type="${item.alert_type}" data-severity="medium">${item.medium_alerts}</td>
                                <td class="high alert-detail" data-type="${item.alert_type}" data-severity="high">${item.high_alerts}</td>
                                <td class="critical alert-detail" data-type="${item.alert_type}" data-severity="critical">${item.critical_alerts}</td>
                            `;
                            tbody.appendChild(row);
                        });
                        
                        // Add event listeners to severity cells
                        document.querySelectorAll('.alert-detail').forEach(cell => {
                            if (parseInt(cell.textContent) > 0) {
                                cell.style.cursor = 'pointer';
                                cell.addEventListener('click', function() {
                                    const alertType = this.getAttribute('data-type');
                                    const severity = this.getAttribute('data-severity');
                                    showAlertDetails(currentResourceId, alertType, severity);
                                });
                            }
                        });
                        
                        // If a specific severity was clicked in the resources view, highlight those cells and show details
                        if (highlightSeverity) {
                            document.querySelectorAll(`.alert-detail[data-severity="${highlightSeverity}"]`).forEach(cell => {
                                if (parseInt(cell.textContent) > 0) {
                                    cell.style.backgroundColor = '#fffacd'; // Light yellow highlight
                                    
                                    // Automatically show details for the first highlighted alert type with this severity
                                    if (data.some(item => item[`${highlightSeverity}_alerts`] > 0)) {
                                        const firstAlertType = data.find(item => item[`${highlightSeverity}_alerts`] > 0).alert_type;
                                        setTimeout(() => {
                                            showAlertDetails(resourceId, firstAlertType, highlightSeverity);
                                        }, 500);
                                    }
                                }
                            });
                        }
                    });
            }
            
            // Show alert details with remediation actions
            // Function to copy webhook URL to clipboard
            function copyWebhookUrl() {
                const webhookUrl = document.getElementById('webhook-url').textContent;
                navigator.clipboard.writeText(webhookUrl).then(() => {
                    alert('Webhook URL copied to clipboard!');
                }).catch(err => {
                    console.error('Failed to copy: ', err);
                });
            }
            
            function showAlertDetails(resourceId, alertType, severity) {
                fetch(`/api/alerts/${resourceId}/${alertType}/${severity}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.length === 0) {
                            modalTitle.textContent = 'No Alerts Found';
                            modalContent.innerHTML = '<p>No alerts match the selected criteria.</p>';
                        } else {
                            modalTitle.textContent = `${severity.charAt(0).toUpperCase() + severity.slice(1)} ${alertType} Alerts for ${resourceId}`;
                            
                            let content = '';
                            data.forEach((alert, index) => {
                                const timestamp = new Date(alert.timestamp).toLocaleString();
                                content += `
                                    <div style="margin-bottom: 20px; ${index > 0 ? 'border-top: 1px solid #eee; padding-top: 15px;' : ''}">
                                        <p><strong>Alert ID:</strong> ${alert.id}</p>
                                        <p><strong>Service:</strong> ${alert.service}</p>
                                        <p><strong>Timestamp:</strong> ${timestamp}</p>
                                        <p><strong>Message:</strong> ${alert.message}</p>
                                        <div class="remediation">
                                            <h4>Recommended Action:</h4>
                                            <p>${alert.remediation}</p>
                                        </div>
                                    </div>
                                `;
                            });
                            
                            modalContent.innerHTML = content;
                        }
                        
                        modal.style.display = 'block';
                    })
                    .catch(error => {
                        modalTitle.textContent = 'Error';
                        modalContent.innerHTML = `<p>Failed to load alert details: ${error.message}</p>`;
                        modal.style.display = 'block';
                    });
            }
        </script>
    </body>
    </html>
    """
    # Replace the webhook URL placeholder with the actual URL
    html_content = html_content.replace("WEBHOOK_URL_PLACEHOLDER", webhook_url)
    return html_content

@app.get("/api/summary", response_model=list[AlertSummary])
async def get_summary():
    """Get summary of alerts by account and service"""
    try:
        logger.info("Fetching account and service summary")
        result = db.get_account_service_summary()
        logger.info(f"Summary data count: {len(result)}")
        return result
    except Exception as e:
        logger.error(f"Error fetching summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/service/{account_id}/{service}", response_model=list[ResourceSummary])
async def get_service_resources(account_id: str, service: str, region: str = None):
    """Get resources for a specific account and service with alert counts"""
    try:
        logger.info(f"Fetching resources for account {account_id}, service {service}, region {region}")
        result = db.get_service_resources(account_id, service, region)
        logger.info(f"Found {len(result)} resources")
        return result
    except Exception as e:
        logger.error(f"Error fetching service resources: {e}")
        # Return a default item instead of raising an exception
        return [{
            'resource_id': f"error-{service}",
            'service': service,
            'region': region or 'us-east-1',
            'total_alerts': 0,
            'medium_alerts': 0,
            'high_alerts': 0,
            'critical_alerts': 0
        }]

@app.get("/api/summary/{severity}")
async def get_summary_by_severity(severity: str):
    """Get all alerts of a specific severity across all accounts and services"""
    try:
        logger.info(f"Fetching all {severity} alerts")
        return db.get_alerts_by_severity(severity)
    except Exception as e:
        logger.error(f"Error fetching alerts by severity: {e}")
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

@app.get("/api/alerts/{resource_id}/{alert_type}/{severity}")
async def get_alert_details(resource_id: str, alert_type: str, severity: str):
    """Get detailed information about specific alerts including remediation actions"""
    try:
        logger.info(f"Fetching alert details for resource {resource_id}, type {alert_type}, severity {severity}")
        return db.get_alert_details(resource_id, alert_type, severity)
    except Exception as e:
        logger.error(f"Error fetching alert details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/alerts/filtered")
async def get_filtered_alerts(account: str, service: str, region: str, severity: str):
    """Get alerts filtered by account, service, region and severity"""
    try:
        logger.info(f"Fetching filtered alerts for account {account}, service {service}, region {region}, severity {severity}")
        return db.get_filtered_alerts(account, service, region, severity)
    except Exception as e:
        logger.error(f"Error fetching filtered alerts: {e}")
        return []

@app.post("/api/webhook")
async def webhook_handler(request: Request):
    """Handle inbound webhook from Postmark"""
    try:
        data = await request.json()
        logger.info(f"Received webhook data: {data}")
        
        # Store the webhook data in a single table
        webhook_id = str(uuid.uuid4())
        current_time = datetime.now()
        current_date = current_time.strftime("%Y-%m-%d")
        timestamp_iso = current_time.isoformat()
        
        # Create queue item with pending status and raw data
        queue_item = {
            "id": webhook_id,
            "timestamp": timestamp_iso,
            "date": current_date,
            "status": "pending",
            "source": "postmark",
            "processed_at": None,
            "raw_data": data  # Include raw data directly in the queue item
        }
        
        # Save to queue table
        dynamodb = db.get_dynamodb_client()
        queue_table = dynamodb.Table('webhook_queue')
        queue_table.put_item(Item=queue_item)
        logger.info(f"Created queue item with pending status: {webhook_id}")
        
        # Return immediately with pending status
        return {
            "status": "success", 
            "message": "Webhook received and queued for processing", 
            "webhook_id": webhook_id
        }
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)