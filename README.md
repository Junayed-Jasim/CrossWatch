# CrossWatch - Activity Tracker

> **A simple tool that watches what apps you use and shows you a dashboard**

---

## 🎯 What Does This Do?

CrossWatch tracks which applications and windows you're using on your computer. It saves this information and shows it to you on a beautiful web page that updates in real-time.

**Think of it like a security camera for your computer activity.**

---

## 📦 What's Inside?

| File | What it does |
|------|---------------|
| `logger.py` | The tracker - runs in background, records your activity |
| `server.py` | The dashboard - shows your data in a web browser |
| `activity_log.csv` | Your data file (auto-created) |
| `sessions.json` | Stores your login session (auto-created) |

---

## 🚀 Quick Start (3 Steps)

### Step 1: Install Required Software

Open Command Prompt or Terminal and run:

```bash
pip install psutil pywin32 websockets
```

### Step 2: Start the Tracker
```bash
python logger.py
```
**What happens?**

- It will ask if you want to keep old data or start fresh

- Then it starts tracking your computer activity

- **Press `CTRL+C` to stop tracking**

### Step 3: Open the Dashboard (in a NEW terminal window)
```bash
python server.py
```
Then open your web browser and go to: http://localhost:8000

**Login password:** `crosswatch123`

---

## 🎮 How to Use
**The Tracker (`logger.py`)**
```text
┌─────────────────────────────────────────────────┐
│  🎯 CrossWatch Logger Started!                  │
│  =========================================      |
│  📋 Found existing activity_log.csv file!       |
│                                                 │
│  What would you like to do?                     │
│     1 - Keep existing data (add new data to it) │
│     2 - Delete old data (start completely fresh)│
│     3 - Cancel (don't run logger)               │
└─────────────────────────────────────────────────┘
```
**Pro tip:** Choose option 1 most of the time to keep your history!


### The Dashboard
Once logged in, you'll see:

| Section |	What it shows |
|-----------|------------------------------|
| Top bar	| Live connection status, Dark/Light mode toggle, Logout button |
| Statistics	| Total activities, Unique apps, Live counter, Last update time |
| Search box	| Type to filter by app name or window title |
| Table |	Your activity history (updates in real-time) |
| Export | button	Download your data as CSV file |


### Cool Things You Can Do
- 🔍 **Search** - Find specific apps or windows

- 🎨 **Dark mode** - Click the sun/moon button

- 📥 **Export** - Save your data to Excel/CSV

- 📱 **Phone view** - Access from other devices on your WiFi

- ⚡ **Live updates** - New activities appear instantly with a green flash

---

## 📱 Access From Your Phone (Same WiFi)
When you run `server.py`, it shows your network address:

```text
📍 Network URL     : http://192.168.1.100:8000/
```
#### Type that address into your phone's browser - same login password works!

---

### ❓ Common Questions

#### "The dashboard shows no data"
**Solution:** Make sure `logger.py` is running in a separate terminal window.


#### "Can't login"
**Solution:** Password is `crosswatch123` (all lowercase, no spaces)


#### "Port 8000 is already in use"
**Solution:** Change the port in `server.py` (line 31: `PORT = 8000` change to `PORT = 8080`)


#### "Module not found errors"
**Solution:** Run the install command again:

```bash
pip install psutil pywin32 websockets
```


### "How do I stop everything?"
- Stop logger: Press `CTRL + C` in the logger terminal

- Stop server: Press `CTRL + C` in the server terminal

---

### 📊 What Your Data Looks Like
The CSV file (`activity_log.csv`) saves rows like this:

```text
Timestamp                   | Counter | Application    | Window Title
2026-05-20 19:02:11.387739  | 1       | Cursor.exe     | server.py - CrossWatch
2026-05-20 19:02:16.464394  | 2       | msedge.exe     | CrossWatch Dashboard
```
You can open this file in Excel, Google Sheets, or any text editor.

---

### 🔧 Troubleshooting Quick Guide
|Problem|	Quick Fix|
|---------------|----------|
"No module named 'win32gui'" |	Run: `pip install pywin32`
"No module named 'websockets'"|	Run: `pip install websockets`
Dashboard won't load |	Make sure `server.py` is running
No data showing |	Make sure `logger.py` is running
Can't connect from phone |	Both devices on same WiFi? Check firewall
Login fails |	Password is `crosswatch123`

---

### 🎯 What Each File Does (Simple Explanation)

#### `logger.py` - The Camera
- Runs in background

- Checks what window you're using every 5 seconds

- Saves to CSV file

- Press `CTRL+C` to stop



### `server.py` - The TV Screen
Creates a website showing your data

- Updates in real-time

- Has password protection

- Run this, then open browser



#### `activity_log.csv` - The Memory Card
- Stores all your activity data

- Can open with Excel

- Delete this file to start fresh



#### `sessions.json` - The Key Ring
- Remembers your login

- Auto-created, don't touch it

---

### 💡 Pro Tips
1. **Run logger first, then server** - Always start logger before opening the dashboard

2. **Keep both running** - You need both windows open for full functionality

3. **Bookmark the dashboard** - http://localhost:8000 is easy to remember

4. **Export before closing** - If you want to save your data, use the export button

5. **Use Dark Mode** - Easier on the eyes, click the button in top-right


---


### 🚪 Stopping Everything
```text
Terminal 1 (Logger):        Terminal 2 (Server):
Press CTRL + C              Press CTRL + C
```
That's it! Both programs will save data and exit cleanly.

---

### 📞 Need Help?
If something doesn't work:

1. Check both terminals are running

2. Make sure you installed all packages

3. Try restarting both programs

4. Check the password is `crosswatch123`


---


### ✨ Features at a Glance
- ✅ Tracks active apps every 5 seconds

- ✅ Shows window titles

- ✅ Beautiful dashboard

- ✅ Real-time updates

- ✅ Search and filter

- ✅ Export to CSV

- ✅ Dark/Light mode

- ✅ Password protected

- ✅ Works on phone (same WiFi)

- ✅ Saves your login session


---


#### Made with Python 🐍

*Start tracking your computer activity in under 2 minutes!*
