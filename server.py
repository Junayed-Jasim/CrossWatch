# CrossWatch Web Server - Project 3: Enhanced Dashboard (FIXED)
# Features: Search, Export CSV, Dark Mode, Auto-refresh
# Author: CrossWatch Project

# ============================================
# IMPORT LIBRARIES
# ============================================
from http.server import HTTPServer, BaseHTTPRequestHandler  # Creates web server
import csv  # Reads CSV log file
import json  # Converts data to JSON for JavaScript
import os  # Checks if files exist

# ============================================
# HTML DASHBOARD - The webpage you see in your browser
# ============================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CrossWatch - Enhanced Activity Dashboard</title>

    <style>
        /* ===== CSS VARIABLES ===== */
        /* These make dark mode switching easier */

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

        /* Dark mode colors - applied when body has 'dark-mode' class */

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

        /* ===== MAIN STYLES ===== */

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(
                135deg,
                var(--bg-gradient-start) 0%,
                var(--bg-gradient-end) 100%
            );
            padding: 20px;
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

        /* ===== HEADER SECTION ===== */

        .header {
            background: var(--header-bg);
            color: var(--header-text);
            padding: 20px 30px;
            border-bottom: 3px solid #3498db;

            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
        }

        .header h1 {
            font-size: 28px;
            margin-bottom: 5px;
        }

        .header p {
            color: #bdc3c7;
            font-size: 14px;
        }

        /* Dark Mode Toggle Button */

        .dark-mode-btn {
            background: rgba(255,255,255,0.2);
            border: none;
            color: white;

            padding: 10px 20px;
            border-radius: 25px;

            cursor: pointer;
            font-size: 14px;
            font-weight: bold;

            transition: all 0.3s ease;
        }

        .dark-mode-btn:hover {
            background: rgba(255,255,255,0.3);
            transform: scale(1.05);
        }

        /* ===== STATISTICS CARDS ===== */

        .stats {
            display: flex;
            gap: 20px;
            padding: 20px 30px;

            background: var(--stat-bg);
            border-bottom: 1px solid var(--border-color);

            flex-wrap: wrap;
        }

        .stat-card {
            flex: 1;

            background: var(--stat-card-bg);
            padding: 15px;

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
            font-size: 14px;
            margin-bottom: 10px;
        }

        .stat-card .value {
            color: #3498db;
            font-size: 32px;
            font-weight: bold;
        }

        /* ===== SEARCH AND CONTROLS SECTION ===== */

        .controls-section {
            padding: 15px 30px;

            background: var(--stat-bg);
            border-bottom: 1px solid var(--border-color);

            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            align-items: center;
        }

        .search-box {
            flex: 2;

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

            padding: 10px 20px;
            border-radius: 8px;

            cursor: pointer;
            font-size: 14px;
            font-weight: bold;

            transition: all 0.3s ease;
        }

        .export-btn:hover {
            background: #219a52;
            transform: scale(1.02);
        }

        /* Auto-refresh Toggle */

        .refresh-control {
            display: flex;
            align-items: center;
            gap: 8px;

            padding: 8px 15px;

            background: var(--stat-card-bg);
            border-radius: 20px;

            font-size: 13px;
        }

        .refresh-control input {
            cursor: pointer;
            width: 16px;
            height: 16px;
        }

        /* ===== REFRESH INFO BAR ===== */

        .refresh-info {
            padding: 8px 30px;

            background: var(--refresh-bg);
            color: var(--refresh-text);

            font-size: 12px;

            border-bottom: 1px solid var(--border-color);

            display: flex;
            justify-content: space-between;
            align-items: center;

            flex-wrap: wrap;
            gap: 10px;
        }

        /* ===== TABLE SECTION ===== */

        .table-container {
            padding: 20px 30px;
            max-height: 550px;
            overflow-y: auto;
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        th {
            background: var(--table-header-bg);
            color: white;

            padding: 12px;

            text-align: left;
            font-size: 14px;

            position: sticky;
            top: 0;
        }

        td {
            padding: 10px 12px;
            border-bottom: 1px solid var(--border-color);

            font-size: 13px;
        }

        tr:hover {
            background: var(--table-row-hover);
        }

        /* App badge styling */

        .app-badge {
            background: #3498db;
            color: white;

            padding: 4px 8px;
            border-radius: 5px;

            font-size: 11px;
            font-weight: bold;

            display: inline-block;
        }

        /* No results message */

        .no-results {
            text-align: center;
            padding: 50px;

            color: #7f8c8d;
            font-size: 16px;
        }

        /* Footer */

        .footer {
            padding: 15px 30px;

            background: var(--stat-bg);

            text-align: center;
            font-size: 12px;

            color: #7f8c8d;

            border-top: 1px solid var(--border-color);
        }
    </style>
</head>

<body>

    <div class="container">

        <!-- HEADER with Dark Mode Button -->

        <div class="header">

            <div>
                <h1>📊 CrossWatch Activity Dashboard</h1>
                <p>Real-time application tracking • Project 3 Enhanced</p>
            </div>

            <button class="dark-mode-btn" id="darkModeBtn">
                🌙 Dark Mode
            </button>

        </div>

        <!-- STATISTICS CARDS -->

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
                <div class="value" id="lastUpdate" style="font-size: 16px;">-</div>
            </div>

        </div>

        <!-- SEARCH AND CONTROLS -->

        <div class="controls-section">

            <input
                type="text"
                id="searchInput"
                class="search-box"
                placeholder="🔍 Search apps or window titles..."
            >

            <button class="export-btn" id="exportBtn">
                📥 Export to CSV
            </button>

            <div class="refresh-control">
                <input type="checkbox" id="autoRefreshToggle" checked>
                <label>Auto-refresh (5s)</label>
            </div>

        </div>

        <!-- REFRESH INFO -->

        <div class="refresh-info">
            <span>🔄 Data source: activity_log.csv</span>
            <span id="filterStatus">Loading data...</span>
        </div>

        <!-- TABLE CONTAINER -->

        <div class="table-container">

            <div id="logContent">
                <div class="no-results">
                    📭 Loading activities from server...
                </div>
            </div>

        </div>

        <!-- FOOTER -->

        <div class="footer">
            CrossWatch - Local Activity Monitor |
            🔍 Search • 📥 Export • 🌙 Dark Mode
        </div>

    </div>

    <script>

        // ============================================
        // GLOBAL VARIABLES
        // ============================================

        let allLogs = [];
        let autoRefreshEnabled = true;
        let refreshInterval = null;

        // ============================================
        // FUNCTION: Load Logs from Server
        // ============================================

        function loadLogs() {

            console.log("Fetching logs from server...");

            fetch('/api/logs')

                .then(response => response.json())

                .then(data => {

                    console.log("Received data:", data);

                    // Check if there's an error from the server

                    if (data.error) {

                        document.getElementById('logContent').innerHTML =
                            '<div class="no-results">⚠️ ' + data.error + '</div>';

                        return;
                    }

                    // Check if we have logs

                    if (!data.logs || data.logs.length === 0) {

                        document.getElementById('logContent').innerHTML =
                            '<div class="no-results">📭 No data yet. Run python logger.py first!</div>';

                        document.getElementById('totalCount').innerText = '0';
                        document.getElementById('uniqueApps').innerText = '0';

                        return;
                    }

                    // Store all logs globally for filtering

                    allLogs = data.logs;

                    // Update statistics cards

                    document.getElementById('totalCount').innerText = data.total;
                    document.getElementById('uniqueApps').innerText = data.unique_apps;
                    document.getElementById('lastUpdate').innerText =
                        new Date().toLocaleTimeString();

                    // Apply current search filter to display

                    applySearchFilter();

                })

                .catch(error => {

                    console.error("Error fetching logs:", error);

                    document.getElementById('logContent').innerHTML =
                        '<div class="no-results">⚠️ Cannot connect to server.</div>';

                });
        }

        // ============================================
        // FUNCTION: Apply Search Filter
        // ============================================

        function applySearchFilter() {

            const searchInput = document.getElementById('searchInput');

            if (!searchInput) return;

            const searchTerm = searchInput.value.toLowerCase();

            // Filter logs based on search term

            let filteredLogs = allLogs;

            if (searchTerm !== '') {

                filteredLogs = allLogs.filter(log => {

                    return (
                        (log.app && log.app.toLowerCase().includes(searchTerm)) ||
                        (log.window && log.window.toLowerCase().includes(searchTerm))
                    );

                });
            }

            // Update filter status display

            const filterSpan = document.getElementById('filterStatus');

            if (filterSpan) {

                if (searchTerm !== '') {

                    filterSpan.innerHTML =
                        `🔍 Found ${filteredLogs.length} results for "${searchTerm}"`;

                } else {

                    filterSpan.innerHTML =
                        `Showing all ${filteredLogs.length} activities`;

                }
            }

            // Display the filtered logs

            displayLogs(filteredLogs);
        }

        // ============================================
        // FUNCTION: Display Logs as HTML Table
        // ============================================

        function displayLogs(logs) {

            const logContent = document.getElementById('logContent');

            if (!logs || logs.length === 0) {

                logContent.innerHTML =
                    '<div class="no-results">📭 No matching activities found.</div>';

                return;
            }

            // Build HTML table
            // FIXED: Using JavaScript template literals
            // instead of broken \\n string concatenation

            let html = `
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Timestamp</th>
                            <th>Application</th>
                            <th>Window Title</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            // Loop through each log and create a row

            for (let i = 0; i < logs.length; i++) {

                const log = logs[i];

                html += `
                    <tr>
                        <td>${escapeHtml(log.counter || '')}</td>
                        <td>${escapeHtml(log.timestamp || '')}</td>

                        <td>
                            <span class="app-badge">
                                ${escapeHtml(log.app || 'Unknown')}
                            </span>
                        </td>

                        <td>${escapeHtml(log.window || '')}</td>
                    </tr>
                `;
            }

            html += `
                    </tbody>
                </table>
            `;

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

            const searchTerm =
                searchInput ? searchInput.value.toLowerCase() : '';

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

            // Create CSV content

            let csvData =
                "Timestamp,Counter,Application,Window Title\\n";

            for (let log of logsToExport) {

                csvData +=
                    `"${log.timestamp || ''}",` +
                    `"${log.counter || ''}",` +
                    `"${log.app || ''}",` +
                    `"${log.window || ''}"\\n`;
            }

            // Create file blob

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

                if (btn) {
                    btn.innerHTML = '☀️ Light Mode';
                }
            }
        }

        // ============================================
        // AUTO-REFRESH CONTROL
        // ============================================

        function startAutoRefresh() {

            if (refreshInterval) {
                clearInterval(refreshInterval);
            }

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

            // Search input

            const searchInput = document.getElementById('searchInput');

            if (searchInput) {

                searchInput.addEventListener(
                    'keyup',
                    applySearchFilter
                );
            }

            // Export button

            const exportBtn = document.getElementById('exportBtn');

            if (exportBtn) {

                exportBtn.addEventListener(
                    'click',
                    exportToCSV
                );
            }

            // Dark mode button

            const darkModeBtn =
                document.getElementById('darkModeBtn');

            if (darkModeBtn) {

                darkModeBtn.addEventListener(
                    'click',
                    toggleDarkMode
                );
            }

            // Auto-refresh toggle

            const refreshToggle =
                document.getElementById('autoRefreshToggle');

            if (refreshToggle) {

                refreshToggle.addEventListener('change', (e) => {

                    autoRefreshEnabled = e.target.checked;

                    console.log(
                        "Auto-refresh:",
                        autoRefreshEnabled ? "ON" : "OFF"
                    );

                });
            }
        }

        // ============================================
        // PAGE INITIALIZATION
        // ============================================

        // FIXED:
        // Wait until entire HTML page is fully loaded
        // before accessing elements

        window.addEventListener('DOMContentLoaded', () => {

            loadDarkModePreference();

            setupEventListeners();

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
    """
    This class handles incoming web requests from your browser
    It defines what happens when someone visits different URLs
    """

    # Suppress server log messages to keep console clean

    def log_message(self, format, *args):
        """Override to reduce console spam"""
        pass

    def do_GET(self):
        """
        This function runs whenever someone visits the server
        self.path tells us which URL was requested
        """

        # OPTION 1: Main dashboard page

        if self.path == '/' or self.path == '/dashboard':

            self.send_response(200)

            self.send_header(
                'Content-type',
                'text/html; charset=utf-8'
            )

            self.end_headers()

            self.wfile.write(
                HTML_TEMPLATE.encode('utf-8')
            )

        # OPTION 2: API endpoint for data

        elif self.path == '/api/logs':

            self.send_response(200)

            self.send_header(
                'Content-type',
                'application/json'
            )

            self.send_header(
                'Access-Control-Allow-Origin',
                '*'
            )

            self.end_headers()

            logs = []

            try:

                # Check if CSV file exists

                if not os.path.exists('activity_log.csv'):

                    response = {
                        'error': 'activity_log.csv not found.',
                        'total': 0,
                        'unique_apps': 0,
                        'logs': []
                    }

                else:

                    # Open and read CSV file

                    with open(
                        'activity_log.csv',
                        'r',
                        encoding='utf-8',
                        errors='ignore'
                    ) as file:

                        reader = csv.DictReader(file)

                        for row in reader:

                            # Skip empty rows

                            if not row.get('Timestamp'):
                                continue

                            # Create log entry dictionary

                            log_entry = {
                                'timestamp': row.get('Timestamp', ''),
                                'counter': row.get('Counter', ''),
                                'app': row.get('Application', ''),
                                'window': row.get('Window Title', '')[:100]
                            }

                            logs.append(log_entry)

                    # Count unique apps

                    unique_apps_set = set()

                    for log in logs:

                        if log['app']:
                            unique_apps_set.add(log['app'])

                    unique_apps_count = len(unique_apps_set)

                    # Reverse logs (newest first)

                    logs.reverse()

                    # Limit logs for performance

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

            # Send JSON response

            self.wfile.write(
                json.dumps(
                    response,
                    indent=2,
                    ensure_ascii=False
                ).encode('utf-8')
            )

        # OPTION 3: Any other URL

        else:

            self.send_response(404)

            self.send_header(
                'Content-type',
                'text/html'
            )

            self.end_headers()

            self.wfile.write(
                b'<h1>404 - Page Not Found</h1>'
            )

# ============================================
# START THE SERVER
# ============================================

def run_server():
    """Starts the web server on port 8000"""

    port = 8000

    server_address = ('localhost', port)

    # Create the server instance

    httpd = HTTPServer(
        server_address,
        CrossWatchHandler
    )

    # Startup information

    print("=" * 60)
    print("🌟 CrossWatch Web Server - PROJECT 3 ENHANCED!")
    print("=" * 60)

    print(f"📍 Local URL: http://localhost:{port}")
    print(f"📍 Network URL: http://127.0.0.1:{port}")

    print("\n✨ FEATURES:")
    print("   🔍 Search")
    print("   📥 Export CSV")
    print("   🌙 Dark Mode")
    print("   🔄 Auto Refresh")

    print("\n⚠️ Press CTRL + C to stop the server")

    print("=" * 60)

    print("\n✅ Server is running...\n")

    try:

        # Keep server running forever

        httpd.serve_forever()

    except KeyboardInterrupt:

        print("\n\n✅ Web server stopped!")

        httpd.server_close()

# ============================================
# RUN THE SERVER
# ============================================

if __name__ == '__main__':
    run_server()