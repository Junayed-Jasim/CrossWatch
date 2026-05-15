# CrossWatch Web Server - Project 4: Network Viewer (FIXED)
# Features: Access from any device on WiFi + Password protection
# Author: CrossWatch Project

# ============================================
# IMPORT LIBRARIES
# ============================================
from http.server import HTTPServer, BaseHTTPRequestHandler
import csv
import json
import os
import socket
import urllib.parse  # NEW: For parsing URLs

# ============================================
# CONFIGURATION - Change these as needed
# ============================================

# Password for accessing the dashboard
SECRET_PASSWORD = "crosswatch123"

# Server settings
PORT = 8000
SERVER_HOST = '0.0.0.0'

# ============================================
# HELPER FUNCTION: Get Computer's IP Address
# ============================================

def get_local_ip():
    """Finds and returns this computer's local IP address on the network."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            return ip
        except:
            return "127.0.0.1"

# ============================================
# PASSWORD PROTECTION - Check if request is authorized
# ============================================

def extract_password_from_path(path):
    """Extract password from URL query string"""
    parsed = urllib.parse.urlparse(path)
    query_params = urllib.parse.parse_qs(parsed.query)
    passwords = query_params.get('password', [])
    return passwords[0] if passwords else None

def is_authorized(path, client_address):
    """
    Checks if the request contains the correct password.
    """
    # Allow access from localhost without password
    if client_address == '127.0.0.1' or client_address == 'localhost':
        return True
    
    # Check for password in URL
    password = extract_password_from_path(path)
    if password and password == SECRET_PASSWORD:
        return True
    
    return False

# ============================================
# HTML DASHBOARD - With fixed API URLs (absolute paths with password)
# ============================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <title>CrossWatch - Network Viewer</title>

    <style>
        :root {
            --bg-gradient-start: #667eea;
            --bg-gradient-end: #764ba2;
            --container-bg: white;
            --text-color: #333;
            --header-bg: #2c3e50;
            --header-text: white;
            --stat-bg: #ecf0f1;
            --stat-card-bg: white;
            --table-header-bg: #34495e;
            --table-row-hover: #f8f9fa;
            --border-color: #ddd;
            --refresh-bg: #fff3cd;
            --refresh-text: #856404;
        }

        body.dark-mode {
            --bg-gradient-start: #1a1a2e;
            --bg-gradient-end: #16213e;
            --container-bg: #0f3460;
            --text-color: #eee;
            --header-bg: #0a1628;
            --header-text: white;
            --stat-bg: #1a1a2e;
            --stat-card-bg: #16213e;
            --table-header-bg: #0a1628;
            --table-row-hover: #1a1a2e;
            --border-color: #2c3e50;
            --refresh-bg: #2c3e50;
            --refresh-text: #ffd700;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, var(--bg-gradient-start) 0%, var(--bg-gradient-end) 100%);
            padding: 15px;
            min-height: 100vh;
            transition: all 0.3s ease;
            color: var(--text-color);
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: var(--container-bg);
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
            transition: background 0.3s ease;
        }

        .header {
            background: var(--header-bg);
            color: var(--header-text);
            padding: 20px 25px;
            border-bottom: 3px solid #3498db;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
        }

        .header h1 {
            font-size: 24px;
            margin-bottom: 5px;
        }

        .header p {
            color: #bdc3c7;
            font-size: 13px;
        }

        .network-badge {
            background: rgba(52, 152, 219, 0.3);
            padding: 8px 15px;
            border-radius: 20px;
            font-size: 12px;
            text-align: center;
            border: 1px solid #3498db;
        }

        .network-badge .ip {
            font-weight: bold;
            font-size: 14px;
            font-family: monospace;
        }

        .dark-mode-btn {
            background: rgba(255,255,255,0.2);
            border: none;
            color: white;
            padding: 8px 16px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 13px;
            font-weight: bold;
            transition: all 0.3s ease;
        }

        .dark-mode-btn:hover {
            background: rgba(255,255,255,0.3);
            transform: scale(1.05);
        }

        .stats {
            display: flex;
            gap: 15px;
            padding: 20px 25px;
            background: var(--stat-bg);
            border-bottom: 1px solid var(--border-color);
            flex-wrap: wrap;
        }

        .stat-card {
            flex: 1;
            min-width: 100px;
            background: var(--stat-card-bg);
            padding: 12px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            transition: transform 0.2s ease;
        }

        .stat-card:hover {
            transform: translateY(-3px);
        }

        .stat-card h3 {
            color: #7f8c8d;
            font-size: 12px;
            margin-bottom: 8px;
        }

        .stat-card .value {
            color: #3498db;
            font-size: 28px;
            font-weight: bold;
        }

        .controls-section {
            padding: 15px 25px;
            background: var(--stat-bg);
            border-bottom: 1px solid var(--border-color);
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            align-items: center;
        }

        .search-box {
            flex: 2;
            min-width: 150px;
            padding: 10px 15px;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            font-size: 14px;
            background: var(--container-bg);
            color: var(--text-color);
        }

        .search-box:focus {
            outline: none;
            border-color: #3498db;
        }

        .export-btn {
            background: #27ae60;
            color: white;
            border: none;
            padding: 10px 18px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 13px;
            font-weight: bold;
            transition: all 0.3s ease;
        }

        .export-btn:hover {
            background: #219a52;
            transform: scale(1.02);
        }

        .refresh-control {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            background: var(--stat-card-bg);
            border-radius: 20px;
            font-size: 12px;
        }

        .refresh-control input {
            cursor: pointer;
            width: 14px;
            height: 14px;
        }

        .refresh-info {
            padding: 8px 25px;
            background: var(--refresh-bg);
            color: var(--refresh-text);
            font-size: 11px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 8px;
        }

        .table-container {
            padding: 20px 25px;
            max-height: 500px;
            overflow-y: auto;
            overflow-x: auto;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            min-width: 500px;
        }

        th {
            background: var(--table-header-bg);
            color: white;
            padding: 10px;
            text-align: left;
            font-size: 13px;
            position: sticky;
            top: 0;
        }

        td {
            padding: 8px 10px;
            border-bottom: 1px solid var(--border-color);
            font-size: 12px;
        }

        tr:hover {
            background: var(--table-row-hover);
        }

        .app-badge {
            background: #3498db;
            color: white;
            padding: 3px 6px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: bold;
            display: inline-block;
        }

        .no-results {
            text-align: center;
            padding: 40px;
            color: #7f8c8d;
            font-size: 14px;
        }

        .footer {
            padding: 12px 25px;
            background: var(--stat-bg);
            text-align: center;
            font-size: 11px;
            color: #7f8c8d;
            border-top: 1px solid var(--border-color);
        }

        @media (max-width: 768px) {
            body {
                padding: 10px;
            }
            .header h1 {
                font-size: 20px;
            }
            .stat-card .value {
                font-size: 22px;
            }
            .controls-section {
                padding: 12px 15px;
            }
            .table-container {
                padding: 15px;
            }
        }
    </style>
</head>

<body>

    <div class="container">

        <div class="header">
            <div>
                <h1>📊 CrossWatch Network Viewer</h1>
                <p>Real-time activity tracking • Project 4 • Access from any device</p>
            </div>
            <div style="display: flex; gap: 10px; align-items: center;">
                <div class="network-badge" id="networkBadge">
                    📡 Loading IP...
                </div>
                <button class="dark-mode-btn" id="darkModeBtn">
                    🌙 Dark Mode
                </button>
            </div>
        </div>

        <div class="stats">
            <div class="stat-card">
                <h3>Total Activities</h3>
                <div class="value" id="totalCount">0</div>
            </div>
            <div class="stat-card">
                <h3>Unique Apps</h3>
                <div class="value" id="uniqueApps">0</div>
            </div>
            <div class="stat-card">
                <h3>Last Update</h3>
                <div class="value" id="lastUpdate" style="font-size: 14px;">-</div>
            </div>
        </div>

        <div class="controls-section">
            <input type="text" id="searchInput" class="search-box" placeholder="🔍 Search apps or window titles...">
            <button class="export-btn" id="exportBtn">📥 Export CSV</button>
            <div class="refresh-control">
                <input type="checkbox" id="autoRefreshToggle" checked>
                <label>Auto-refresh (5s)</label>
            </div>
        </div>

        <div class="refresh-info">
            <span>🔄 Data source: activity_log.csv</span>
            <span id="filterStatus">Loading data...</span>
        </div>

        <div class="table-container">
            <div id="logContent">
                <div class="no-results">📭 Loading activities from server...</div>
            </div>
        </div>

        <div class="footer">
            CrossWatch - Network Viewer |
            🔍 Search • 📥 Export • 🌙 Dark Mode • 📡 Access from any device on WiFi
        </div>

    </div>

    <script>

        // ============================================
        // FIXED: Get password from current URL to use in API calls
        // ============================================
        
        // Get the current page's URL parameters
        const urlParams = new URLSearchParams(window.location.search);
        const currentPassword = urlParams.get('password') || '';
        
        // Build API URLs with password (if exists)
        let apiUrl = '/api/logs';
        let networkUrl = '/api/network';
        
        if (currentPassword) {
            apiUrl = `/api/logs?password=${currentPassword}`;
            networkUrl = `/api/network?password=${currentPassword}`;
        }
        
        console.log("API URL:", apiUrl);
        console.log("Network URL:", networkUrl);

        // ============================================
        // GLOBAL VARIABLES
        // ============================================

        let allLogs = [];
        let autoRefreshEnabled = true;
        let refreshInterval = null;

        // ============================================
        // FUNCTION: Get Network IP from Server
        // ============================================

        function getNetworkInfo() {
            fetch(networkUrl)
                .then(response => response.json())
                .then(data => {
                    const badge = document.getElementById('networkBadge');
                    if (data.ip) {
                        badge.innerHTML = `📡 Access from: <span class="ip">${data.ip}:${data.port}</span>`;
                    } else {
                        badge.innerHTML = `📡 Port: ${data.port}`;
                    }
                })
                .catch(error => {
                    console.error("Error getting network info:", error);
                    const badge = document.getElementById('networkBadge');
                    badge.innerHTML = `📡 Port: 8000`;
                });
        }

        // ============================================
        // FUNCTION: Load Logs from Server
        // ============================================

        function loadLogs() {
            console.log("Fetching logs from:", apiUrl);

            fetch(apiUrl)
                .then(response => {
                    console.log("Response status:", response.status);
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    console.log("Received data:", data);

                    if (data.error) {
                        document.getElementById('logContent').innerHTML =
                            '<div class="no-results">⚠️ ' + data.error + '</div>';
                        return;
                    }

                    if (!data.logs || data.logs.length === 0) {
                        document.getElementById('logContent').innerHTML =
                            '<div class="no-results">📭 No data yet. Run python logger.py first!</div>';
                        document.getElementById('totalCount').innerText = '0';
                        document.getElementById('uniqueApps').innerText = '0';
                        return;
                    }

                    allLogs = data.logs;

                    document.getElementById('totalCount').innerText = data.total;
                    document.getElementById('uniqueApps').innerText = data.unique_apps;
                    document.getElementById('lastUpdate').innerText = new Date().toLocaleTimeString();

                    applySearchFilter();
                })
                .catch(error => {
                    console.error("Error fetching logs:", error);
                    document.getElementById('logContent').innerHTML =
                        '<div class="no-results">⚠️ Cannot connect to server. Make sure server is running and you are using the correct URL with password.</div>';
                });
        }

        // ============================================
        // FUNCTION: Apply Search Filter
        // ============================================

        function applySearchFilter() {
            const searchInput = document.getElementById('searchInput');
            if (!searchInput) return;
            const searchTerm = searchInput.value.toLowerCase();
            let filteredLogs = allLogs;
            if (searchTerm !== '') {
                filteredLogs = allLogs.filter(log => {
                    return (
                        (log.app && log.app.toLowerCase().includes(searchTerm)) ||
                        (log.window && log.window.toLowerCase().includes(searchTerm))
                    );
                });
            }
            const filterSpan = document.getElementById('filterStatus');
            if (filterSpan) {
                if (searchTerm !== '') {
                    filterSpan.innerHTML = `🔍 Found ${filteredLogs.length} results for "${searchTerm}"`;
                } else {
                    filterSpan.innerHTML = `Showing all ${filteredLogs.length} activities`;
                }
            }
            displayLogs(filteredLogs);
        }

        // ============================================
        // FUNCTION: Display Logs as HTML Table
        // ============================================

        function displayLogs(logs) {
            const logContent = document.getElementById('logContent');
            if (!logs || logs.length === 0) {
                logContent.innerHTML = '<div class="no-results">📭 No matching activities found.</div>';
                return;
            }
            let html = `<table><thead><tr><th>#</th><th>Timestamp</th><th>Application</th><th>Window Title</th></tr></thead><tbody>`;
            for (let i = 0; i < logs.length; i++) {
                const log = logs[i];
                html += `<tr><td>${escapeHtml(log.counter || '')}</td><td>${escapeHtml(log.timestamp || '')}</td><td><span class="app-badge">${escapeHtml(log.app || 'Unknown')}</span></td><td>${escapeHtml(log.window || '')}</td></tr>`;
            }
            html += `</tbody>{"</div>"}`;
            logContent.innerHTML = html;
        }

        // ============================================
        // FUNCTION: Escape HTML
        // ============================================

        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // ============================================
        // FUNCTION: Export to CSV
        // ============================================

        function exportToCSV() {
            const searchInput = document.getElementById('searchInput');
            const searchTerm = searchInput ? searchInput.value.toLowerCase() : '';
            let logsToExport = allLogs;
            if (searchTerm !== '') {
                logsToExport = allLogs.filter(log => {
                    return (
                        (log.app && log.app.toLowerCase().includes(searchTerm)) ||
                        (log.window && log.window.toLowerCase().includes(searchTerm))
                    );
                });
            }
            if (logsToExport.length === 0) {
                alert('No data to export!');
                return;
            }
            let csvData = "Timestamp,Counter,Application,Window Title\\n";
            for (let log of logsToExport) {
                csvData += `"${log.timestamp || ''}",${log.counter || ''},"${log.app || ''}","${log.window || ''}"\\n`;
            }
            const blob = new Blob([csvData], { type: 'text/csv' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'crosswatch_export.csv';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            alert("✅ CSV Export Complete!");
        }

        // ============================================
        // FUNCTION: Dark Mode Toggle
        // ============================================

        function toggleDarkMode() {
            document.body.classList.toggle('dark-mode');
            const btn = document.getElementById('darkModeBtn');
            if (document.body.classList.contains('dark-mode')) {
                btn.innerHTML = '☀️ Light Mode';
                localStorage.setItem('darkMode', 'enabled');
            } else {
                btn.innerHTML = '🌙 Dark Mode';
                localStorage.setItem('darkMode', 'disabled');
            }
        }

        // ============================================
        // FUNCTION: Load Saved Dark Mode Preference
        // ============================================

        function loadDarkModePreference() {
            const savedMode = localStorage.getItem('darkMode');
            if (savedMode === 'enabled') {
                document.body.classList.add('dark-mode');
                const btn = document.getElementById('darkModeBtn');
                if (btn) btn.innerHTML = '☀️ Light Mode';
            }
        }

        // ============================================
        // AUTO-REFRESH CONTROL
        // ============================================

        function startAutoRefresh() {
            if (refreshInterval) clearInterval(refreshInterval);
            refreshInterval = setInterval(() => {
                if (autoRefreshEnabled) {
                    console.log("Auto-refreshing...");
                    loadLogs();
                }
            }, 5000);
        }

        // ============================================
        // SETUP EVENT LISTENERS
        // ============================================

        function setupEventListeners() {
            const searchInput = document.getElementById('searchInput');
            if (searchInput) {
                searchInput.addEventListener('keyup', applySearchFilter);
            }
            const exportBtn = document.getElementById('exportBtn');
            if (exportBtn) {
                exportBtn.addEventListener('click', exportToCSV);
            }
            const darkModeBtn = document.getElementById('darkModeBtn');
            if (darkModeBtn) {
                darkModeBtn.addEventListener('click', toggleDarkMode);
            }
            const refreshToggle = document.getElementById('autoRefreshToggle');
            if (refreshToggle) {
                refreshToggle.addEventListener('change', (e) => {
                    autoRefreshEnabled = e.target.checked;
                    console.log("Auto-refresh:", autoRefreshEnabled ? "ON" : "OFF");
                });
            }
        }

        // ============================================
        // PAGE INITIALIZATION
        // ============================================

        window.addEventListener('DOMContentLoaded', () => {
            loadDarkModePreference();
            setupEventListeners();
            getNetworkInfo();
            loadLogs();
            startAutoRefresh();
        });

    </script>

</body>
</html>
"""

