# CrossWatch Web Server - Project 5: Project 4 + WebSocket Live Streaming
# Features: All Project 4 features + real-time WebSocket activity feed
# Author: CrossWatch Project

# ============================================
# IMPORT LIBRARIES
# ============================================
from http.server import HTTPServer, BaseHTTPRequestHandler
import csv
import json
import os
import socket
import urllib.parse
import time
import threading
import asyncio
import io

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    print("⚠️  websockets not installed. Run: pip install websockets")

# ============================================
# CONFIGURATION
# ============================================

SECRET_PASSWORD = "crosswatch123"
PORT = 8000
SERVER_HOST = '0.0.0.0'
WEBSOCKET_PORT = 8765

# ============================================
# GLOBAL STATE FOR WEBSOCKET
# ============================================

connected_clients = set()
activity_history = []
client_lock = threading.Lock()
ws_event_loop = None  # Saved so the CSV watcher thread can post onto it

# ============================================
# HELPER: Get Local IP
# ============================================

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except:
            return "127.0.0.1"

# ============================================
# HELPER: Parse a single CSV line safely
# ============================================

def parse_csv_line(line: str):
    try:
        reader = csv.reader(io.StringIO(line))
        parts = next(reader)
        if len(parts) < 4:
            return None
        return {
            'timestamp': parts[0].strip(),
            'counter':   parts[1].strip(),
            'app':       parts[2].strip(),
            'window':    parts[3].strip()[:100],
        }
    except Exception:
        return None

# ============================================
# CSV FILE WATCHER — runs in a daemon thread
# Detects new lines and broadcasts via WebSocket
# ============================================

