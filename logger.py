# CrossWatch Activity Logger
# Tracks which application you're using
# Saves as CSV for easy analysis in Excel

import sys
# This makes Python print each line immediately instead of waiting/buffering
sys.stdout.reconfigure(line_buffering=True)

import time
import datetime
import psutil
import os
import csv  # NEW: For CSV file handling

def clean_text(text):
    """Remove special characters that cause problems"""
    if not text:
        return "Unknown"
    # Replace problematic characters (convert to simple ASCII)
    text = text.encode('ascii', 'ignore').decode('ascii')
    return text if text else "Unknown"

def get_active_window():
    """Get the active window title"""
    try:
        import win32gui
        window = win32gui.GetForegroundWindow()
        window_title = win32gui.GetWindowText(window)
        return clean_text(window_title)
    except:
        return "Unknown"

def get_current_app():
    """Get the current application name"""
    try:
        import win32gui
        import win32process
        
        window = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(window)
        process = psutil.Process(pid)
        return clean_text(process.name())
    except:
        return "Unknown"

def init_csv():
    """Create CSV file with headers if it doesn't exist"""
    if not os.path.exists("activity_log.csv"):
        with open("activity_log.csv", "w", newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            # Write headers (column names)
            writer.writerow(["Timestamp", "Counter", "Application", "Window Title"])

print("CrossWatch Logger Started!")
print("Tracking your computer activity...")
print("Saving to: activity_log.csv")
print("Press CTRL + C to stop\n")

# Initialize the CSV file with headers
init_csv()

# Counter to see it's working (increases every 5 seconds)
counter = 0

while True:
    try:
        counter += 1  # Increment the counter each loop
        
        # Get current time (when this check happens)
        current_time = datetime.datetime.now()
        
        # Get app and window info from your computer
        app_name = get_current_app()
        window_title = get_active_window()
        
        # Print to screen (you see this in Command Prompt)
        print(f"{current_time} | #{counter} | App: {app_name}")
        
        # Save to CSV file (better for analysis)
        with open("activity_log.csv", "a", newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([current_time, counter, app_name, window_title[:50]])
        
        # Wait 5 seconds before checking again
        time.sleep(5)
        
    except KeyboardInterrupt:
        # This runs when you press CTRL + C to stop the program
        print("\n\nLogger stopped!")
        print(f"Saved {counter} activities to activity_log.csv")
        print("\nOpen 'activity_log.csv' in Excel to see your data!")
        break
    except Exception as e:
        # This catches ANY other error so the program doesn't crash
        print(f" Error: {e}")
        # Continue running even if there's an error (don't stop)
        time.sleep(5)