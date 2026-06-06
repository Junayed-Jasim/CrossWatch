# CrossWatch Logger - Linux (Phase 3b)
# X11/Wayland event-driven window tracking
# Author: CrossWatch Project

import time
import datetime
import csv
import os
import json
import threading
import sys
import subprocess

# ============================================
# DETECT DISPLAY SERVER
# ============================================

def detect_display_server():
    wayland = os.environ.get('WAYLAND_DISPLAY')
    x11     = os.environ.get('DISPLAY')
    if wayland:
        return 'wayland'
    elif x11:
        return 'x11'
    else:
        return 'none'

DISPLAY_SERVER = detect_display_server()
print(f"🖥️  Display server: {DISPLAY_SERVER.upper()}")

# ============================================
# X11 IMPORTS
# ============================================

X11_AVAILABLE = False
if DISPLAY_SERVER == 'x11':
    try:
        from Xlib import display as xdisplay, X
        from Xlib.ext import record
        from Xlib.protocol import rq
        import Xlib.Xatom
        X11_AVAILABLE = True
    except ImportError:
        print("⚠️  python-xlib not installed. Run: pip install python-xlib")

# ============================================
# TRAY IMPORTS
# ============================================

try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False
    print("⚠️  pystray not installed. Run: pip install pystray")

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("⚠️  psutil not installed. Run: pip install psutil")

try:
    import urllib.request
    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False

# ============================================
# LOAD CONFIG
# ============================================

DEFAULT_CONFIG = {
    "device_id":      "linux-main",
    "server_url":     "http://localhost:8000",
    "api_key":        "crosswatch123",
    "post_to_server": False
}

def load_config():
    if os.path.exists('config.json'):
        try:
            with open('config.json', 'r') as f:
                cfg = json.load(f)
            return {**DEFAULT_CONFIG, **cfg}
        except Exception as e:
            print(f"⚠️  Could not load config.json: {e}")
    return DEFAULT_CONFIG

CONFIG = load_config()

# ============================================
# DATA MANAGEMENT
# ============================================

def ask_user_about_data():
    if os.path.exists("activity_log.csv"):
        print("\n📋 Found existing activity_log.csv file!")
        print("\nWhat would you like to do?")
        print("   1 - Keep existing data")
        print("   2 - Delete old data (start fresh)")
        print("   3 - Cancel")
        choice = input("\nEnter 1, 2, or 3: ")
        if choice == '1':
            print("\n✅ Keeping existing data.")
            return 'a'
        elif choice == '2':
            print("\n⚠️  Deleting old data...")
            os.remove("activity_log.csv")
            print("✅ Old data deleted.")
            return 'w'
        elif choice == '3':
            print("\n❌ Cancelled.")
            return 'cancel'
        else:
            print("\n⚠️  Invalid choice. Keeping existing data.")
            return 'a'
    else:
        print("\n📋 No existing log file found. Creating new one.")
        return 'w'

write_mode = ask_user_about_data()
if write_mode == 'cancel':
    print("\n🚪 Exiting logger...")
    sys.exit()

# ============================================
# CSV SETUP
# ============================================

