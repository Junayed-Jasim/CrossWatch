# CrossWatch Logger - Phase 3a
# Event-driven foreground window tracking (no polling)
# Author: CrossWatch Project

import time
import datetime
import csv
import os
import json
import threading
import sys

try:
    import win32gui
    import win32process
    import win32con
    import win32api
    import win32event
    import ctypes
    import ctypes.wintypes
    import psutil
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    print("⚠️  pywin32 not installed. Run: pip install pywin32")

try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False
    print("⚠️  pystray not installed. Run: pip install pystray")

try:
    import urllib.request
    import urllib.parse
    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False

# ============================================
# LOAD CONFIG
# ============================================

DEFAULT_CONFIG = {
    "device_id":  "desktop-main",
    "server_url": "http://localhost:8000",
    "api_key":    "crosswatch123",
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

print("🎯 CrossWatch Logger Started!")
print("=" * 40)

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

# ============================================
#  Ask user what they want (or just start)
# ============================================

write_mode = ask_user_about_data()
if write_mode == 'cancel':
    print("\n🚪 Exiting logger...")
    sys.exit()

# ============================================
# STEP 3: Create or open the CSV file based on user's choice
# ============================================

# 'w' mode = create new file with headers (deletes old data)
# 'a' mode = open existing file (keeps old data, but need to check if headers exist)

# ============================================
# CSV SETUP
# ============================================

def setup_csv():
    if write_mode == 'w':
        with open("activity_log.csv", "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Counter", "Application", "Window Title"])
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

counter       = 0
last_app      = None
last_window   = None
state_lock    = threading.Lock()

# ============================================
# HELPER: Get current foreground window info
# ============================================

def get_foreground_window_info():
    try:
        hwnd         = win32gui.GetForegroundWindow()
        window_title = win32gui.GetWindowText(hwnd)
        _, pid       = win32process.GetWindowThreadProcessId(hwnd)
        app_name     = psutil.Process(pid).name()
        return app_name, window_title
    except Exception:
        return None, None

# ============================================
# HELPER: Write one row to CSV
# ============================================

def write_csv_row(app_name, window_title):
    global counter
    with state_lock:
        counter += 1
        now = datetime.datetime.now()
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
    except Exception as e:
        print(f"⚠️  Could not post to server: {e}")

# ============================================
# CORE: Handle foreground window change
# ============================================

def on_foreground_change(app_name, window_title):
    global last_app, last_window

    if not app_name or not window_title:
        return

    # Deduplication — skip if same as last logged
    with state_lock:
        if app_name == last_app and window_title == last_window:
            return
        last_app    = app_name
        last_window = window_title

    write_csv_row(app_name, window_title)
    post_event_to_server(app_name, window_title)

# ============================================
# TITLE CHANGE POLLER — catches tab/file switches
# ============================================

def start_title_poller():
    def poll():
        while True:
            try:
                app_name, window_title = get_foreground_window_info()
                on_foreground_change(app_name, window_title)
            except Exception:
                pass
            time.sleep(0.1)

    t = threading.Thread(target=poll, daemon=True)
    t.start()
    print("✅ Title poller active (0.1s)")

# ============================================
# WIN32 EVENT HOOK — fires on foreground change
# ============================================

def start_event_hook():
    if not WIN32_AVAILABLE:
        print("⚠️  win32 not available. Cannot start event hook.")
        return

    WinEventProcType = ctypes.WINFUNCTYPE(
        None,
        ctypes.wintypes.HANDLE,
        ctypes.wintypes.DWORD,
        ctypes.wintypes.HWND,
        ctypes.wintypes.LONG,
        ctypes.wintypes.LONG,
        ctypes.wintypes.DWORD,
        ctypes.wintypes.DWORD
    )

    def hook_callback(hWinEventHook, event, hwnd, idObject, idChild, dwEventThread, dwmsEventTime):
        app_name, window_title = get_foreground_window_info()
        on_foreground_change(app_name, window_title)

    callback = WinEventProcType(hook_callback)

    hook = ctypes.windll.user32.SetWinEventHook(
        win32con.EVENT_SYSTEM_FOREGROUND,
        win32con.EVENT_SYSTEM_FOREGROUND,
        0,
        callback,
        0, 0,
        win32con.WINEVENT_OUTOFCONTEXT
    )

    if not hook:
        print("❌ Could not set event hook.")
        return

    print("✅ Event hook active — tracking foreground changes")

    msg = ctypes.wintypes.MSG()
    while ctypes.windll.user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) != 0:
        ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
        ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))

# ============================================
# TRAY ICON
# ============================================

def create_tray_icon():
    if not TRAY_AVAILABLE:
        return None

    # Green circle icon
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
# MAIN
# ============================================

print("\n" + "=" * 50)
print("🎯 CrossWatch Logger — Phase 3a")
print("=" * 50)
print(f"   Device ID  : {CONFIG['device_id']}")
print(f"   Server     : {CONFIG['server_url']}")
print(f"   Post events: {CONFIG.get('post_to_server', False)}")
print("=" * 50)
print("Tracking foreground window changes...")
print("Right-click tray icon to quit.\n")

# Log current window immediately on startup
if WIN32_AVAILABLE:
    app, win = get_foreground_window_info()
    if app:
        on_foreground_change(app, win)

# Start event hook in background thread
hook_thread = threading.Thread(target=start_event_hook, daemon=True)
hook_thread.start()
start_title_poller()

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