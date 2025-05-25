"""
Routes for settings page
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
import logging

router = APIRouter(prefix="/settings", tags=["settings"])
logger = logging.getLogger(__name__)

@router.get("/", response_class=HTMLResponse)
async def get_settings_page():
    """Return the settings page HTML"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Settings - Alert Insight Hub</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
            h1 { color: #333; }
            .nav-tabs { display: flex; border-bottom: 1px solid #ddd; margin-bottom: 20px; }
            .nav-tab { padding: 10px 15px; cursor: pointer; }
            .nav-tab.active { border: 1px solid #ddd; border-bottom: none; border-radius: 4px 4px 0 0; background-color: #fff; font-weight: bold; }
            .nav-tab:hover:not(.active) { background-color: #f5f5f5; }
            .settings-container { max-width: 800px; margin: 0 auto; }
            .settings-section { margin-bottom: 30px; background-color: #fff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); padding: 20px; }
            .settings-title { font-size: 18px; font-weight: bold; margin-bottom: 15px; }
            .form-group { margin-bottom: 15px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input[type="text"], input[type="password"] { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
            button { background-color: #0078d7; color: white; border: none; padding: 10px 15px; border-radius: 4px; cursor: pointer; }
            button:hover { background-color: #005a9e; }
            .success-message { color: green; margin-top: 10px; }
            .error-message { color: red; margin-top: 10px; }
            .api-status { margin-top: 10px; padding: 10px; border-radius: 4px; }
            .api-status.success { background-color: #e6ffe6; color: #006600; }
            .api-status.error { background-color: #ffe6e6; color: #cc0000; }
        </style>
    </head>
    <body>
        <div class="nav-tabs">
            <div class="nav-tab" onclick="window.location.href='/'">Main Dashboard</div>
            <div class="nav-tab" onclick="window.location.href='/queue'">Queue Dashboard</div>
            <div class="nav-tab active">Settings</div>
        </div>
        
        <div class="settings-container">
            <h1>Application Settings</h1>
            
            <div class="settings-section">
                <div class="settings-title">Groq API Configuration</div>
                <div class="form-group">
                    <label for="gorqcloud_api_key">API Key:</label>
                    <input type="password" id="gorqcloud_api_key" placeholder="Enter your Groq API key">
                </div>
                <div class="form-group">
                    <label for="agent_role">Agent Role:</label>
                    <input type="text" id="agent_role" placeholder="Enter the agent role (e.g., AWS Cloud Expert)">
                </div>
                <div class="form-group">
                    <label for="agent_description">Role Description:</label>
                    <textarea id="agent_description" rows="4" style="width: 100%; padding: 8px;" 
                        placeholder="Enter a detailed description of the agent's role and expertise"></textarea>
                </div>
                <button id="save-api-key">Save Settings</button>
                <button id="test-api-key">Test Connection</button>
                <div id="api-status" class="api-status" style="display: none;"></div>
            </div>
            
            <div class="settings-section">
                <div class="settings-title">Alert Processing Settings</div>
                <div class="form-group">
                    <label for="use_ai_recommendations">
                        <input type="checkbox" id="use_ai_recommendations"> 
                        Use AI for alert recommendations
                    </label>
                    <p>When enabled, the system will use Gorqcloud AI to generate recommendations for alerts.</p>
                </div>
                <button id="save-processing-settings">Save Settings</button>
                <div id="processing-status" class="api-status" style="display: none;"></div>
            </div>
        </div>
        
        <script>
            // Load settings on page load
            document.addEventListener('DOMContentLoaded', function() {
                loadSettings();
                
                // Set up event listeners
                document.getElementById('save-api-key').addEventListener('click', saveApiKey);
                document.getElementById('test-api-key').addEventListener('click', testApiConnection);
                document.getElementById('save-processing-settings').addEventListener('click', saveProcessingSettings);
            });
            
            // Load settings from API
            function loadSettings() {
                fetch('/api/settings/')
                    .then(response => response.json())
                    .then(data => {
                        if (data.gorqcloud_api_key) {
                            document.getElementById('gorqcloud_api_key').value = data.gorqcloud_api_key;
                        }
                        
                        if (data.agent_role) {
                            document.getElementById('agent_role').value = data.agent_role;
                        }
                        
                        if (data.agent_description) {
                            document.getElementById('agent_description').value = data.agent_description;
                        }
                        
                        if (data.use_ai_recommendations === 'true') {
                            document.getElementById('use_ai_recommendations').checked = true;
                        }
                    })
                    .catch(error => {
                        console.error('Error loading settings:', error);
                    });
            }
            
            // Save API key and agent settings
            function saveApiKey() {
                const apiKey = document.getElementById('gorqcloud_api_key').value;
                const agentRole = document.getElementById('agent_role').value;
                const agentDescription = document.getElementById('agent_description').value;
                
                fetch('/api/settings/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        gorqcloud_api_key: apiKey,
                        agent_role: agentRole,
                        agent_description: agentDescription
                    })
                })
                .then(response => response.json())
                .then(data => {
                    const statusElement = document.getElementById('api-status');
                    statusElement.style.display = 'block';
                    
                    if (data.status === 'success') {
                        statusElement.className = 'api-status success';
                        statusElement.textContent = 'Settings saved successfully';
                    } else {
                        statusElement.className = 'api-status error';
                        statusElement.textContent = data.message || 'Error saving settings';
                    }
                    
                    // Hide status after 3 seconds
                    setTimeout(() => {
                        statusElement.style.display = 'none';
                    }, 3000);
                })
                .catch(error => {
                    console.error('Error saving settings:', error);
                    const statusElement = document.getElementById('api-status');
                    statusElement.style.display = 'block';
                    statusElement.className = 'api-status error';
                    statusElement.textContent = 'Error saving settings';
                });
            }
            
            // Test API connection
            function testApiConnection() {
                const statusElement = document.getElementById('api-status');
                statusElement.style.display = 'block';
                statusElement.className = 'api-status';
                statusElement.textContent = 'Testing connection...';
                
                fetch('/api/settings/test-gorqcloud')
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'success') {
                            statusElement.className = 'api-status success';
                            statusElement.textContent = 'Connection successful!';
                        } else {
                            statusElement.className = 'api-status error';
                            statusElement.textContent = data.message || 'Connection failed';
                        }
                    })
                    .catch(error => {
                        console.error('Error testing API connection:', error);
                        statusElement.className = 'api-status error';
                        statusElement.textContent = 'Error testing connection';
                    });
            }
            
            // Save processing settings
            function saveProcessingSettings() {
                const useAI = document.getElementById('use_ai_recommendations').checked;
                
                fetch('/api/settings/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        use_ai_recommendations: useAI.toString()
                    })
                })
                .then(response => response.json())
                .then(data => {
                    const statusElement = document.getElementById('processing-status');
                    statusElement.style.display = 'block';
                    
                    if (data.status === 'success') {
                        statusElement.className = 'api-status success';
                        statusElement.textContent = 'Settings saved successfully';
                    } else {
                        statusElement.className = 'api-status error';
                        statusElement.textContent = data.message || 'Error saving settings';
                    }
                    
                    // Hide status after 3 seconds
                    setTimeout(() => {
                        statusElement.style.display = 'none';
                    }, 3000);
                })
                .catch(error => {
                    console.error('Error saving settings:', error);
                    const statusElement = document.getElementById('processing-status');
                    statusElement.style.display = 'block';
                    statusElement.className = 'api-status error';
                    statusElement.textContent = 'Error saving settings';
                });
            }
        </script>
    </body>
    </html>
    """
    return html_content