def watch_csv_file():
    global activity_history, ws_event_loop

    last_line_count = 0

    # Pre-load last 50 entries on startup
    try:
        if os.path.exists('activity_log.csv'):
            with open('activity_log.csv', 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                for row in rows[-50:]:
                    if row.get('Timestamp'):
                        activity_history.append({
                            'timestamp': row.get('Timestamp', ''),
                            'counter':   row.get('Counter', ''),
                            'app':       row.get('Application', ''),
                            'window':    row.get('Window Title', '')[:100],
                        })
                last_line_count = len(rows) + 1  # +1 for header
    except Exception as e:
        print(f"⚠️  CSV pre-load error: {e}")

    while True:
        try:
            if os.path.exists('activity_log.csv'):
                with open('activity_log.csv', 'r', encoding='utf-8', errors='ignore') as f:
                    all_lines = f.readlines()

                current_count = len(all_lines)

                if current_count > last_line_count:
                    new_lines = all_lines[last_line_count:]
                    last_line_count = current_count

                    for line in new_lines:
                        line = line.strip()
                        if not line or line.startswith('Timestamp'):
                            continue

                        activity = parse_csv_line(line)
                        if not activity:
                            continue

                        activity_history.append(activity)
                        if len(activity_history) > 50:
                            activity_history.pop(0)

                        if ws_event_loop is not None and ws_event_loop.is_running():
                            asyncio.run_coroutine_threadsafe(
                                broadcast_to_all(activity),
                                ws_event_loop
                            )

            time.sleep(1)

        except Exception as e:
            print(f"⚠️  CSV watcher error: {e}")
            time.sleep(2)

# ============================================
# WEBSOCKET HANDLER
# ============================================

async def websocket_handler(websocket):
    client_address = websocket.remote_address[0] if websocket.remote_address else 'unknown'
    print(f"🔌 WebSocket client connected: {client_address}")

    with client_lock:
        connected_clients.add(websocket)

    try:
        await websocket.send(json.dumps({
            'type':    'welcome',
            'message': 'Connected to CrossWatch real-time feed',
            'history': activity_history[-20:],
        }))

        async for message in websocket:
            try:
                data = json.loads(message)
                if data.get('type') == 'ping':
                    await websocket.send(json.dumps({'type': 'pong'}))
            except Exception:
                pass

    except Exception:
        pass
    finally:
        with client_lock:
            connected_clients.discard(websocket)


async def broadcast_to_all(activity: dict):
    if not connected_clients:
        return

    message = json.dumps({
        'type':      'activity',
        'data':      activity,
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
    })

    with client_lock:
        clients = list(connected_clients)

    for client in clients:
        try:
            await client.send(message)
        except Exception:
            pass

# ============================================
# START WEBSOCKET SERVER IN BACKGROUND THREAD
# ============================================

def start_websocket_server_thread():
    global ws_event_loop

    def run():
        global ws_event_loop

        async def _main():
            async with websockets.serve(websocket_handler, "0.0.0.0", WEBSOCKET_PORT):
                local_ip = get_local_ip()
                print(f"🔌 WebSocket server running on ws://0.0.0.0:{WEBSOCKET_PORT}")
                print(f"   From other devices: ws://{local_ip}:{WEBSOCKET_PORT}")
                await asyncio.Future()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        ws_event_loop = loop
        loop.run_until_complete(_main())

    t = threading.Thread(target=run, daemon=True)
    t.start()


def start_csv_watcher():
    t = threading.Thread(target=watch_csv_file, daemon=True)
    t.start()
    print("📁 CSV file watcher started")

# ============================================
# HTML DASHBOARD
# Project 4 UI fully preserved + WebSocket live feed added
# ============================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <title>CrossWatch — Network Viewer</title>

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">

    <style>
        :root {
            --bg:               #080c14;
            --surface:          #0d1320;
            --surface-raised:   #111926;
            --surface-hover:    #162030;
            --border:           #1e2d42;
            --border-subtle:    #131f30;
            --accent:           #00c2ff;
            --accent-dim:       rgba(0, 194, 255, 0.10);
            --accent-glow:      rgba(0, 194, 255, 0.22);
            --green:            #00e0a0;
            --green-dim:        rgba(0, 224, 160, 0.10);
            --amber:            #ffb830;
            --amber-dim:        rgba(255, 184, 48, 0.10);
            --danger:           #ff5270;
            --text-primary:     #dce8f5;
            --text-secondary:   #6e8caa;
            --text-muted:       #334d68;
            --font-ui:          'Plus Jakarta Sans', sans-serif;
            --font-mono:        'JetBrains Mono', monospace;
            --radius-sm:        6px;
            --radius-md:        10px;
            --radius-lg:        16px;
            --transition:       0.2s ease;
        }

        body.light-mode {
            --bg:               #eae7e0;
            --surface:          #f5f3ee;
            --surface-raised:   #faf9f5;
            --surface-hover:    #edeae4;
            --border:           #d2cbc0;
            --border-subtle:    #e2ddd5;
            --accent:           #2563eb;
            --accent-dim:       rgba(37, 99, 235, 0.08);
            --accent-glow:      rgba(37, 99, 235, 0.16);
            --green:            #0d9468;
            --green-dim:        rgba(13, 148, 104, 0.08);
            --amber:            #b86e00;
            --amber-dim:        rgba(184, 110, 0, 0.08);
            --danger:           #dc2626;
            --text-primary:     #2a2520;
            --text-secondary:   #5c554d;
            --text-muted:       #9a9186;
        }

        *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: var(--font-ui);
            background-color: var(--bg);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 24px 20px;
            transition: background-color var(--transition), color var(--transition);
            background-image: radial-gradient(ellipse 70% 35% at 50% -5%, rgba(0, 194, 255, 0.06) 0%, transparent 70%);
        }

        body.light-mode { background-image: none; }

        body.light-mode .topbar { background: #1a1a2e; border-color: #2a2a44; }
        body.light-mode .topbar .network-pill { background: rgba(0, 194, 255, 0.10); border-color: rgba(0, 194, 255, 0.25); color: #5dcfef; }
        body.light-mode .btn-theme { background: rgba(255, 255, 255, 0.07); border-color: rgba(255, 255, 255, 0.14); color: #90aec8; }
        body.light-mode .btn-theme:hover { background: rgba(0, 194, 255, 0.13); border-color: rgba(0, 194, 255, 0.30); color: #5dcfef; }
        body.light-mode .stats-row { box-shadow: 0 1px 4px rgba(42, 37, 32, 0.07); }
        body.light-mode .stat-icon.accent { background: var(--accent-dim); border-color: rgba(37, 99, 235, 0.18); }
        body.light-mode .stat-icon.green { background: var(--green-dim); border-color: rgba(13, 148, 104, 0.18); }
        body.light-mode .stat-icon.amber { background: var(--amber-dim); border-color: rgba(184, 110, 0, 0.18); }
        body.light-mode th { background: #ebe8e1; color: #7a7168; }
        body.light-mode .table-wrapper { box-shadow: 0 1px 4px rgba(42, 37, 32, 0.06); }
        body.light-mode .app-badge { background: rgba(37, 99, 235, 0.07); color: #2563eb; border-color: rgba(37, 99, 235, 0.16); }
        body.light-mode .search-input { background: #fdfcfa; border-color: #cfc8bc; }
        body.light-mode .search-input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-glow); }
        body.light-mode .btn-export { background: #0d9468; color: #ffffff; }
        body.light-mode .btn-export:hover { background: #0a7d58; box-shadow: 0 4px 14px rgba(13, 148, 104, 0.20); }
        body.light-mode .refresh-toggle { background: #faf9f5; border-color: #d2cbc0; }
        body.light-mode .footer { background: #f0ede7; border-top: 1px solid var(--border); }
        body.light-mode .status-bar { background: #f0ede7; }

        .app-shell { max-width: 1440px; margin: 0 auto; display: flex; flex-direction: column; gap: 2px; }

        /* ── Topbar ── */
        .topbar {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg) var(--radius-lg) 0 0;
            padding: 18px 28px;
            display: flex; align-items: center; justify-content: space-between;
            gap: 16px; flex-wrap: wrap;
        }

        .topbar__brand { display: flex; align-items: center; gap: 14px; }

        .brand-icon {
            width: 42px; height: 42px;
            border-radius: var(--radius-sm);
            background: var(--accent-dim);
            border: 1px solid rgba(0, 194, 255, 0.3);
            display: flex; align-items: center; justify-content: center;
            font-size: 20px; position: relative; flex-shrink: 0;
        }

        .brand-icon::after {
            content: '';
            position: absolute; inset: -5px;
            border-radius: calc(var(--radius-sm) + 5px);
            border: 1px solid var(--accent);
            opacity: 0;
            animation: pulse-ring 2.8s ease-out infinite;
        }

        @keyframes pulse-ring {
            0%   { opacity: 0.45; transform: scale(1); }
            100% { opacity: 0;    transform: scale(1.4); }
        }

        .brand-text h1 { font-size: 19px; font-weight: 800; letter-spacing: -0.4px; color: #ffffff; line-height: 1.2; }
        .brand-text h1 span { color: var(--accent); }
        .brand-text p { font-size: 11px; color: #6e8caa; font-family: var(--font-mono); letter-spacing: 0.02em; margin-top: 3px; }

        .topbar__controls { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }

        .network-pill {
            display: flex; align-items: center; gap: 8px;
            padding: 7px 14px;
            background: var(--accent-dim);
            border: 1px solid rgba(0, 194, 255, 0.25);
            border-radius: 999px;
            font-family: var(--font-mono); font-size: 12px; color: var(--accent);
            white-space: nowrap;
        }

        /* WebSocket status pill — NEW in P5 */
        .ws-pill {
            display: flex; align-items: center; gap: 8px;
            padding: 7px 14px;
            background: var(--green-dim);
            border: 1px solid rgba(0, 224, 160, 0.25);
            border-radius: 999px;
            font-family: var(--font-mono); font-size: 11px; color: var(--green);
            white-space: nowrap;
            transition: background var(--transition), border-color var(--transition), color var(--transition);
        }

        .ws-pill.disconnected {
            background: rgba(255, 82, 112, 0.08);
            border-color: rgba(255, 82, 112, 0.25);
            color: var(--danger);
        }

        .live-dot {
            width: 7px; height: 7px; border-radius: 50%;
            background: var(--green); box-shadow: 0 0 5px var(--green);
            animation: blink 1.6s ease-in-out infinite; flex-shrink: 0;
        }

        .live-dot.offline {
            background: var(--danger); box-shadow: 0 0 5px var(--danger);
            animation: none;
        }

        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.25; } }

        .btn-theme {
            padding: 7px 15px;
            background: var(--surface-raised);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            color: var(--text-secondary);
            font-family: var(--font-ui); font-size: 12px; font-weight: 600;
            cursor: pointer;
            transition: border-color var(--transition), color var(--transition), background var(--transition);
            white-space: nowrap;
        }

        .btn-theme:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-dim); }

        /* ── Stats Row — 4 columns now (added Live Received) ── */
        .stats-row {
            background: var(--border-subtle);
            border-left: 1px solid var(--border);
            border-right: 1px solid var(--border);
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1px;
        }

        .stat-item {
            background: var(--surface); padding: 16px 22px;
            display: flex; align-items: center; gap: 14px;
            transition: background var(--transition);
        }

        .stat-item:hover { background: var(--surface-raised); }

        .stat-icon {
            width: 38px; height: 38px; border-radius: var(--radius-sm);
            display: flex; align-items: center; justify-content: center;
            font-size: 16px; flex-shrink: 0;
        }

        .stat-icon.accent { background: var(--accent-dim); border: 1px solid rgba(0,194,255,0.2); }
        .stat-icon.green  { background: var(--green-dim);  border: 1px solid rgba(0,224,160,0.2); }
        .stat-icon.amber  { background: var(--amber-dim);  border: 1px solid rgba(255,184,48,0.2); }

        .stat-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.09em; color: var(--text-muted); margin-bottom: 5px; }
        .stat-value { font-size: 26px; font-weight: 800; color: var(--text-primary); line-height: 1; font-variant-numeric: tabular-nums; }
        .stat-value.mono { font-size: 13px; font-family: var(--font-mono); font-weight: 500; }

        /* Clickable Unique Apps stat — same as P4 */
        .stat-item.clickable { cursor: pointer; position: relative; }
        .stat-item.clickable::after {
            content: '›'; position: absolute; right: 16px; top: 50%;
            transform: translateY(-50%); font-size: 20px; color: var(--text-muted);
            transition: color var(--transition), transform var(--transition);
        }
        .stat-item.clickable:hover::after { color: var(--green); transform: translateY(-50%) translateX(3px); }
        .stat-item.clickable:hover { background: var(--surface-raised); }

        /* ── Toolbar ── */
        .toolbar {
            background: var(--surface);
            border-left: 1px solid var(--border);
            border-right: 1px solid var(--border);
            padding: 13px 28px;
            display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
        }

        .search-wrapper { flex: 1; min-width: 200px; position: relative; }
        .search-wrapper svg { position: absolute; left: 11px; top: 50%; transform: translateY(-50%); color: var(--text-muted); pointer-events: none; width: 14px; height: 14px; }

        .search-input {
            width: 100%; padding: 9px 14px 9px 34px;
            background: var(--surface-raised);
            border: 1px solid var(--border); border-radius: var(--radius-sm);
            color: var(--text-primary); font-family: var(--font-ui); font-size: 13px;
            transition: border-color var(--transition), box-shadow var(--transition);
        }
        .search-input::placeholder { color: var(--text-muted); }
        .search-input:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-glow); }

        .btn-export {
            padding: 9px 18px; background: var(--green); color: #041a10;
            font-family: var(--font-ui); font-size: 12px; font-weight: 700;
            border: none; border-radius: var(--radius-sm); cursor: pointer;
            letter-spacing: 0.02em;
            transition: opacity var(--transition), transform var(--transition), box-shadow var(--transition);
            white-space: nowrap;
        }
        .btn-export:hover { opacity: 0.88; transform: translateY(-1px); box-shadow: 0 4px 14px rgba(0, 224, 160, 0.28); }
        .btn-export:active { transform: translateY(0); }

        .refresh-toggle {
            display: flex; align-items: center; gap: 8px; padding: 7px 13px;
            background: var(--surface-raised); border: 1px solid var(--border);
            border-radius: var(--radius-sm); cursor: pointer; user-select: none;
            font-size: 12px; color: var(--text-secondary); font-weight: 600;
            white-space: nowrap; transition: border-color var(--transition);
        }
        .refresh-toggle:hover { border-color: var(--accent); }
        .refresh-toggle input[type="checkbox"] {
            appearance: none; width: 30px; height: 16px;
            background: var(--border); border-radius: 999px;
            position: relative; cursor: pointer; flex-shrink: 0;
            transition: background var(--transition);
        }
        .refresh-toggle input[type="checkbox"]::after {
            content: ''; position: absolute; width: 12px; height: 12px;
            background: var(--text-secondary); border-radius: 50%;
            top: 2px; left: 2px;
            transition: transform var(--transition), background var(--transition);
        }
        .refresh-toggle input[type="checkbox"]:checked { background: var(--green); }
        .refresh-toggle input[type="checkbox"]:checked::after { background: #041a10; transform: translateX(14px); }

        /* ── Status Bar ── */
        .status-bar {
            background: var(--surface-raised);
            border-left: 1px solid var(--border); border-right: 1px solid var(--border);
            border-top: 1px solid var(--border-subtle);
            padding: 7px 28px;
            display: flex; justify-content: space-between; align-items: center;
            gap: 8px; flex-wrap: wrap;
            font-family: var(--font-mono); font-size: 10.5px; color: var(--text-muted);
        }
        .status-bar .hl { color: var(--accent); font-weight: 600; }

        /* Active filter bar */
        .active-filter-bar {
            background: var(--accent-dim);
            border-left: 3px solid var(--accent);
            border-right: 1px solid var(--border);
            padding: 9px 22px;
            display: none;
            align-items: center; justify-content: space-between; gap: 10px;
            font-size: 12px; font-weight: 600; color: var(--accent);
            font-family: var(--font-mono);
        }
        .active-filter-bar.visible { display: flex; }
        .active-filter-bar .clear-filter {
            background: var(--surface-raised); border: 1px solid var(--border);
            color: var(--text-secondary); font-family: var(--font-ui); font-size: 11px;
            font-weight: 600; padding: 4px 12px; border-radius: var(--radius-sm);
            cursor: pointer; transition: background var(--transition), border-color var(--transition), color var(--transition);
        }
        .active-filter-bar .clear-filter:hover { background: var(--accent-dim); border-color: var(--accent); color: var(--accent); }

        /* ── Table ── */
        .table-wrapper {
            background: var(--surface); border: 1px solid var(--border); border-top: none;
            overflow-x: auto; overflow-y: auto; max-height: 540px;
            scrollbar-width: thin; scrollbar-color: var(--border) transparent;
        }
        .table-wrapper::-webkit-scrollbar { width: 5px; height: 5px; }
        .table-wrapper::-webkit-scrollbar-thumb { background: var(--border); border-radius: 999px; }

        table { width: 100%; border-collapse: collapse; min-width: 520px; }
        thead tr { position: sticky; top: 0; z-index: 10; }

        th {
            background: var(--surface-raised); border-bottom: 1px solid var(--border);
            padding: 10px 16px; text-align: left; font-size: 10px; font-weight: 700;
            text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-muted); white-space: nowrap;
        }
        th:first-child { border-left: 3px solid var(--accent); padding-left: 13px; }

        td {
            padding: 10px 16px; border-bottom: 1px solid var(--border-subtle);
            font-size: 12.5px; color: var(--text-secondary);
            transition: background var(--transition);
        }
        td:first-child { font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); border-left: 3px solid transparent; padding-left: 13px; transition: color var(--transition), border-color var(--transition); }
        td:nth-child(2) { font-family: var(--font-mono); font-size: 11.5px; white-space: nowrap; }
        tr:hover td { background: var(--surface-hover); }
        tr:hover td:first-child { border-left-color: var(--accent); color: var(--accent); }

        /* NEW: flash animation for live-inserted rows */
        @keyframes row-flash {
            0%   { background: rgba(0, 224, 160, 0.18); }
            100% { background: transparent; }
        }
        tr.live-new td { animation: row-flash 1.4s ease-out forwards; }

        .app-badge {
            display: inline-flex; align-items: center;
            background: var(--accent-dim); color: var(--accent);
            border: 1px solid rgba(0, 194, 255, 0.18);
            padding: 2px 8px; border-radius: 4px;
            font-size: 11px; font-family: var(--font-mono); font-weight: 600;
            letter-spacing: 0.03em; white-space: nowrap;
        }

        .empty-state { padding: 64px 20px; text-align: center; }
        .empty-state .empty-icon { font-size: 36px; margin-bottom: 14px; opacity: 0.45; }
        .empty-state p { font-size: 13.5px; color: var(--text-secondary); margin-bottom: 6px; }
        .empty-state small { font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); }

        @keyframes row-in { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
        tbody tr.animate-in { animation: row-in 0.2s ease both; }

        /* ── Footer ── */
        .footer {
            background: var(--surface); border: 1px solid var(--border); border-top: none;
            border-radius: 0 0 var(--radius-lg) var(--radius-lg);
            padding: 11px 28px; display: flex; align-items: center; justify-content: space-between;
            flex-wrap: wrap; gap: 8px; font-size: 10.5px; color: var(--text-muted); font-family: var(--font-mono);
        }
        .footer .footer-mark { font-weight: 600; letter-spacing: 0.07em; text-transform: uppercase; font-size: 9.5px; }

        /* ── Apps Modal (same as P4) ── */
        .apps-modal-overlay {
            position: fixed; inset: 0; background: rgba(0,0,0,0.55); backdrop-filter: blur(4px);
            z-index: 900; opacity: 0; visibility: hidden;
            transition: opacity 0.25s ease, visibility 0.25s ease;
        }
        .apps-modal-overlay.active { opacity: 1; visibility: visible; }

        .apps-modal {
            position: fixed; top: 50%; left: 50%;
            transform: translate(-50%, -50%) scale(0.95);
            background: var(--surface); border: 1px solid var(--border);
            border-radius: var(--radius-lg); width: 440px; max-width: 92vw; max-height: 80vh;
            display: flex; flex-direction: column; z-index: 950;
            opacity: 0; visibility: hidden;
            transition: opacity 0.25s ease, visibility 0.25s ease, transform 0.25s ease;
            box-shadow: 0 20px 60px rgba(0,0,0,0.35);
        }
        .apps-modal.active { opacity: 1; visibility: visible; transform: translate(-50%, -50%) scale(1); }

        .apps-modal__header {
            padding: 18px 22px; border-bottom: 1px solid var(--border-subtle);
            display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-shrink: 0;
        }
        .apps-modal__header h2 { font-size: 15px; font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 10px; }
        .apps-modal__header h2 .count-badge {
            font-size: 11px; font-weight: 600; background: var(--green-dim); color: var(--green);
            border: 1px solid rgba(0,224,160,0.2); padding: 2px 8px; border-radius: 999px; font-family: var(--font-mono);
        }
        .apps-modal__close {
            width: 30px; height: 30px; border-radius: var(--radius-sm);
            background: var(--surface-raised); border: 1px solid var(--border);
            color: var(--text-secondary); font-size: 16px; cursor: pointer;
            display: flex; align-items: center; justify-content: center;
            transition: background var(--transition), color var(--transition), border-color var(--transition);
        }
        .apps-modal__close:hover { background: var(--accent-dim); border-color: var(--accent); color: var(--accent); }

        .apps-modal__body {
            overflow-y: auto; padding: 8px 0; flex: 1;
            scrollbar-width: thin; scrollbar-color: var(--border) transparent;
        }
        .apps-modal__body::-webkit-scrollbar { width: 4px; }
        .apps-modal__body::-webkit-scrollbar-thumb { background: var(--border); border-radius: 999px; }

        .app-list-item {
            padding: 11px 22px; display: flex; align-items: center; justify-content: space-between;
            gap: 12px; cursor: pointer; transition: background var(--transition); border-left: 3px solid transparent;
        }
        .app-list-item:hover { background: var(--surface-hover); border-left-color: var(--accent); }
        .app-list-item__name { font-size: 13px; font-weight: 600; color: var(--text-primary); font-family: var(--font-mono); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1; }
        .app-list-item__count { font-size: 11px; font-weight: 600; color: var(--text-muted); font-family: var(--font-mono); background: var(--surface-raised); border: 1px solid var(--border); padding: 2px 9px; border-radius: 999px; flex-shrink: 0; }
        .app-list-item__arrow { color: var(--text-muted); font-size: 12px; flex-shrink: 0; transition: color var(--transition), transform var(--transition); }
        .app-list-item:hover .app-list-item__arrow { color: var(--accent); transform: translateX(2px); }

        /* ── Export Modal (same as P4) ── */

        @media (max-width: 768px) {
            body { padding: 10px; }
            .topbar { padding: 14px 16px; }
            .brand-text h1 { font-size: 16px; }
            .stats-row { grid-template-columns: repeat(2, 1fr); }
            .stat-item { padding: 13px 16px; }
            .toolbar { padding: 11px 16px; }
            .status-bar { padding: 6px 16px; }
            th, td { padding: 9px 12px; }
            .footer { flex-direction: column; text-align: center; padding: 11px 16px; }
        }
    </style>
</head>

<body>
    <div class="app-shell">

        <header class="topbar">
            <div class="topbar__brand">
                <div class="brand-icon">📡</div>
                <div class="brand-text">
                    <h1>Cross<span>Watch</span></h1>
                    <p>Network Viewer &middot; Real-time activity tracking &middot; Project 5</p>
                </div>
            </div>
            <div class="topbar__controls">
                <!-- WebSocket live status pill — NEW -->
                <div class="ws-pill disconnected" id="wsPill">
                    <span class="live-dot offline" id="wsDot"></span>
                    <span id="wsStatusText">Connecting&hellip;</span>
                </div>
                <!-- Original network pill -->
                <div class="network-pill" id="networkBadge">
                    <span class="live-dot"></span>
                    <span>Connecting&hellip;</span>
                </div>
                <button class="btn-theme" id="darkModeBtn">☀️ Light Mode</button>
            </div>
        </header>

        <!-- Stats row — P4 original + NEW "Live Received" counter -->
        <section class="stats-row" aria-label="Summary statistics">
            <div class="stat-item">
                <div class="stat-icon accent">📊</div>
                <div>
                    <div class="stat-label">Total Activities</div>
                    <div class="stat-value" id="totalCount">—</div>
                </div>
            </div>
            <!-- Unique Apps — UNCHANGED from P4, still clickable -->
            <div class="stat-item clickable" id="uniqueAppsStat" title="Click to see all unique apps">
                <div class="stat-icon green">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color:var(--green)"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>
                </div>
                <div>
                    <div class="stat-label">Unique Apps</div>
                    <div class="stat-value" id="uniqueApps">—</div>
                </div>
            </div>
            <!-- NEW: live records received via WebSocket -->
            <div class="stat-item">
                <div class="stat-icon green">⚡</div>
                <div>
                    <div class="stat-label">Live Received</div>
                    <div class="stat-value" id="wsCount">0</div>
                </div>
            </div>
            <div class="stat-item">
                <div class="stat-icon amber">🕐</div>
                <div>
                    <div class="stat-label">Last Update</div>
                    <div class="stat-value mono" id="lastUpdate">—</div>
                </div>
            </div>
        </section>

        <div class="toolbar">
            <div class="search-wrapper">
                <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.7">
                    <circle cx="6.5" cy="6.5" r="4.5"/>
                    <line x1="10.5" y1="10.5" x2="14" y2="14"/>
                </svg>
                <input type="text" id="searchInput" class="search-input"
                    placeholder="Filter by app name or window title&hellip;"
                    autocomplete="off" spellcheck="false">
            </div>
            <button class="btn-export" id="exportBtn">↓ Export CSV</button>
            <label class="refresh-toggle">
                <input type="checkbox" id="autoRefreshToggle" checked>
                Auto-refresh (5s)
            </label>
        </div>

        <div class="status-bar">
            <span>source: activity_log.csv</span>
            <span id="filterStatus">Loading&hellip;</span>
        </div>

        <div class="active-filter-bar" id="activeFilterBar">
            <span>Filtering: <span id="activeFilterName"></span></span>
            <button class="clear-filter" id="clearFilterBtn">✕ Clear Filter</button>
        </div>

        <div class="table-wrapper">
            <div id="logContent">
                <div class="empty-state">
                    <div class="empty-icon">📭</div>
                    <p>Waiting for data from server&hellip;</p>
                    <small>Make sure logger.py is running</small>
                </div>
            </div>
        </div>

        <footer class="footer">
            <span class="footer-mark">CrossWatch &mdash; Network Viewer</span>
            <span>Filter &middot; Export CSV &middot; Dark / Light Mode &middot; LAN Access &middot; ⚡ Live</span>
        </footer>

    </div>

    <!-- Apps Modal — UNCHANGED from P4 -->
    <div class="apps-modal-overlay" id="appsModalOverlay"></div>
    <div class="apps-modal" id="appsModal">
        <div class="apps-modal__header">
            <h2>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color:var(--green)"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>
                Unique Apps
                <span class="count-badge" id="modalAppCount">0</span>
            </h2>
            <button class="apps-modal__close" id="appsModalClose">&times;</button>
        </div>
        <div class="apps-modal__body" id="appsModalBody"></div>
    </div>

    <!-- Export Modal — UNCHANGED from P4 -->
    <div class="apps-modal-overlay" id="exportModalOverlay"></div>
    <div class="apps-modal" id="exportModal" style="width:380px;">
        <div class="apps-modal__header">
            <h2>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color:var(--accent)"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                Export Data
            </h2>
            <button class="apps-modal__close" id="exportModalClose">&times;</button>
        </div>
        <div class="apps-modal__body" style="padding:20px 22px;display:flex;flex-direction:column;gap:12px;overflow-y:visible;">
            <button class="btn-export" id="btnExportCurrent" style="width:100%;text-align:left;display:flex;justify-content:space-between;align-items:center;padding:12px 18px;font-size:13px;">
                <span><strong style="display:block;margin-bottom:2px;">Export Current View</strong><span style="font-weight:400;opacity:0.9;">Download only what's currently filtered</span></span>
                <span style="font-size:16px;">↓</span>
            </button>
            <button class="btn-export" id="btnExportFull" style="width:100%;text-align:left;display:flex;justify-content:space-between;align-items:center;padding:12px 18px;font-size:13px;background:var(--surface-raised);color:var(--text-primary);border:1px solid var(--border);">
                <span><strong style="display:block;margin-bottom:2px;">Download Full History</strong><span style="font-weight:400;color:var(--text-secondary);">The complete original Logs</span></span>
                <span style="font-size:16px;color:var(--text-muted);">↓</span>
            </button>
        </div>
    </div>

    <script>
        // ============================================================
        // CONFIGURATION
        // ============================================================

        const urlParams       = new URLSearchParams(window.location.search);
        const currentPassword = urlParams.get('password') || '';
        const currentHost     = window.location.hostname;
        const WS_PORT         = 8765;

        let apiUrl     = '/api/logs';
        let networkUrl = '/api/network';
        if (currentPassword) {
            apiUrl     = `/api/logs?password=${currentPassword}`;
            networkUrl = `/api/network?password=${currentPassword}`;
        }

        // ============================================================
        // STATE — all from P4 + wsCount
        // ============================================================

        let state = {
            allLogs:           [],
            autoRefresh:       true,
            refreshIntervalId: null,
            firstLoad:         true,
            lastTimeStr:       '',
            appFilter:         null,
            wsCount:           0,        // live records received via WebSocket
            csvTotal:          0,        // full row count from activity_log.csv
            csvTotalKnown:     false,
        };

        // ============================================================
        // WEBSOCKET — NEW in P5
        // ============================================================

        let ws = null;

        function connectWebSocket() {
            const wsUrl = `ws://${currentHost}:${WS_PORT}`;

            try { ws = new WebSocket(wsUrl); } catch(e) { return; }

            ws.onopen = () => {
                setWsPill(true);
            };

            ws.onmessage = (event) => {
                let msg;
                try { msg = JSON.parse(event.data); } catch(e) { return; }

                if (msg.type === 'welcome') {
                    // Server sends last 20 on connect — use them only if table is still empty
                    if (msg.history && msg.history.length && state.allLogs.length === 0) {
                        state.allLogs = msg.history.map(normalise);
                        state.firstLoad = true;
                        applySearchFilter();
                        updateStats(countUniqueApps(state.allLogs));
                    }
                }
                else if (msg.type === 'activity') {
                    const activity = normalise(msg.data);

                    // Prepend to log array (newest first)
                    state.allLogs.unshift(activity);
                    if (state.allLogs.length > 200) state.allLogs.pop();

                    // Update counts
                    state.wsCount++;
                    document.getElementById('wsCount').textContent = state.wsCount;
                    if (state.csvTotalKnown) setCsvTotal(state.csvTotal + 1);
                    updateStats(countUniqueApps(state.allLogs));

                    // If no active search/filter, insert row at top of table directly
                    const searchTerm = (document.getElementById('searchInput')?.value || '').toLowerCase();
                    const appMatches = !state.appFilter || activity.app === state.appFilter;
                    const searchMatches = !searchTerm ||
                        (activity.app && activity.app.toLowerCase().includes(searchTerm)) ||
                        (activity.window && activity.window.toLowerCase().includes(searchTerm));

                    if (appMatches && searchMatches) {
                        prependLiveRow(activity);
                    }
                }
            };

            ws.onerror = () => setWsPill(false);

            ws.onclose = () => {
                setWsPill(false);
                setTimeout(connectWebSocket, 3000);
            };
        }

        function normalise(item) {
            if (typeof item === 'string') {
                const p = item.split(',');
                return { timestamp: p[0]||'', counter: p[1]||'', app: p[2]||'', window: p[3]||'' };
            }
            return { timestamp: item.timestamp||'', counter: item.counter||'', app: item.app||'', window: item.window||'' };
        }

        function countUniqueApps(logs) {
            return new Set(logs.map(l => l.app).filter(Boolean)).size;
        }

        function setWsPill(connected) {
            const pill = document.getElementById('wsPill');
            const dot  = document.getElementById('wsDot');
            const text = document.getElementById('wsStatusText');
            if (connected) {
                pill.classList.remove('disconnected');
                dot.classList.remove('offline');
                text.textContent = 'Live';
            } else {
                pill.classList.add('disconnected');
                dot.classList.add('offline');
                text.textContent = 'Reconnecting…';
            }
        }

        // Insert a single new row at the very top of the existing table
        // without re-rendering everything — keeps scroll position intact
        function prependLiveRow(activity) {
            const tbody = document.querySelector('#logContent tbody');
            if (!tbody) {
                // Table not rendered yet, fall back to full render
                applySearchFilter();
                return;
            }

            const tr = document.createElement('tr');
            tr.classList.add('live-new');   // green flash animation
            tr.innerHTML = `
                <td>${escapeHtml(activity.counter)}</td>
                <td>${escapeHtml(activity.timestamp)}</td>
                <td><span class="app-badge">${escapeHtml(activity.app || 'Unknown')}</span></td>
                <td>${escapeHtml(activity.window)}</td>
            `;
            tbody.insertBefore(tr, tbody.firstChild);

            // Keep table to 200 visible rows max
            while (tbody.rows.length > 200) tbody.deleteRow(tbody.rows.length - 1);
        }

        // ============================================================
        // REST API POLLING — same as P4
        // ============================================================

        function getNetworkInfo() {
            fetch(networkUrl)
                .then(r => r.json())
                .then(data => {
                    const badge = document.getElementById('networkBadge');
                    badge.innerHTML = data.ip
                        ? `<span class="live-dot"></span><span>${data.ip}:${data.port}</span>`
                        : `<span class="live-dot"></span><span>port ${data.port}</span>`;
                })
                .catch(() => {});
        }

        function loadLogs() {
            let url = apiUrl;
            if (state.appFilter) {
                url += (url.includes('?') ? '&' : '?') + `app=${encodeURIComponent(state.appFilter)}`;
            }

            fetch(url)
                .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
                .then(data => {
                    if (data.error) { showError(data.error); return; }
                    if (!data.logs || !data.logs.length) {
                        showEmptyState('No activity yet.', 'Run python logger.py to start recording.');
                        setCsvTotal(0);
                        updateStats(0);
                        return;
                    }
                    state.allLogs = data.logs;
                    setCsvTotal(data.total);
                    updateStats(data.unique_apps);
                    applySearchFilter();
                })
                .catch(err => {
                    if (state.allLogs && state.allLogs.length > 0) {
                        const el = document.getElementById('lastUpdate');
                        if (el) el.innerHTML = `<span style="color:#ff5270;font-weight:600;">Server Offline</span> <span style="opacity:.7;font-size:.9em;margin-left:6px;">(Last: ${state.lastTimeStr})</span>`;
                    } else {
                        showError('Cannot connect to server. Make sure server is running.');
                    }
                });
        }

        function setCsvTotal(total) {
            state.csvTotal = total;
            state.csvTotalKnown = true;
            document.getElementById('totalCount').textContent = state.csvTotal.toLocaleString();
        }

        function updateStats(uniqueAppsCount) {
            document.getElementById('uniqueApps').textContent = uniqueAppsCount;
            state.lastTimeStr = new Date().toLocaleTimeString();
            const el = document.getElementById('lastUpdate');
            if (state.autoRefresh) {
                el.innerHTML = `<span class="live-dot" style="margin-right:6px;display:inline-block;"></span>${state.lastTimeStr}`;
            } else {
                el.innerHTML = `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--text-muted);margin-right:6px;opacity:.8;"></span>${state.lastTimeStr}`;
            }
        }

        function applySearchFilter() {
            const term = (document.getElementById('searchInput')?.value || '').toLowerCase();
            let filtered = state.allLogs;

            if (state.appFilter) filtered = filtered.filter(l => (l.app || 'Unknown') === state.appFilter);
            if (term) filtered = filtered.filter(l =>
                (l.app && l.app.toLowerCase().includes(term)) ||
                (l.window && l.window.toLowerCase().includes(term)));

            const el = document.getElementById('filterStatus');
            if (el) {
                if (state.appFilter && term) {
                    el.innerHTML = `<span class="hl">${filtered.length}</span> results for &ldquo;${term}&rdquo; in <strong>${escapeHtml(state.appFilter)}</strong>`;
                } else if (state.appFilter) {
                    el.innerHTML = `<span class="hl">${filtered.length}</span> activit${filtered.length !== 1 ? 'ies' : 'y'} for <strong>${escapeHtml(state.appFilter)}</strong>`;
                } else if (term) {
                    el.innerHTML = `<span class="hl">${filtered.length}</span> result${filtered.length !== 1 ? 's' : ''} for &ldquo;${term}&rdquo;`;
                } else {
                    el.innerHTML = `Showing all <span class="hl">${filtered.length}</span> activities`;
                }
            }
            displayLogs(filtered);
        }

        function displayLogs(logs) {
            const container = document.getElementById('logContent');
            if (!logs || !logs.length) {
                showEmptyState('No matching activities found.', 'Try a different search term.');
                return;
            }
            let html = `<table><thead><tr><th>#</th><th>Timestamp</th><th>Application</th><th>Window Title</th></tr></thead><tbody>`;
            for (const log of logs) {
                html += `<tr>
                    <td>${escapeHtml(log.counter || '')}</td>
                    <td>${escapeHtml(log.timestamp || '')}</td>
                    <td><span class="app-badge">${escapeHtml(log.app || 'Unknown')}</span></td>
                    <td>${escapeHtml(log.window || '')}</td>
                </tr>`;
            }
            html += `</tbody></table>`;
            container.innerHTML = html;

            if (state.firstLoad) {
                container.querySelectorAll('tbody tr').forEach((row, i) => {
                    row.classList.add('animate-in');
                    row.style.animationDelay = `${Math.min(i * 16, 200)}ms`;
                });
                state.firstLoad = false;
            }
        }

        function escapeHtml(text) {
            if (!text) return '';
            const d = document.createElement('div');
            d.textContent = text;
            return d.innerHTML;
        }

        function showEmptyState(headline, sub) {
            document.getElementById('logContent').innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📭</div>
                    <p>${headline}</p>
                    ${sub ? `<small>${sub}</small>` : ''}
                </div>`;
        }

        function showError(message) {
            document.getElementById('logContent').innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">⚠️</div>
                    <p>${message}</p>
                </div>`;
        }

        // ============================================================
        // EXPORT — same as P4
        // ============================================================

        function exportToCSV(ignoreSearch = false, limit200 = false) {
            const term = (!ignoreSearch && document.getElementById('searchInput')?.value || '').toLowerCase();
            let data = state.allLogs;
            if (term) data = data.filter(l => (l.app && l.app.toLowerCase().includes(term)) || (l.window && l.window.toLowerCase().includes(term)));
            if (limit200) data = data.slice(0, 200);
            if (!data.length) { alert('No data to export!'); return; }

            let csv = 'Timestamp,Counter,Application,Window Title\\n';
            for (const l of data) csv += `"${l.timestamp}",${l.counter},"${l.app}","${l.window}"\\n`;

            let filename = `crosswatch_export_${Date.now()}.csv`;
            if (state.appFilter) {
                const safe = state.appFilter.replace(/[^a-z0-9]/gi, '_').toLowerCase();
                filename = `crosswatch_${safe}_export_${Date.now()}.csv`;
            } else if (term) {
                filename = `crosswatch_search_export_${Date.now()}.csv`;
            }

            const a = Object.assign(document.createElement('a'), {
                href: URL.createObjectURL(new Blob([csv], { type: 'text/csv' })),
                download: filename,
            });
            document.body.appendChild(a); a.click(); document.body.removeChild(a);
        }

        // ============================================================
        // THEME — same as P4
        // ============================================================

        function toggleDarkMode() {
            const isLight = document.body.classList.toggle('light-mode');
            document.getElementById('darkModeBtn').innerHTML = isLight ? '🌙 Dark Mode' : '☀️ Light Mode';
            localStorage.setItem('cwTheme', isLight ? 'light' : 'dark');
        }

        function loadDarkModePreference() {
            if (localStorage.getItem('cwTheme') === 'light') {
                document.body.classList.add('light-mode');
                const btn = document.getElementById('darkModeBtn');
                if (btn) btn.innerHTML = '🌙 Dark Mode';
            }
        }

        // ============================================================
        // AUTO-REFRESH — same as P4
        // ============================================================

        function startAutoRefresh() {
            if (state.refreshIntervalId) clearInterval(state.refreshIntervalId);
            state.refreshIntervalId = setInterval(() => {
                if (state.autoRefresh) loadLogs();
            }, 5000);
        }

        // ============================================================
        // UNIQUE APPS MODAL — same as P4
        // ============================================================

        function openAppsModal() {
            const body = document.getElementById('appsModalBody');
            body.innerHTML = `<div class="empty-state" style="padding:40px 20px;"><p>Loading apps…</p></div>`;
            document.getElementById('appsModalOverlay').classList.add('active');
            document.getElementById('appsModal').classList.add('active');

            let url = '/api/unique-apps';
            if (currentPassword) url += `?password=${currentPassword}`;

            fetch(url)
                .then(r => r.json())
                .then(data => {
                    const sorted = data.apps || [];
                    document.getElementById('modalAppCount').textContent = sorted.length;

                    if (!sorted.length) {
                        body.innerHTML = `<div class="empty-state" style="padding:40px 20px;"><div class="empty-icon">📭</div><p>No apps recorded yet.</p></div>`;
                    } else {
                        body.innerHTML = sorted.map(a => `
                            <div class="app-list-item" data-app="${escapeHtml(a.name)}">
                                <span class="app-list-item__name">${escapeHtml(a.name)}</span>
                                <span class="app-list-item__count">${a.count}</span>
                                <span class="app-list-item__arrow">›</span>
                            </div>`).join('');

                        body.querySelectorAll('.app-list-item').forEach(item => {
                            item.addEventListener('click', () => {
                                filterByApp(item.getAttribute('data-app'));
                                closeAppsModal();
                            });
                        });
                    }
                })
                .catch(() => {
                    body.innerHTML = `<div class="empty-state" style="padding:40px 20px;"><div class="empty-icon">⚠️</div><p>Error loading apps.</p></div>`;
                });
        }

        function closeAppsModal() {
            document.getElementById('appsModalOverlay').classList.remove('active');
            document.getElementById('appsModal').classList.remove('active');
        }

        function filterByApp(appName) {
            state.appFilter = appName;
            document.getElementById('activeFilterName').textContent = appName;
            document.getElementById('activeFilterBar').classList.add('visible');
            document.getElementById('searchInput').value = '';
            loadLogs();
        }

        function clearAppFilter() {
            state.appFilter = null;
            document.getElementById('activeFilterBar').classList.remove('visible');
            document.getElementById('searchInput').value = '';
            loadLogs();
        }

        // ============================================================
        // EXPORT MODAL — same as P4
        // ============================================================

        function openExportModal() {
            const btnCurrent = document.getElementById('btnExportCurrent');
            if (state.appFilter) {
                btnCurrent.innerHTML = `<span><strong style="display:block;margin-bottom:2px;">Export Recent 200</strong><span style="font-weight:400;opacity:0.9;">Download up to 200 recent logs for this app</span></span><span style="font-size:16px;">↓</span>`;
                let btnAppFull = document.getElementById('btnExportAppFull');
                if (!btnAppFull) {
                    btnAppFull = document.createElement('button');
                    btnAppFull.id = 'btnExportAppFull';
                    btnAppFull.className = 'btn-export';
                    btnAppFull.style.cssText = 'width:100%;text-align:left;display:flex;justify-content:space-between;align-items:center;padding:12px 18px;font-size:13px;background:var(--surface-raised);color:var(--text-primary);border:1px solid var(--border);';
                    btnAppFull.addEventListener('click', () => { closeExportModal(); exportToCSV(true, false); });
                    document.getElementById('btnExportFull').before(btnAppFull);
                }
                btnAppFull.style.display = 'flex';
                btnAppFull.innerHTML = `<span><strong style="display:block;margin-bottom:2px;">Download ${escapeHtml(state.appFilter)} Full History</strong><span style="font-weight:400;color:var(--text-secondary);">Export full app history</span></span><span style="font-size:16px;color:var(--text-muted);">↓</span>`;
            } else {
                btnCurrent.innerHTML = `<span><strong style="display:block;margin-bottom:2px;">Export Current View</strong><span style="font-weight:400;opacity:0.9;">Download only what's currently shown</span></span><span style="font-size:16px;">↓</span>`;
                const btnAppFull = document.getElementById('btnExportAppFull');
                if (btnAppFull) btnAppFull.style.display = 'none';
            }
            document.getElementById('exportModalOverlay').classList.add('active');
            document.getElementById('exportModal').classList.add('active');
        }

        function closeExportModal() {
            document.getElementById('exportModalOverlay').classList.remove('active');
            document.getElementById('exportModal').classList.remove('active');
        }

        // ============================================================
        // EVENT LISTENERS
        // ============================================================

        function setupEventListeners() {
            document.getElementById('searchInput')?.addEventListener('input', applySearchFilter);
            document.getElementById('exportBtn')?.addEventListener('click', openExportModal);
            document.getElementById('darkModeBtn')?.addEventListener('click', toggleDarkMode);
            document.getElementById('uniqueAppsStat')?.addEventListener('click', openAppsModal);
            document.getElementById('appsModalOverlay')?.addEventListener('click', closeAppsModal);
            document.getElementById('appsModalClose')?.addEventListener('click', closeAppsModal);
            document.getElementById('clearFilterBtn')?.addEventListener('click', clearAppFilter);
            document.getElementById('exportModalOverlay')?.addEventListener('click', closeExportModal);
            document.getElementById('exportModalClose')?.addEventListener('click', closeExportModal);
            document.getElementById('btnExportCurrent')?.addEventListener('click', () => {
                closeExportModal();
                exportToCSV(false, !!state.appFilter);
            });
            document.getElementById('btnExportFull')?.addEventListener('click', () => {
                closeExportModal();
                let url = '/api/download-csv';
                if (currentPassword) url += `?password=${currentPassword}`;
                window.location.href = url;
            });
            document.getElementById('autoRefreshToggle')?.addEventListener('change', e => {
                state.autoRefresh = e.target.checked;
                const el = document.getElementById('lastUpdate');
                if (state.lastTimeStr && el && !el.innerHTML.includes('Offline')) {
                    if (state.autoRefresh) {
                        el.innerHTML = `<span class="live-dot" style="margin-right:6px;display:inline-block;"></span>${state.lastTimeStr}`;
                    } else {
                        el.innerHTML = `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--text-muted);margin-right:6px;opacity:.8;"></span>${state.lastTimeStr}`;
                    }
                }
            });
            document.addEventListener('keydown', e => {
                if (e.key === 'Escape') { closeAppsModal(); closeExportModal(); }
            });
        }

        // ============================================================
        // INIT
        // ============================================================

        window.addEventListener('DOMContentLoaded', () => {
            loadDarkModePreference();
            setupEventListeners();
            getNetworkInfo();
            loadLogs();
            startAutoRefresh();
            connectWebSocket();   // NEW: start live WebSocket connection
        });
    </script>

</body>
</html>
"""

# ============================================
# PASSWORD HELPERS
# ============================================

def extract_password_from_path(path):
    parsed = urllib.parse.urlparse(path)
    query_params = urllib.parse.parse_qs(parsed.query)
    passwords = query_params.get('password', [])
    return passwords[0] if passwords else None

# ============================================
# HTTP SERVER HANDLER — same as P4 + kept all endpoints
# ============================================

class CrossWatchHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed       = urllib.parse.urlparse(self.path)
        path         = parsed.path
        query_params = urllib.parse.parse_qs(parsed.query)
        pw_from_url  = query_params.get('password', [None])[0]

        # Auth check (bypass for /api/network)
        if path != '/api/network':
            client_ip  = self.client_address[0]
            authorized = (client_ip in ('127.0.0.1', 'localhost')) or (pw_from_url == SECRET_PASSWORD)

            if not authorized:
                self.send_response(401)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                host = self.headers.get('Host', 'IP_ADDRESS')
                error_html = f"""<!DOCTYPE html>
<html><head><title>CrossWatch — Access Denied</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
<style>
body{{font-family:'Plus Jakarta Sans',sans-serif;background:#080c14;color:#dce8f5;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px;margin:0;}}
.card{{max-width:480px;width:100%;background:#0d1320;border:1px solid #1e2d42;border-top:3px solid #ff5270;border-radius:12px;padding:40px 36px;text-align:center;}}
h1{{font-size:22px;font-weight:800;color:#ff5270;margin:18px 0 10px;}}
p{{color:#6e8caa;font-size:13.5px;line-height:1.6;margin-bottom:10px;}}
code{{display:block;background:#111926;border:1px solid #1e2d42;border-radius:6px;padding:12px 16px;font-family:'JetBrains Mono',monospace;font-size:12px;color:#00c2ff;word-break:break-all;margin:20px 0;text-align:left;}}
small{{color:#334d68;font-size:11px;font-family:'JetBrains Mono',monospace;}}
</style></head>
<body><div class="card"><div style="font-size:40px;">🔒</div>
<h1>Access Denied</h1>
<p>This dashboard is password protected. Add your password to the URL:</p>
<code>http://{host}/?password={SECRET_PASSWORD}</code>
<small>Accessing from the same computer does not require a password.</small>
</div></body></html>"""
                self.wfile.write(error_html.encode('utf-8'))
                return

        # /api/network
        if path == '/api/network':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            local_ip = get_local_ip()
            self.wfile.write(json.dumps({
                'ip': local_ip, 'port': PORT,
                'ws_port': WEBSOCKET_PORT,
                'message': f'Access from http://{local_ip}:{PORT}/?password={SECRET_PASSWORD}'
            }, indent=2).encode())

        # Main dashboard
        elif path in ('/', '/dashboard'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode('utf-8'))

        # /api/logs
        elif path == '/api/logs':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            app_filter = query_params.get('app', [None])[0]
            logs = []
            try:
                if not os.path.exists('activity_log.csv'):
                    response = {'error': 'activity_log.csv not found. Run python logger.py first!', 'total': 0, 'unique_apps': 0, 'logs': []}
                else:
                    total_count = 0
                    unique_apps_set = set()
                    with open('activity_log.csv', 'r', encoding='utf-8', errors='ignore') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            if not row.get('Timestamp'):
                                continue
                            app_name = row.get('Application', '')
                            total_count += 1
                            if app_name: unique_apps_set.add(app_name)
                            if app_filter and app_filter != app_name:
                                continue
                            logs.append({
                                'timestamp': row.get('Timestamp', ''),
                                'counter':   row.get('Counter', ''),
                                'app':       app_name,
                                'window':    row.get('Window Title', '')[:100],
                            })
                    logs.reverse()
                    if not app_filter: logs = logs[:200]
                    response = {'total': total_count, 'unique_apps': len(unique_apps_set), 'logs': logs}
            except Exception as e:
                response = {'error': f'Error reading log file: {e}', 'total': 0, 'unique_apps': 0, 'logs': []}

            self.wfile.write(json.dumps(response, indent=2, ensure_ascii=False).encode())

        # /api/unique-apps
        elif path == '/api/unique-apps':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            app_counts = {}
            try:
                if os.path.exists('activity_log.csv'):
                    with open('activity_log.csv', 'r', encoding='utf-8', errors='ignore') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            app = row.get('Application', '').strip()
                            if app: app_counts[app] = app_counts.get(app, 0) + 1
            except Exception:
                pass
            self.wfile.write(json.dumps({
                'apps': [{'name': k, 'count': v} for k, v in sorted(app_counts.items(), key=lambda x: -x[1])]
            }, indent=2, ensure_ascii=False).encode())

        # /api/download-csv
        elif path == '/api/download-csv':
            try:
                if os.path.exists('activity_log.csv'):
                    self.send_response(200)
                    self.send_header('Content-type', 'text/csv')
                    self.send_header('Content-Disposition', f'attachment; filename="crosswatch_full_logs_{int(time.time()*1000)}.csv"')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    with open('activity_log.csv', 'rb') as f:
                        self.wfile.write(f.read())
                else:
                    self.send_response(404); self.end_headers(); self.wfile.write(b'File not found')
            except Exception as e:
                self.send_response(500); self.end_headers(); self.wfile.write(str(e).encode())

        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<h1>404 - Page Not Found</h1>')

# ============================================
# ENTRY POINT
# ============================================

def run_server():
    if not WEBSOCKETS_AVAILABLE:
        print("❌ Cannot start: websockets library is missing.")
        print("   Run: pip install websockets")
        return

    local_ip = get_local_ip()

    start_csv_watcher()
    start_websocket_server_thread()
    time.sleep(0.5)  # Let WS loop initialise before printing

    httpd = HTTPServer((SERVER_HOST, PORT), CrossWatchHandler)

    print("=" * 65)
    print("🌐 CrossWatch Network Viewer — PROJECT 5 (Live + P4 features)")
    print("=" * 65)
    print(f"\n📍 HTTP Dashboard  : http://localhost:{PORT}")
    print(f"📍 Network URL     : http://{local_ip}:{PORT}/?password={SECRET_PASSWORD}")
    print(f"\n🔌 WebSocket       : ws://{local_ip}:{WEBSOCKET_PORT}")
    print(f"\n🔒 Password        : {SECRET_PASSWORD}")
    print("\n✨ FEATURES:")
    print("   ⚡ Real-time WebSocket live rows (green flash on new entry)")
    print("   📊 Unique Apps modal with per-app filter")
    print("   ↓  Export CSV (current view or full history)")
    print("   🔄 REST API fallback polling every 5s")
    print("   🌙 Dark / Light mode")
    print("\n⚠️  Press CTRL+C to stop")
    print("=" * 65)
    print("✅ Servers running…\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n✅ Stopped.")
        httpd.server_close()

if __name__ == '__main__':
    run_server()