# ============================================
# SERVER HANDLER - Handles browser requests
# ============================================

class CrossWatchHandler(BaseHTTPRequestHandler):
    """Handles incoming web requests from your browser"""

    def log_message(self, format, *args):
        """Override to reduce console spam"""
        pass

    def do_GET(self):
        """
        Handles different URLs:
        /           - Main dashboard
        /api/logs   - Returns activity data as JSON
        /api/network - Returns IP address info
        """
        
        # Parse the URL to get path and query parameters
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query_params = urllib.parse.parse_qs(parsed.query)
        
        # Get the password from query parameters
        password_from_url = query_params.get('password', [None])[0]
        
        # Check if request is authorized (unless it's the network info endpoint)
        if path != '/api/network':
            client_ip = self.client_address[0]
            authorized = False
            
            # Localhost is always authorized
            if client_ip == '127.0.0.1' or client_ip == 'localhost':
                authorized = True
            
            # Check password
            elif password_from_url and password_from_url == SECRET_PASSWORD:
                authorized = True
            
            if not authorized:
                self.send_response(401)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                
                error_html = f"""
                <!DOCTYPE html>
                <html>
                <head><title>CrossWatch - Access Denied</title>
                <style>
                    body{{font-family:Arial;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);padding:50px;text-align:center;}}
                    .container{{max-width:500px;margin:0 auto;background:white;padding:30px;border-radius:15px;box-shadow:0 10px 40px rgba(0,0,0,0.2);}}
                    h1{{color:#e74c3c;}}
                    code{{background:#f4f4f4;padding:10px;display:block;border-radius:5px;margin:20px 0;}}
                </style>
                </head>
                <body>
                    <div class="container">
                        <h1>🔒 Access Denied</h1>
                        <p>This dashboard is password protected.</p>
                        <p>Add the password to the URL:</p>
                        <code>http://{self.headers.get('Host', 'IP_ADDRESS')}/?password={SECRET_PASSWORD}</code>
                        <p><small>Access from the same computer does not require a password.</small></p>
                    </div>
                </body>
                </html>
                """
                self.wfile.write(error_html.encode('utf-8'))
                return

        # ============================================
        # OPTION 1: Network Info API
        # ============================================
        
        if path == '/api/network':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            local_ip = get_local_ip()
            response = {
                'ip': local_ip,
                'port': PORT,
                'password': SECRET_PASSWORD,
                'message': f'Access from http://{local_ip}:{PORT}/?password={SECRET_PASSWORD}'
            }
            
            self.wfile.write(json.dumps(response, indent=2).encode('utf-8'))

        # ============================================
        # OPTION 2: Main dashboard page
        # ============================================
        
        elif path == '/' or path == '/dashboard':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode('utf-8'))

        # ============================================
        # OPTION 3: API endpoint for data
        # ============================================

        elif path == '/api/logs':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            logs = []

            try:
                if not os.path.exists('activity_log.csv'):
                    response = {
                        'error': 'activity_log.csv not found. Run python logger.py first!',
                        'total': 0,
                        'unique_apps': 0,
                        'logs': []
                    }
                else:
                    with open('activity_log.csv', 'r', encoding='utf-8', errors='ignore') as file:
                        reader = csv.DictReader(file)
                        for row in reader:
                            if not row.get('Timestamp'):
                                continue
                            log_entry = {
                                'timestamp': row.get('Timestamp', ''),
                                'counter': row.get('Counter', ''),
                                'app': row.get('Application', ''),
                                'window': row.get('Window Title', '')[:100]
                            }
                            logs.append(log_entry)

                    unique_apps_set = set()
                    for log in logs:
                        if log['app']:
                            unique_apps_set.add(log['app'])
                    unique_apps_count = len(unique_apps_set)

                    logs.reverse()
                    logs = logs[:200]

                    response = {
                        'total': len(logs),
                        'unique_apps': unique_apps_count,
                        'logs': logs
                    }

            except Exception as error:
                response = {
                    'error': f'Error reading log file: {str(error)}',
                    'total': 0,
                    'unique_apps': 0,
                    'logs': []
                }

            self.wfile.write(json.dumps(response, indent=2, ensure_ascii=False).encode('utf-8'))

        # ============================================
        # OPTION 4: Any other URL
        # ============================================

        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<h1>404 - Page Not Found</h1>')

