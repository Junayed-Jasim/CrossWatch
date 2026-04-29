# CrossWatch Simple Logger - With Data Management Choice
# This version asks you whether to keep or delete old data
# Author: CrossWatch Project

import time
import datetime
import csv
import os

print("🎯 CrossWatch Logger Started!")
print("=" * 40)

# ============================================
# STEP 1: Check if old data exists and ask user what to do
# ============================================

def ask_user_about_data():
    """
    This function checks if there's existing data and asks the user
    whether they want to keep it or start fresh.
    
    Returns:
        'a' - Append mode (keep old data, add new data)
        'w' - Write mode (delete old data, start fresh)
    """
    
    # Check if the CSV file already exists from previous runs
    if os.path.exists("activity_log.csv"):
        
        # File exists! Ask user what they want to do
        print("\n📋 Found existing activity_log.csv file!")
        print(f"   Current file has data from your previous runs.")
        print("\nWhat would you like to do?")
        print("   1 - Keep existing data (add new data to it)")
        print("   2 - Delete old data (start completely fresh)")
        print("   3 - Cancel (don't run logger)")
        
        # Get user's choice
        choice = input("\nEnter 1, 2, or 3: ")
        
        if choice == '1':
            # User wants to KEEP old data
            print("\n✅ Keeping existing data. New activities will be added to the file.")
            return 'a'  # 'a' = append mode (add to existing)
        
        elif choice == '2':
            # User wants to DELETE old data and start fresh
            print("\n⚠️  Deleting old data and starting fresh...")
            os.remove("activity_log.csv")  # Delete the old file
            print("✅ Old data deleted. Will create new file.")
            return 'w'  # 'w' = write mode (create new file)
        
        elif choice == '3':
            # User wants to cancel
            print("\n❌ Operation cancelled. Logger will not start.")
            return 'cancel'
        
        else:
            # User typed something invalid
            print("\n⚠️  Invalid choice. Keeping existing data by default.")
            return 'a'
    
    else:
        # No existing file - this is first time running
        print("\n📋 No existing log file found. Creating new one.")
        return 'w'  # 'w' = write mode (create new file)

# ============================================
# STEP 2: Ask user what they want (or just start)
# ============================================

# Ask the user about data management
write_mode = ask_user_about_data()

# If user chose cancel, exit the program
if write_mode == 'cancel':
    print("\n🚪 Exiting logger...")
    exit()

# ============================================
# STEP 3: Create or open the CSV file based on user's choice
# ============================================

# 'w' mode = create new file with headers (deletes old data)
# 'a' mode = open existing file (keeps old data, but need to check if headers exist)

if write_mode == 'w':
    # WRITE MODE: Create brand new file with headers
    with open("activity_log.csv", "w", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Counter", "Application", "Window Title"])
        print("✅ Created NEW activity_log.csv file")
else:
    # APPEND MODE: Check if file has headers, add them if missing
    with open("activity_log.csv", "r", encoding='utf-8') as f:
        first_line = f.readline().strip()
        
    # If first line is not the header, add it
    if first_line != "Timestamp,Counter,Application,Window Title":
        # Read all existing data
        with open("activity_log.csv", "r", encoding='utf-8') as f:
            old_data = f.readlines()
        
        # Write headers first, then old data
        with open("activity_log.csv", "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Counter", "Application", "Window Title"])
            # Write back the old data (skip first line if it was wrong)
            for line in old_data:
                if line.strip() and not line.startswith("Timestamp"):
                    f.write(line)
    
    print("✅ Opening existing activity_log.csv file (keeping old data)")

print("\n" + "=" * 40)
print("Tracking your computer activity...")
print("Press CTRL + C to stop")
print("=" * 40 + "\n")

# ============================================
# STEP 4: Start tracking (the main loop)
# ============================================

counter = 0  # This counts how many activities we've tracked in THIS run

try:
    while True:
        counter += 1  # Increase counter by 1 each time
        
        # Get current time (when this check happens)
        now = datetime.datetime.now()
        
        # Default values (in case libraries aren't installed)
        app_name = "TestApp"
        window_title = f"Activity #{counter}"
        
        # Try to get real app information (Windows only)
        try:
            import win32gui  # Library to get window information
            import win32process  # Library to get process information
            import psutil  # Library to get process details
            
            # Get the window that is currently active (the one you're using)
            window = win32gui.GetForegroundWindow()
            
            # Get the title of that window (like "Google Chrome - YouTube")
            window_title = win32gui.GetWindowText(window)
            
            # Get the process ID of the window
            _, pid = win32process.GetWindowThreadProcessId(window)
            
            # Get the process (app) name from the process ID
            process = psutil.Process(pid)
            app_name = process.name()
            
        except:
            # If libraries are not installed, use demo data
            # This prevents the program from crashing
            app_name = "Demo Mode (install pywin32 and psutil)"
            window_title = f"Check #{counter}"
        
        # Print to screen so you can see what's happening
        print(f"{now} | #{counter} | {app_name}")
        
        # Save to CSV file
        # 'a' mode = append (add to end of file, don't overwrite)
        with open("activity_log.csv", "a", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Write one row with: timestamp, counter, app name, window title (limited to 50 chars)
            writer.writerow([now, counter, app_name, window_title[:50]])
        
        # Wait 5 seconds before checking again
        # This prevents the program from using too much CPU
        time.sleep(5)
        
except KeyboardInterrupt:
    # This runs when you press CTRL + C to stop the program
    print(f"\n\n{'=' * 40}")
    print("✅ Logger stopped!")
    print(f"✅ Saved {counter} NEW activities to activity_log.csv")
    print(f"\n📊 Total activities in file: Check the file or open the dashboard")
    print(f"📊 Open http://localhost:8000 to see your data!")
    print(f"{'=' * 40}")