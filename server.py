# CrossWatch Web Server - Complete Working Version
# This creates a web dashboard that shows your activity logs
# Author: CrossWatch Project

# Import necessary libraries
from http.server import HTTPServer, BaseHTTPRequestHandler  # Creates the web server
import csv  # Reads the CSV log file
import json  # Converts data to JSON format for JavaScript
import os  # Checks if files exist

# ============================================
# HTML DASHBOARD - This is what you see in your browser
# ============================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>CrossWatch - Activity Dashboard</title>
    <meta charset="UTF-8">
    <style>
        /* CSS Styling - Makes the dashboard look nice */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }
        
        .header {
            background: #2c3e50;
            color: white;
            padding: 20px 30px;
            border-bottom: 3px solid #3498db;
        }
        
        .header h1 {
            font-size: 28px;
            margin-bottom: 5px;
        }
        
        .header p {
            color: #bdc3c7;
            font-size: 14px;
        }
        
        .stats {
            display: flex;
            gap: 20px;
            padding: 20px 30px;
            background: #ecf0f1;
            border-bottom: 1px solid #ddd;
        }
        
        .stat-card {
            flex: 1;
            background: white;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        .stat-card h3 {
            color: #7f8c8d;
            font-size: 14px;
            margin-bottom: 10px;
        }
        
        .stat-card .value {
            color: #2c3e50;
            font-size: 28px;
            font-weight: bold;
        }
        
        .refresh-info {
            padding: 10px 30px;
            background: #fff3cd;
            color: #856404;
            font-size: 12px;
            border-bottom: 1px solid #ffeeba;
        }
        
        .table-container {
            padding: 20px 30px;
            max-height: 500px;
            overflow-y: auto;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th {
            background: #34495e;
            color: white;
            padding: 12px;
            text-align: left;
            font-size: 14px;
            position: sticky;
            top: 0;
        }
        
        td {
            padding: 10px 12px;
            border-bottom: 1px solid #ecf0f1;
            font-size: 13px;
        }
        
        tr:hover {
            background: #f8f9fa;
        }
        
        .app-badge {
            background: #3498db;
            color: white;
            padding: 4px 8px;
            border-radius: 5px;
            font-size: 11px;
            font-weight: bold;
            display: inline-block;
        }
        
        .footer {
            padding: 15px 30px;
            background: #ecf0f1;
            text-align: center;
            font-size: 12px;
            color: #7f8c8d;
        }
        
        .loading {
            text-align: center;
            padding: 50px;
            color: #7f8c8d;
        }
        
        .error {
            background: #f8d7da;
            color: #721c24;
            padding: 15px;
            border-radius: 5px;
            margin: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 CrossWatch Activity Dashboard</h1>
            <p>Real-time application tracking</p>
        </div>
        
        <div class="stats" id="stats">
            <div class="stat-card">
                <h3>Total Activities</h3>
                <div class="value" id="totalCount">-</div>
            </div>
            <div class="stat-card">
                <h3>Unique Apps</h3>
                <div class="value" id="uniqueApps">-</div>
            </div>
            <div class="stat-card">
                <h3>Last Update</h3>
                <div class="value" id="lastUpdate">-</div>
            </div>
        </div>
        
        <div class="refresh-info">
            🔄 Auto-refreshing every 5 seconds | Data source: activity_log.csv
        </div>
        
        <div class="table-container">
            <div id="logContent">
                <div class="loading">Loading activities...</div>
            </div>
        </div>
        
        <div class="footer">
            CrossWatch - Local Activity Monitor | Your data stays on your computer
        </div>
    </div>
    
    <script>
        // This JavaScript code runs in your browser and fetches data from the server
        
        function loadLogs() {
            // Fetch data from the server's API endpoint
            fetch('/api/logs')
                .then(response => response.json())  // Convert response to JSON
                .then(data => {
                    // Check if there's an error
                    if (data.error) {
                        document.getElementById('logContent').innerHTML = 
                            '<div class="error">⚠️ ' + data.error + '</div>';
                        return;
                    }
                    
                    // Update the statistics cards
                    document.getElementById('totalCount').innerText = data.total;
                    document.getElementById('uniqueApps').innerText = data.unique_apps;
                    document.getElementById('lastUpdate').innerText = new Date().toLocaleTimeString();
                    
                    // Check if there are any logs
                    if (data.logs.length === 0) {
                        document.getElementById('logContent').innerHTML = 
                            '<div class="loading">No activities found. Run python logger.py first!</div>';
                        return;
                    }
                    
                    // Build an HTML table from the data
                    let html = '<table>\\n<thead>\\n<tr>\\n';
                    html += '<th>#</th><th>Timestamp</th><th>Application</th><th>Window Title</th>\\n';
                    html += '</tr>\\n</thead>\\n<tbody>\\n';
                    
                    // Loop through each log entry (only show last 50 for performance)
                    for (let i = 0; i < data.logs.length; i++) {
                        const log = data.logs[i];
                        html += '<tr>\\n';
                        html += '<td>' + log.counter + '</td>\\n';
                        html += '<td>' + log.timestamp + '</td>\\n';
                        html += '<td><span class="app-badge">' + escapeHtml(log.app) + '</span></td>\\n';
                        html += '<td>' + escapeHtml(log.window) + '</td>\\n';
                        html += '</tr>\\n';
                    }
                    
                    html += '</tbody>\\n</table>\\n';
                    document.getElementById('logContent').innerHTML = html;
                })
                .catch(error => {
                    // Handle any errors (like server not running)
                    document.getElementById('logContent').innerHTML = 
                        '<div class="error">⚠️ Error loading logs: ' + error + '</div>';
                });
        }
        
        // Helper function to prevent HTML injection (security)
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        // Load logs immediately when page opens
        loadLogs();
        
        // Then automatically refresh every 5 seconds
        setInterval(loadLogs, 5000);
    </script>
</body>
</html>
"""

# ============================================
# SERVER HANDLER - Handles browser requests
# ============================================

class CrossWatchHandler(BaseHTTPRequestHandler):
    """
    This class handles incoming web requests from your browser
    It defines what happens when someone visits different URLs
    """
    
    # FIXED: Added this method to suppress server log messages (makes output cleaner)
    def log_message(self, format, *args):
        """Override to reduce console spam - only log errors"""
        # You can comment out the 'pass' and uncomment the line below to see all requests
        pass
        # print(f"[{self.log_date_time_string()}] {format % args}")
    
    def do_GET(self):
        """
        This function runs whenever someone visits the server
        self.path tells us which URL was requested
        """
        
        # OPTION 1: Main dashboard page (http://localhost:8000/)
        if self.path == '/' or self.path == '/dashboard':
            # Send HTTP 200 OK status
            self.send_response(200)
            
            # Tell browser we're sending HTML content
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            # Send the HTML dashboard to the browser
            self.wfile.write(HTML_TEMPLATE.encode('utf-8'))
        
        # OPTION 2: API endpoint for data (http://localhost:8000/api/logs)
        elif self.path == '/api/logs':
            # Send HTTP 200 OK status
            self.send_response(200)
            
            # Tell browser we're sending JSON data
            self.send_header('Content-type', 'application/json')
            # FIXED: Added CORS headers to prevent browser security issues
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Read the CSV log file and convert to JSON
            logs = []
            
            try:
                # Check if the CSV file exists
                if not os.path.exists('activity_log.csv'):
                    # If file doesn't exist, send error message
                    response = {
                        'error': 'activity_log.csv not found. Run python logger.py first!',
                        'total': 0,
                        'unique_apps': 0,
                        'logs': []
                    }
                else:
                    # Open and read the CSV file
                    # FIXED: Added error handling for file reading with proper encoding
                    with open('activity_log.csv', 'r', encoding='utf-8', errors='ignore') as file:
                        # Use CSV reader to parse the file
                        reader = csv.DictReader(file)
                        
                        # Loop through each row in the CSV
                        for row in reader:
                            # FIXED: Added validation to skip empty rows
                            if not row.get('Timestamp'):
                                continue
                            
                            # Create a dictionary for each log entry
                            log_entry = {
                                'timestamp': row.get('Timestamp', ''),
                                'counter': row.get('Counter', ''),
                                'app': row.get('Application', ''),
                                'window': row.get('Window Title', '')[:100]  # FIXED: Increased from 60 to 100 chars
                            }
                            logs.append(log_entry)
                    
                    # Calculate how many unique applications were used
                    # Create a set (like a list but with unique values only)
                    unique_apps_set = set()
                    for log in logs:
                        if log['app']:
                            unique_apps_set.add(log['app'])
                    
                    # Get the count of unique apps
                    unique_apps_count = len(unique_apps_set)
                    
                    # Reverse the logs so newest appears first
                    logs.reverse()
                    
                    # FIXED: Limit to last 100 entries for better performance
                    logs = logs[:100]
                    
                    # Create the JSON response
                    response = {
                        'total': len(logs),
                        'unique_apps': unique_apps_count,
                        'logs': logs  # Send limited logs for performance
                    }
                    
            except Exception as error:
                # If any error occurs, send error message
                # FIXED: Added more detailed error information
                response = {
                    'error': f'Error reading log file: {str(error)}',
                    'total': 0,
                    'unique_apps': 0,
                    'logs': []
                }
            
            # Convert Python dictionary to JSON string and send to browser
            # FIXED: Added ensure_ascii=False to properly handle unicode characters
            self.wfile.write(json.dumps(response, indent=2, ensure_ascii=False).encode('utf-8'))
        
        # OPTION 3: Any other URL - return 404 Not Found
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<h1>404 - Page Not Found</h1>')
            self.wfile.write(b'<p>Try <a href="/">http://localhost:8000/</a></p>')

# ============================================
# START THE SERVER
# ============================================

def run_server():
    """Starts the web server on port 8000"""
    
    # Server settings
    port = 8000  # Port number (like a door number for network traffic)
    server_address = ('localhost', port)  # Only accessible from this computer
    
    # Create the server instance
    httpd = HTTPServer(server_address, CrossWatchHandler)
    
    # Print startup information
    print("=" * 50)
    print("🌐 CrossWatch Web Server Started!")
    print("=" * 50)
    print(f"📍 Local URL: http://localhost:{port}")
    print(f"📍 Network URL: http://127.0.0.1:{port}")
    print("\n📋 Instructions:")
    print("   1. Open your web browser")
    print("   2. Go to http://localhost:8000")
    print("   3. Watch your activities appear in real-time!")
    print("\n⚠️  Press CTRL + C to stop the server")
    print("=" * 50)
    print("\n✅ Server is running... (waiting for connections)")
    
    try:
        # Keep the server running forever (until CTRL+C)
        httpd.serve_forever()
    except KeyboardInterrupt:
        # This runs when you press CTRL+C
        print("\n\n✅ Web server stopped!")
        httpd.server_close()

# This checks if the script is being run directly (not imported)
if __name__ == '__main__':
    run_server()