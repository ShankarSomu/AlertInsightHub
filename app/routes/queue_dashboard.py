"""
Routes for webhook queue dashboard
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
import logging
import json
from datetime import datetime, timedelta
from .. import db

router = APIRouter(prefix="/queue", tags=["queue"])
logger = logging.getLogger(__name__)

@router.get("/", response_class=HTMLResponse)
async def get_queue_dashboard():
    """Return the queue dashboard HTML page"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Webhook Queue Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
            h1 { color: #333; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; cursor: pointer; position: relative; }
            th:hover { background-color: #e0e0e0; }
            tr:hover { background-color: #f5f5f5; }
            .pending { color: #ff9900; }
            .processed { color: #4CAF50; }
            .error { color: #cc0000; }
            .chart-container { display: flex; gap: 20px; margin-bottom: 20px; }
            .chart-box { flex: 1; background-color: #fff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); padding: 15px; height: 300px; }
            .chart-title { font-size: 16px; font-weight: bold; margin-bottom: 10px; }
            .stats-container { display: flex; gap: 20px; margin-bottom: 20px; flex-wrap: wrap; }
            .stat-box { flex: 1; min-width: 200px; background-color: #fff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); padding: 15px; text-align: center; }
            .stat-title { font-size: 14px; color: #666; }
            .stat-value { font-size: 24px; font-weight: bold; margin: 10px 0; }
            .stat-pending { color: #ff9900; }
            .stat-processed { color: #4CAF50; }
            .stat-error { color: #cc0000; }
            .stat-total { color: #0078d7; }
            .filter-controls { display: flex; flex-wrap: wrap; gap: 15px; margin-bottom: 15px; background-color: #f9f9f9; padding: 10px; border-radius: 4px; }
            .filter-group { display: flex; align-items: center; gap: 5px; }
            select, input { padding: 5px; border-radius: 3px; border: 1px solid #ddd; }
            button { background-color: #0078d7; color: white; border: none; padding: 5px 15px; border-radius: 4px; cursor: pointer; }
            button:hover { background-color: #005a9e; }
            .nav-tabs { display: flex; border-bottom: 1px solid #ddd; margin-bottom: 20px; }
            .nav-tab { padding: 10px 15px; cursor: pointer; }
            .nav-tab.active { border: 1px solid #ddd; border-bottom: none; border-radius: 4px 4px 0 0; background-color: #fff; font-weight: bold; }
            .nav-tab:hover:not(.active) { background-color: #f5f5f5; }
        </style>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body>
        <h1>Webhook Queue Dashboard</h1>
        
        <div class="nav-tabs">
            <div class="nav-tab" onclick="window.location.href='/'">Main Dashboard</div>
            <div class="nav-tab active">Queue Dashboard</div>
            <div style="margin-left: auto; display: flex; gap: 10px;">
                <button onclick="processWebhooks()" class="action-btn">Process Pending Webhooks</button>
                <button onclick="loadSampleWebhooks()" class="action-btn">Load Sample Webhooks</button>
                <button onclick="clearWebhooks()" class="action-btn danger">Clear Webhooks</button>
            </div>
        </div>
        
        <div class="chart-container">
            <div class="chart-box">
                <div class="chart-title">Webhook Status Distribution</div>
                <canvas id="statusChart"></canvas>
            </div>
            <div class="chart-box">
                <div class="chart-title">Webhooks by Date</div>
                <canvas id="dateChart"></canvas>
            </div>
        </div>
        
        <div class="stats-container">
            <div class="stat-box">
                <div class="stat-title">Total Webhooks</div>
                <div class="stat-value stat-total" id="total-count">0</div>
            </div>
            <div class="stat-box">
                <div class="stat-title">Pending</div>
                <div class="stat-value stat-pending" id="pending-count">0</div>
            </div>
            <div class="stat-box">
                <div class="stat-title">Processed</div>
                <div class="stat-value stat-processed" id="processed-count">0</div>
            </div>
            <div class="stat-box">
                <div class="stat-title">Error</div>
                <div class="stat-value stat-error" id="error-count">0</div>
            </div>
        </div>
        
        <div class="filter-controls">
            <div class="filter-group">
                <label for="date-filter">Date:</label>
                <input type="date" id="date-filter">
            </div>
            <div class="filter-group">
                <label for="status-filter">Status:</label>
                <select id="status-filter">
                    <option value="all">All Statuses</option>
                    <option value="pending">Pending</option>
                    <option value="processed">Processed</option>
                    <option value="error">Error</option>
                </select>
            </div>
            <button id="apply-filters">Apply Filters</button>
            <button id="reset-filters">Reset</button>
        </div>
        
        <h2>Webhook Queue Items</h2>
        <table id="queue-table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Date</th>
                    <th>Timestamp</th>
                    <th>Status</th>
                    <th>Processed At</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody id="queue-body"></tbody>
        </table>
        
        <script>
            // Global variables
            let queueData = [];
            let statusChart = null;
            let dateChart = null;
            
            // Initialize charts
            function initializeCharts(stats) {
                // Status distribution chart
                const statusCtx = document.getElementById('statusChart').getContext('2d');
                statusChart = new Chart(statusCtx, {
                    type: 'doughnut',
                    data: {
                        labels: ['Pending', 'Processed', 'Error'],
                        datasets: [{
                            data: [stats.pending, stats.processed, stats.error],
                            backgroundColor: [
                                'rgba(255, 153, 0, 0.6)',
                                'rgba(76, 175, 80, 0.6)',
                                'rgba(204, 0, 0, 0.6)'
                            ],
                            borderColor: [
                                'rgba(255, 153, 0, 1)',
                                'rgba(76, 175, 80, 1)',
                                'rgba(204, 0, 0, 1)'
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
                        }
                    }
                });
                
                // Date chart
                const dateCtx = document.getElementById('dateChart').getContext('2d');
                
                // Extract dates and counts
                const dates = Object.keys(stats.dates).sort();
                const pendingByDate = dates.map(date => stats.dates[date].pending);
                const processedByDate = dates.map(date => stats.dates[date].processed);
                const errorByDate = dates.map(date => stats.dates[date].error);
                
                dateChart = new Chart(dateCtx, {
                    type: 'bar',
                    data: {
                        labels: dates,
                        datasets: [
                            {
                                label: 'Pending',
                                data: pendingByDate,
                                backgroundColor: 'rgba(255, 153, 0, 0.6)',
                                borderColor: 'rgba(255, 153, 0, 1)',
                                borderWidth: 1
                            },
                            {
                                label: 'Processed',
                                data: processedByDate,
                                backgroundColor: 'rgba(76, 175, 80, 0.6)',
                                borderColor: 'rgba(76, 175, 80, 1)',
                                borderWidth: 1
                            },
                            {
                                label: 'Error',
                                data: errorByDate,
                                backgroundColor: 'rgba(204, 0, 0, 0.6)',
                                borderColor: 'rgba(204, 0, 0, 1)',
                                borderWidth: 1
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        aspectRatio: 2,
                        scales: {
                            x: {
                                stacked: true
                            },
                            y: {
                                stacked: true,
                                beginAtZero: true
                            }
                        }
                    }
                });
            }
            
            // Update stats display
            function updateStats(stats) {
                document.getElementById('total-count').textContent = stats.total;
                document.getElementById('pending-count').textContent = stats.pending;
                document.getElementById('processed-count').textContent = stats.processed;
                document.getElementById('error-count').textContent = stats.error;
                
                // Update charts if they exist
                if (statusChart) {
                    statusChart.data.datasets[0].data = [stats.pending, stats.processed, stats.error];
                    statusChart.update();
                }
                
                if (dateChart && stats.dates) {
                    const dates = Object.keys(stats.dates).sort();
                    const pendingByDate = dates.map(date => stats.dates[date].pending);
                    const processedByDate = dates.map(date => stats.dates[date].processed);
                    const errorByDate = dates.map(date => stats.dates[date].error);
                    
                    dateChart.data.labels = dates;
                    dateChart.data.datasets[0].data = pendingByDate;
                    dateChart.data.datasets[1].data = processedByDate;
                    dateChart.data.datasets[2].data = errorByDate;
                    dateChart.update();
                }
            }
            
            // Load queue data
            function loadQueueData(date = null, status = null) {
                let url = '/api/webhooks/queue';
                const params = [];
                
                // Only add valid parameters
                if (date && date.trim() !== '') params.push(`date=${date}`);
                if (status && status !== 'all') params.push(`status=${status}`);
                if (params.length > 0) url += '?' + params.join('&');
                
                console.log('Loading queue data from:', url);
                
                // Get the queue data directly
                fetch(url)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! Status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    console.log('Queue data received:', data.length, 'items');
                    queueData = data;
                    
                    // Render the queue table with the data
                    renderQueueTable(data);
                })
                .catch(error => {
                    console.error('Error loading queue data:', error);
                    document.getElementById('queue-body').innerHTML = 
                        `<tr><td colspan="6" style="text-align: center; padding: 20px; color: red;">
                            Error loading data: ${error.message}. 
                            <button onclick="loadSampleWebhooks()" style="margin-left: 10px;">
                                Load Sample Data
                            </button>
                        </td></tr>`;
                });
            }
            
            // Render queue table
            function renderQueueTable(data) {
                const tbody = document.getElementById('queue-body');
                tbody.innerHTML = '';
                
                if (data.length === 0) {
                    const row = document.createElement('tr');
                    row.innerHTML = `<td colspan="6" style="text-align: center; padding: 20px;">
                        No webhook queue items found.
                        <button onclick="loadSampleWebhooks()" style="margin-left: 10px;">
                            Load Sample Data
                        </button>
                    </td>`;
                    tbody.appendChild(row);
                    return;
                }
                
                data.forEach(item => {
                    const row = document.createElement('tr');
                    const timestamp = new Date(item.timestamp).toLocaleString();
                    const processedAt = item.processed_at ? new Date(item.processed_at).toLocaleString() : '-';
                    
                    let statusClass = '';
                    if (item.status === 'pending') statusClass = 'pending';
                    else if (item.status === 'processed') statusClass = 'processed';
                    else if (item.status === 'error') statusClass = 'error';
                    
                    row.innerHTML = `
                        <td>${item.id.substring(0, 8)}...</td>
                        <td>${item.date || '-'}</td>
                        <td>${timestamp}</td>
                        <td class="${statusClass}">${item.status}</td>
                        <td>${processedAt}</td>
                        <td>
                            <button onclick="viewDetails('${item.id}')">View</button>
                            ${item.status !== 'pending' ? `<button onclick="reprocess('${item.id}')">Reprocess</button>` : ''}
                        </td>
                    `;
                    tbody.appendChild(row);
                });
            }
            
            // Load stats data
            function loadStatsData(date = null) {
                let url = '/api/webhooks/stats';
                if (date) url += `?date=${date}`;
                
                fetch(url)
                    .then(response => response.json())
                    .then(stats => {
                        if (!statusChart || !dateChart) {
                            initializeCharts(stats);
                        }
                        updateStats(stats);
                    })
                    .catch(error => {
                        console.error('Error loading stats data:', error);
                    });
            }
            
            // View webhook details
            function viewDetails(id) {
                window.location.href = `/queue/details/${id}`;
            }
            
            // Apply filters
            function applyFilters() {
                const dateFilter = document.getElementById('date-filter').value;
                const statusFilter = document.getElementById('status-filter').value;
                
                // Only use date filter if it's not empty
                const dateParam = dateFilter && dateFilter.trim() !== '' ? dateFilter : null;
                const statusParam = statusFilter !== 'all' ? statusFilter : null;
                
                loadQueueData(dateParam, statusParam);
                loadStatsData(dateParam);
            }
            
            // Load sample webhooks
            function loadSampleWebhooks() {
                console.log('Loading sample webhooks...');
                fetch('/api/webhooks/load-samples', {
                    method: 'POST'
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! Status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(result => {
                    console.log('Sample webhooks loaded:', result);
                    if (result.status === 'success') {
                        alert('Sample webhooks loaded successfully');
                        // Reload data with a slight delay to ensure DynamoDB has time to update
                        setTimeout(() => {
                            loadQueueData(null, null);
                            loadStatsData(null);
                        }, 1000);
                    } else {
                        alert('Error: ' + result.message);
                    }
                })
                .catch(error => {
                    console.error('Error loading sample webhooks:', error);
                    alert('Error loading sample webhooks: ' + error.message);
                });
            }
            
            // Reprocess webhook from queue table
            function reprocess(id) {
                fetch(`/api/webhooks/queue/${id}/reprocess`, {
                    method: 'POST'
                })
                .then(response => response.json())
                .then(result => {
                    if (result.status === 'success') {
                        alert('Webhook marked for reprocessing');
                        // Reload data
                        applyFilters();
                    } else {
                        alert('Error: ' + result.message);
                    }
                })
                .catch(error => {
                    console.error('Error reprocessing webhook:', error);
                    alert('Error reprocessing webhook');
                });
            }
            
            // Process pending webhooks
            function processWebhooks() {
                fetch('/api/webhooks/process', {
                    method: 'POST'
                })
                .then(response => response.json())
                .then(result => {
                    if (result.status === 'success') {
                        alert('Webhooks processed successfully');
                        // Reload data
                        applyFilters();
                    } else {
                        alert('Error: ' + result.message);
                    }
                })
                .catch(error => {
                    console.error('Error processing webhooks:', error);
                    alert('Error processing webhooks');
                });
            }
            
            // Clear webhooks
            function clearWebhooks() {
                if (confirm('Are you sure you want to clear all webhooks?')) {
                    fetch('/api/webhooks/clear', {
                        method: 'POST'
                    })
                    .then(response => response.json())
                    .then(result => {
                        if (result.status === 'success') {
                            alert('Webhooks cleared successfully');
                            // Reload data
                            applyFilters();
                        } else {
                            alert('Error: ' + result.message);
                        }
                    })
                    .catch(error => {
                        console.error('Error clearing webhooks:', error);
                        alert('Error clearing webhooks');
                    });
                }
            }
            
            // Initialize page
            document.addEventListener('DOMContentLoaded', function() {
                // Set empty date filter by default
                document.getElementById('date-filter').value = '';
                document.getElementById('status-filter').value = 'all';
                
                // Load initial data without any filters
                loadQueueData(null, null);
                loadStatsData(null);
                
                // Set up event listeners
                document.getElementById('apply-filters').addEventListener('click', applyFilters);
                document.getElementById('reset-filters').addEventListener('click', function() {
                    document.getElementById('date-filter').value = '';
                    document.getElementById('status-filter').value = 'all';
                    loadQueueData(null, null);
                    loadStatsData(null);
                });
            });
        </script>
    </body>
    </html>
    """
    return html_content

@router.get("/details/{webhook_id}", response_class=HTMLResponse)
async def get_webhook_details(webhook_id: str):
    """Return the webhook details page"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Webhook Details</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
            h1 { color: #333; }
            pre { background-color: #f5f5f5; padding: 15px; border-radius: 4px; overflow-x: auto; }
            .nav-tabs { display: flex; border-bottom: 1px solid #ddd; margin-bottom: 20px; }
            .nav-tab { padding: 10px 15px; cursor: pointer; }
            .nav-tab.active { border: 1px solid #ddd; border-bottom: none; border-radius: 4px 4px 0 0; background-color: #fff; font-weight: bold; }
            .nav-tab:hover:not(.active) { background-color: #f5f5f5; }
            .info-box { background-color: #fff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); padding: 15px; margin-bottom: 20px; }
            .info-row { display: flex; margin-bottom: 10px; }
            .info-label { font-weight: bold; width: 150px; }
            .pending { color: #ff9900; }
            .processed { color: #4CAF50; }
            .error { color: #cc0000; }
            button { background-color: #0078d7; color: white; border: none; padding: 5px 15px; border-radius: 4px; cursor: pointer; margin-right: 10px; }
            button:hover { background-color: #005a9e; }
        </style>
    </head>
    <body>
        <div class="nav-tabs">
            <div class="nav-tab" onclick="window.location.href='/'">Main Dashboard</div>
            <div class="nav-tab" onclick="window.location.href='/queue'">Queue Dashboard</div>
            <div class="nav-tab active">Webhook Details</div>
        </div>
        
        <h1>Webhook Details</h1>
        
        <div class="info-box" id="webhook-info">
            <h2>Loading webhook information...</h2>
        </div>
        
        <div class="info-box">
            <h2>Raw Data</h2>
            <pre id="raw-data">Loading...</pre>
        </div>
        
        <button onclick="window.location.href='/queue'">Back to Queue</button>
        <button id="reprocess-btn" style="display:none;">Reprocess</button>
        
        <script>
            // Load webhook details
            function loadWebhookDetails() {
                const webhookId = window.location.pathname.split('/').pop();
                
                fetch(`/api/webhooks/queue/${webhookId}`)
                    .then(response => response.json())
                    .then(data => {
                        // Update webhook info
                        const webhookInfo = document.getElementById('webhook-info');
                        
                        let statusClass = '';
                        if (data.status === 'pending') statusClass = 'pending';
                        else if (data.status === 'processed') statusClass = 'processed';
                        else if (data.status === 'error') statusClass = 'error';
                        
                        const timestamp = new Date(data.timestamp).toLocaleString();
                        const processedAt = data.processed_at ? new Date(data.processed_at).toLocaleString() : '-';
                        
                        webhookInfo.innerHTML = `
                            <h2>Webhook Information</h2>
                            <div class="info-row">
                                <div class="info-label">ID:</div>
                                <div>${data.id}</div>
                            </div>
                            <div class="info-row">
                                <div class="info-label">Date:</div>
                                <div>${data.date || '-'}</div>
                            </div>
                            <div class="info-row">
                                <div class="info-label">Timestamp:</div>
                                <div>${timestamp}</div>
                            </div>
                            <div class="info-row">
                                <div class="info-label">Status:</div>
                                <div class="${statusClass}">${data.status}</div>
                            </div>
                            <div class="info-row">
                                <div class="info-label">Processed At:</div>
                                <div>${processedAt}</div>
                            </div>
                        `;
                        
                        // Add error message if present
                        if (data.error_message) {
                            webhookInfo.innerHTML += `
                            <div class="info-row">
                                <div class="info-label">Error:</div>
                                <div class="error">${data.error_message}</div>
                            </div>`;
                        }
                        
                        // Show reprocess button if not pending
                        if (data.status !== 'pending') {
                            document.getElementById('reprocess-btn').style.display = 'inline-block';
                        }
                        
                        // Load raw data
                        return fetch(`/api/webhooks/data/${webhookId}`);
                    })
                    .then(response => response.json())
                    .then(data => {
                        // Format and display raw data
                        document.getElementById('raw-data').textContent = JSON.stringify(data.raw_data, null, 2);
                    })
                    .catch(error => {
                        console.error('Error loading webhook details:', error);
                        document.getElementById('webhook-info').innerHTML = `<h2>Error loading webhook details</h2><p>${error.message}</p>`;
                        document.getElementById('raw-data').textContent = 'Error loading raw data';
                    });
            }
            
            // Reprocess webhook from details page
            function reprocessWebhook() {
                const webhookId = window.location.pathname.split('/').pop();
                
                fetch(`/api/webhooks/queue/${webhookId}/reprocess`, {
                    method: 'POST'
                })
                .then(response => response.json())
                .then(result => {
                    if (result.status === 'success') {
                        alert('Webhook marked for reprocessing');
                        // Reload details
                        loadWebhookDetails();
                    } else {
                        alert('Error: ' + result.message);
                    }
                })
                .catch(error => {
                    console.error('Error reprocessing webhook:', error);
                    alert('Error reprocessing webhook');
                });
            }
            
            // Initialize page
            document.addEventListener('DOMContentLoaded', function() {
                loadWebhookDetails();
                document.getElementById('reprocess-btn').addEventListener('click', reprocessWebhook);
            });
        </script>
    </body>
    </html>
    """.replace("WEBHOOK_ID", webhook_id)
    return html_content