# ============================================
# START THE SERVER
# ============================================

def run_server():
    """Starts the web server on all network interfaces"""
    
    local_ip = get_local_ip()
    server_address = (SERVER_HOST, PORT)
    httpd = HTTPServer(server_address, CrossWatchHandler)

    print("=" * 61)
    print("🌐 CrossWatch Network Viewer - PROJECT 4!")
    print("=" * 61)

    print(f"\n📡 SERVER STARTED ON ALL NETWORK INTERFACES")
    print(f"   Listening on: {SERVER_HOST}:{PORT}")

    print(f"\n📍 ACCESS FROM THIS COMPUTER:")
    print(f"   http://localhost:{PORT}")
    print(f"📍 Network URL: http://127.0.0.1:{PORT}")

    print(f"\n📱 ACCESS FROM PHONE / TABLET / OTHER DEVICES:")
    print(f"   http://{local_ip}:{PORT}/?password={SECRET_PASSWORD}")

    print(f"\n🔒 PASSWORD: {SECRET_PASSWORD}")

    print("\n✨ FEATURES: Search • Export CSV • Dark Mode • Network Access")

    print("\n⚠️  Press CTRL + C to stop the server")
    print("=" * 61)

    print("✅ Server is running...\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n✅ Web server stopped!")
        httpd.server_close()

if __name__ == '__main__':
    run_server()