def setup_csv():
    if write_mode == 'w':
        with open("activity_log.csv", "w", newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(["Timestamp", "Counter", "Application", "Window Title"])
        print("✅ Created new activity_log.csv")
    else:
        if os.path.exists("activity_log.csv"):
            with open("activity_log.csv", "r", encoding='utf-8') as f:
                first_line = f.readline().strip()
            if first_line != "Timestamp,Counter,Application,Window Title":
                with open("activity_log.csv", "r", encoding='utf-8') as f:
                    old_data = f.readlines()
                with open("activity_log.csv", "w", newline='', encoding='utf-8') as f:
                    csv.writer(f).writerow(["Timestamp", "Counter", "Application", "Window Title"])
                    for line in old_data:
                        if line.strip() and not line.startswith("Timestamp"):
                            f.write(line)
        print("✅ Opened existing activity_log.csv")

setup_csv()

# ============================================
# TRACKING STATE
# ============================================

counter     = 0
last_app    = None
last_window = None
state_lock  = threading.Lock()

# ============================================
# HELPER: Get active window info (X11)
# ============================================

def get_active_window_x11():
    try:
        d         = xdisplay.Display()
        root      = d.screen().root
        net_wm    = d.intern_atom('_NET_ACTIVE_WINDOW')
        win_id    = root.get_full_property(net_wm, X.AnyPropertyType)
        if not win_id or not win_id.value:
            return None, None
        win       = d.create_resource_object('window', win_id.value[0])
        wm_name   = d.intern_atom('_NET_WM_NAME')
        title_prop = win.get_full_property(wm_name, 0)
        if title_prop:
            window_title = title_prop.value.decode('utf-8', errors='ignore')
        else:
            window_title = win.get_wm_name() or ''
        pid_atom  = d.intern_atom('_NET_WM_PID')
        pid_prop  = win.get_full_property(pid_atom, X.AnyPropertyType)
        if pid_prop and PSUTIL_AVAILABLE:
            pid      = pid_prop.value[0]
            app_name = psutil.Process(pid).name()
        else:
            app_name = 'unknown'
        d.close()
        return app_name, window_title
    except Exception as e:
        return None, None

# ============================================
# HELPER: Degraded mode (Wayland)
# ============================================

def get_active_window_wayland():
    # Wayland does not allow cross-app window monitoring without
    # compositor-specific protocols. Running in degraded mode.
    return 'wayland-session', '[active window unavailable on Wayland]'

# ============================================
# HELPER: Get active window (auto-select path)
# ============================================

def get_active_window_info():
    if DISPLAY_SERVER == 'x11' and X11_AVAILABLE:
        return get_active_window_x11()
    elif DISPLAY_SERVER == 'wayland':
        return get_active_window_wayland()
    else:
        return None, None

# ============================================
# HELPER: Write one row to CSV
# ============================================

def write_csv_row(app_name, window_title):
    global counter
    with state_lock:
        counter += 1
        now         = datetime.datetime.now()
        row_counter = counter
    with open("activity_log.csv", "a", newline='', encoding='utf-8') as f:
        csv.writer(f).writerow([now, row_counter, app_name, window_title[:100]])
    print(f"{now} | #{row_counter} | {app_name} | {window_title[:60]}")

# ============================================
# HELPER: POST event to server (optional)
# ============================================

def post_event_to_server(app_name, window_title):
    if not CONFIG.get('post_to_server'):
        return
    try:
        now     = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        payload = json.dumps({
            'device_id': CONFIG['device_id'],
            'app':       app_name,
            'window':    window_title[:100],
            'timestamp': now,
        }).encode('utf-8')
        req = urllib.request.Request(
            CONFIG['server_url'] + '/api/events',
            data    = payload,
            headers = {
                'Content-Type': 'application/json',
                'X-Token':      CONFIG['api_key'],
            },
            method = 'POST'
        )
        urllib.request.urlopen(req, timeout=3)
    except Exception:
        pass

# ============================================
# CORE: Handle window change
# ============================================

def on_window_change(app_name, window_title):
    global last_app, last_window
    if not app_name or not window_title:
        return
    with state_lock:
        if app_name == last_app and window_title == last_window:
            return
        last_app    = app_name
        last_window = window_title
    write_csv_row(app_name, window_title)
    post_event_to_server(app_name, window_title)

# ============================================
# POLLER — 0.1s title change detection
# ============================================

def start_poller():
    def poll():
        while True:
            try:
                app_name, window_title = get_active_window_info()
                on_window_change(app_name, window_title)
            except Exception:
                pass
            time.sleep(0.1)

    t = threading.Thread(target=poll, daemon=True)
    t.start()
    print("✅ Poller active (0.1s)")

# ============================================
# TRAY ICON
# ============================================

def create_tray_icon():
    if not TRAY_AVAILABLE:
        return None

    img  = Image.new('RGB', (64, 64), color=(8, 12, 20))
    draw = ImageDraw.Draw(img)
    draw.ellipse([16, 16, 48, 48], fill=(0, 224, 160))

    def on_quit(icon, item):
        icon.stop()
        os._exit(0)

    menu = pystray.Menu(
        pystray.MenuItem('CrossWatch Logger — Running', None, enabled=False),
        pystray.MenuItem('Quit', on_quit)
    )

    icon = pystray.Icon('CrossWatch', img, 'CrossWatch Logger', menu)
    return icon

# ============================================
# DEGRADED MODE WARNING
# ============================================

def print_capability_warning():
    if DISPLAY_SERVER == 'wayland':
        print("\n⚠️  DEGRADED MODE — Wayland detected")
        print("   Active window title unavailable without compositor support.")
        print("   Only session-level events will be logged.")
        print("   For full monitoring, use X11 session.\n")
    elif DISPLAY_SERVER == 'none':
        print("\n❌ No display server detected. Cannot monitor windows.")
        sys.exit()

# ============================================
# MAIN
# ============================================

print("\n" + "=" * 50)
print("🎯 CrossWatch Logger — Linux (Phase 3b)")
print("=" * 50)
print(f"   Device ID     : {CONFIG['device_id']}")
print(f"   Server        : {CONFIG['server_url']}")
print(f"   Display server: {DISPLAY_SERVER.upper()}")
print(f"   Post events   : {CONFIG.get('post_to_server', False)}")
print("=" * 50)

print_capability_warning()

# Log current window immediately on startup
app, win = get_active_window_info()
if app:
    on_window_change(app, win)

# Start poller
start_poller()

# Start tray icon (blocks main thread)
icon = create_tray_icon()
if icon:
    icon.run()
else:
    print("ℹ️  No tray icon — running in terminal. Press CTRL+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n✅ Logger stopped.")