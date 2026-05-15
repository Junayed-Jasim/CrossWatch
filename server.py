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
#
# [REDESIGN v2] What changed from the original template:
#   - TYPOGRAPHY: Replaced generic 'Segoe UI' with Google Fonts pairing:
#     'Plus Jakarta Sans' (clean, professional UI font) +
#     'JetBrains Mono' (purposeful monospace for data/timestamps).
#     Original fonts had no personality for a monitoring tool.
#
#   - DARK MODE (default): Richer depth with layered surface colors
#     (#080c14 background → #0d1320 panels → #111926 raised elements).
#     Original dark mode used flat, low-contrast navy blocks.
#
#   - LIGHT MODE (v5 — warm cream): Replaced cold blue-slate tones with
#     warm linen/cream palette (#eae7e0 body, #f5f3ee panels, #faf9f5 raised).
#     Text uses warm charcoal (#2a2520) instead of cold slate. Borders are
#     warm tan (#d2cbc0). Box-shadows add depth. Topbar stays dark navy.
#
#   - ACCENT SYSTEM: Three-color semantic palette:
#     Cyan (#00c2ff) for primary info/data,
#     Mint green (#00e0a0) for positive actions (export, live dot),
#     Amber (#ffb830) for time/temporal data.
#     Original used a single flat #3498db for everything.
#
#   - TOPBAR: Replaced plain div header with a flex layout that includes
#     an animated pulse-ring icon and a custom-styled live network pill.
#     Original header was a simple colored bar with no visual hierarchy.
#
#   - STATS ROW: Grid layout with icon boxes per metric, colored by type.
#     Original used equal flex cards that all looked identical.
#
#   - SEARCH BAR: Added inline SVG magnifier icon inside the input.
#     Original had a plain placeholder emoji.
#
#   - AUTO-REFRESH TOGGLE: Replaced plain native checkbox with a
#     CSS-only animated toggle switch. Same HTML <input type="checkbox">
#     underneath — no JS change, purely cosmetic upgrade.
#
#   - TABLE: Sticky-header scrollable container. Rows have a left-border
#     accent that illuminates on hover. Counter column uses monospace.
#     Original had basic padding and a generic dark header.
#
#   - ACCESS DENIED PAGE: Redesigned to match the new dark theme with
#     proper spacing, icon, and brand consistency.
#
#   - ANIMATIONS: Added CSS keyframe animations for:
#     (a) pulse-ring on the brand icon (live indicator),
#     (b) blink on the live-status dot,
#     (c) staggered row-in fade for table rows on data load.
#     Original had no entrance animations.
#
#   - JS IMPROVEMENTS (no logic changes, same API):
#     * Centralized mutable values into a `state` object instead of
#       scattered let globals.
#     * Split showError() and showEmptyState() into dedicated helpers.
#     * CSV export filename now includes timestamp to prevent overwrite.
#     * Used 'input' event instead of 'keyup' for search (catches paste).
#     * Theme key changed to 'cwTheme' to avoid conflicts with other apps.
#
#   All original comments are preserved. New change notes are marked
#   with [CHANGE] inline.
# ============================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">

    <!-- [CHANGE] Updated title to match new brand wordmark style -->
    <title>CrossWatch — Network Viewer</title>

    <!--
        [CHANGE] Added Google Fonts:
        - 'Plus Jakarta Sans': Clean, geometric sans-serif with great weight range.
          Far more professional than Segoe UI for a monitoring dashboard.
        - 'JetBrains Mono': Purpose-built for code/data display. Used on all
          timestamps, IP addresses, and monospace data fields.
        Both load with font-display:swap for no layout shift.
    -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">

    <style>
        /* ============================================================
           [CHANGE] DESIGN TOKEN SYSTEM
           All visual values are CSS custom properties. Swapping a theme
           means only the :root block changes — no scattered overrides.
           Original code had a mix of hardcoded hex values and variables.
        ============================================================ */
        :root {
            /* Dark theme (default) — deep navy with layered surfaces */
            --bg:               #080c14;   /* [CHANGE] was: gradient from #667eea to #764ba2 */
            --surface:          #0d1320;   /* [CHANGE] was: --container-bg: white */
            --surface-raised:   #111926;   /* [CHANGE] new layer — for toolbar, stats bg */
            --surface-hover:    #162030;   /* [CHANGE] new — table row hover */
            --border:           #1e2d42;   /* [CHANGE] was: --border-color: #ddd */
            --border-subtle:    #131f30;   /* [CHANGE] new — very faint separator */

            /* Semantic accent colors — each carries a specific meaning */
            --accent:           #00c2ff;   /* [CHANGE] was: single #3498db for everything */
            --accent-dim:       rgba(0, 194, 255, 0.10);
            --accent-glow:      rgba(0, 194, 255, 0.22);
            --green:            #00e0a0;   /* [CHANGE] new — for positive/live actions */
            --green-dim:        rgba(0, 224, 160, 0.10);
            --amber:            #ffb830;   /* [CHANGE] new — for time/temporal data */
            --amber-dim:        rgba(255, 184, 48, 0.10);
            --danger:           #ff5270;   /* [CHANGE] new — for error states */

            /* Typography */
            --text-primary:     #dce8f5;   /* [CHANGE] was: --text-color: #eee (too harsh) */
            --text-secondary:   #6e8caa;
            --text-muted:       #334d68;

            /* [CHANGE] Explicit font stack — original used implicit system fallbacks */
            --font-ui:          'Plus Jakarta Sans', sans-serif;
            --font-mono:        'JetBrains Mono', monospace;

            /* Spacing tokens */
            --radius-sm:        6px;
            --radius-md:        10px;
            --radius-lg:        16px;
            --transition:       0.2s ease;
        }

        /*
            [CHANGE v5] LIGHT MODE — Warm cream/stone palette.

            Previous light mode (v4) used cold blue-slate tones (#e8edf5, #f2f5fa)
            which looked washed-out and too bright. This revision shifts to warm
            cream/linen tones inspired by Notion, Linear, and Apple HIG light modes.

            Core changes from v4:
            - Replaced cold blue-white surfaces with warm linen/cream tones
            - Background: warm stone (#eae7e0) instead of cold blue (#e8edf5)
            - Panels: soft cream (#f5f3ee) instead of icy white (#f2f5fa)
            - Text: warm charcoal (#2a2520) instead of cold slate (#1c2b3a)
            - Borders: warm tan (#d2cbc0) instead of cold steel (#c8d3e2)
            - Added box-shadows for depth instead of relying solely on color layers
            - Topbar stays dark navy — anchors the layout

            The warm undertone eliminates the "blinding white screen" feel and
            makes extended reading sessions much more comfortable.
        */
        body.light-mode {
            /* Surfaces — warm cream layers, never pure white */
            --bg:               #eae7e0;   /* Page bg: warm linen stone */
            --surface:          #f5f3ee;   /* Panel/card: soft warm cream */
            --surface-raised:   #faf9f5;   /* Elevated: toolbar, th — warmest white */
            --surface-hover:    #edeae4;   /* Row hover — warm taupe tint */

            /* Borders — warm tan, visible but soft */
            --border:           #d2cbc0;
            --border-subtle:    #e2ddd5;

            /* Accent: deep indigo-blue — strong contrast on warm surfaces */
            --accent:           #2563eb;
            --accent-dim:       rgba(37, 99, 235, 0.08);
            --accent-glow:      rgba(37, 99, 235, 0.16);

            /* Semantic green — rich emerald for warm backgrounds */
            --green:            #0d9468;
            --green-dim:        rgba(13, 148, 104, 0.08);

            /* Semantic amber — warm golden on warm bg */
            --amber:            #b86e00;
            --amber-dim:        rgba(184, 110, 0, 0.08);

            /* Danger */
            --danger:           #dc2626;

            /* Typography — warm charcoal, never cold blue-black */
            --text-primary:     #2a2520;   /* Rich warm charcoal */
            --text-secondary:   #5c554d;   /* Warm mid-brown */
            --text-muted:       #9a9186;   /* Warm stone for subtle text */
        }

        /* ── Topbar: always dark navy in light mode ─────────────────────────
           The topbar stays dark regardless of theme.
           Professional tools (Grafana, Datadog, Linear) keep a dark header
           even in light mode — it anchors the brand and provides a strong
           visual top edge to the layout.
        ─────────────────────────────────────────────────────────────────── */
        body.light-mode .topbar {
            background: #1a1a2e;
            border-color: #2a2a44;
        }

        /* Network pill on dark topbar */
        body.light-mode .topbar .network-pill {
            background: rgba(0, 194, 255, 0.10);
            border-color: rgba(0, 194, 255, 0.25);
            color: #5dcfef;
        }

        /* Theme button: readable on dark topbar */
        body.light-mode .btn-theme {
            background: rgba(255, 255, 255, 0.07);
            border-color: rgba(255, 255, 255, 0.14);
            color: #90aec8;
        }

        body.light-mode .btn-theme:hover {
            background: rgba(0, 194, 255, 0.13);
            border-color: rgba(0, 194, 255, 0.30);
            color: #5dcfef;
        }

        /* Stats row: warm shadow for depth on cream surfaces */
        body.light-mode .stats-row {
            box-shadow: 0 1px 4px rgba(42, 37, 32, 0.07);
        }

        /* Stat icon borders: warmer tints */
        body.light-mode .stat-icon.accent {
            background: var(--accent-dim);
            border-color: rgba(37, 99, 235, 0.18);
        }
        body.light-mode .stat-icon.green {
            background: var(--green-dim);
            border-color: rgba(13, 148, 104, 0.18);
        }
        body.light-mode .stat-icon.amber {
            background: var(--amber-dim);
            border-color: rgba(184, 110, 0, 0.18);
        }

        /* Table header: warm stone tone, not cold blue */
        body.light-mode th {
            background: #ebe8e1;
            color: #7a7168;
        }

        /* Table wrapper: warm shadow for panel depth */
        body.light-mode .table-wrapper {
            box-shadow: 0 1px 4px rgba(42, 37, 32, 0.06);
        }

        /* App badge: adjusted for warm backgrounds */
        body.light-mode .app-badge {
            background: rgba(37, 99, 235, 0.07);
            color: #2563eb;
            border-color: rgba(37, 99, 235, 0.16);
        }

        /* Search input: cream white with warm border */
        body.light-mode .search-input {
            background: #fdfcfa;
            border-color: #cfc8bc;
        }

        body.light-mode .search-input:focus {
            border-color: var(--accent);
            box-shadow: 0 0 0 3px var(--accent-glow);
        }

        /* Export button: rich emerald on warm surfaces */
        body.light-mode .btn-export {
            background: #0d9468;
            color: #ffffff;
        }

        body.light-mode .btn-export:hover {
            background: #0a7d58;
            box-shadow: 0 4px 14px rgba(13, 148, 104, 0.20);
        }

        /* Refresh toggle: warm raised surface */
        body.light-mode .refresh-toggle {
            background: #faf9f5;
            border-color: #d2cbc0;
        }

        /* Footer: warm separator and slightly darker cream */
        body.light-mode .footer {
            background: #f0ede7;
            border-top: 1px solid var(--border);
        }

        /* Status bar: warm raised */
        body.light-mode .status-bar {
            background: #f0ede7;
        }

        /* ============================================================
           BASE RESET & GLOBAL STYLES
           Original had the same reset — kept identical.
        ============================================================ */
        *, *::before, *::after {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            /* [CHANGE] Font changed from 'Segoe UI' to the Plus Jakarta Sans stack */
            font-family: var(--font-ui);
            background-color: var(--bg);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 24px 20px;
            transition: background-color var(--transition), color var(--transition);

            /*
                [CHANGE] Subtle radial glow at the top of the page.
                Creates depth without a garish gradient background.
                Original had a full-page linear-gradient which competed
                with the content and looked dated.
            */
            background-image: radial-gradient(
                ellipse 70% 35% at 50% -5%,
                rgba(0, 194, 255, 0.06) 0%,
                transparent 70%
            );
        }

        /* [CHANGE v4] Remove the cyan radial glow in light mode — on a light
           slate background it creates an odd blue patch. Light mode gets a
           clean, flat background instead; depth comes from surface layers. */
        body.light-mode {
            background-image: none;
        }

        /* ============================================================
           [CHANGE] APP-SHELL LAYOUT
           Single centered column. Sections stack with 2px gap that shows
           the background through — acts as a visual separator without
           needing explicit borders between every panel.
           Original used a single .container div with overflow:hidden.
        ============================================================ */
        .app-shell {
            max-width: 1440px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 2px;
        }

        /* ============================================================
           [CHANGE] TOPBAR — Complete redesign
           Original was a flat colored rectangle with an <h1> and a badge.
           New version has: brand icon with pulse animation, wordmark with
           accent-colored product name, monospace subtitle, network pill
           with live dot, and a cleaner theme toggle button.
        ============================================================ */
        .topbar {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg) var(--radius-lg) 0 0;
            padding: 18px 28px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            flex-wrap: wrap;
        }

        .topbar__brand {
            display: flex;
            align-items: center;
            gap: 14px;
        }

        /*
            [CHANGE] Brand icon square — new element entirely.
            The ::after creates the pulse ring animation that suggests
            the dashboard is "live". Pure CSS, no JS required.
        */
        .brand-icon {
            width: 42px;
            height: 42px;
            border-radius: var(--radius-sm);
            background: var(--accent-dim);
            border: 1px solid rgba(0, 194, 255, 0.3);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            position: relative;
            flex-shrink: 0;
        }

        .brand-icon::after {
            content: '';
            position: absolute;
            inset: -5px;
            border-radius: calc(var(--radius-sm) + 5px);
            border: 1px solid var(--accent);
            opacity: 0;
            animation: pulse-ring 2.8s ease-out infinite;
        }

        @keyframes pulse-ring {
            0%   { opacity: 0.45; transform: scale(1); }
            100% { opacity: 0;    transform: scale(1.4); }
        }

        .brand-text h1 {
            font-size: 19px;
            font-weight: 800;
            letter-spacing: -0.4px;
            color: #ffffff;
            line-height: 1.2;
        }

        /* [CHANGE] Accent on just the product name — original had no color variation in heading */
        .brand-text h1 span { color: var(--accent); }

        .brand-text p {
            font-size: 11px;
            color: #6e8caa;
            font-family: var(--font-mono);
            letter-spacing: 0.02em;
            margin-top: 3px;
        }

        .topbar__controls {
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }

        /*
            [CHANGE] Network pill — replaced the original .network-badge.
            Added a blinking live dot to reinforce that data is real-time.
            Original badge had no liveness indicator.
        */
        .network-pill {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 7px 14px;
            background: var(--accent-dim);
            border: 1px solid rgba(0, 194, 255, 0.25);
            border-radius: 999px;
            font-family: var(--font-mono);
            font-size: 12px;
            color: var(--accent);
            white-space: nowrap;
        }

        /* [CHANGE] Animated live indicator dot — blinks on a slow rhythm */
        .live-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: var(--green);
            box-shadow: 0 0 5px var(--green);
            animation: blink 1.6s ease-in-out infinite;
            flex-shrink: 0;
        }

        @keyframes blink {
            0%, 100% { opacity: 1; }
            50%       { opacity: 0.25; }
        }

        /*
            [CHANGE] Theme toggle button — replaced .dark-mode-btn.
            Original used rgba(255,255,255,0.2) on a dark header which
            only worked on dark backgrounds. New version is fully theme-aware
            using surface variables so it looks correct in both modes.
        */
        .btn-theme {
            padding: 7px 15px;
            background: var(--surface-raised);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            color: var(--text-secondary);
            font-family: var(--font-ui);
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: border-color var(--transition), color var(--transition), background var(--transition);
            white-space: nowrap;
        }

        .btn-theme:hover {
            border-color: var(--accent);
            color: var(--accent);
            background: var(--accent-dim);
        }

        /* ============================================================
           [CHANGE] STATS ROW — Grid layout with semantic icon boxes.
           Original used flex cards that were identical in appearance.
           New version: each stat has a colored icon box, and the row
           uses a 3-column grid with 1px gaps on a subtle background
           to create built-in dividers without explicit border rules.
        ============================================================ */
        .stats-row {
            background: var(--border-subtle); /* Shows through the 1px gap = divider effect */
            border-left: 1px solid var(--border);
            border-right: 1px solid var(--border);
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1px;
        }

        .stat-item {
            background: var(--surface);
            padding: 16px 22px;
            display: flex;
            align-items: center;
            gap: 14px;
            transition: background var(--transition);
        }

        .stat-item:hover { background: var(--surface-raised); }

        /* [CHANGE] Icon box per stat — original had none, just text */
        .stat-icon {
            width: 38px;
            height: 38px;
            border-radius: var(--radius-sm);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            flex-shrink: 0;
        }

        /* [CHANGE] Three distinct semantic colors per stat type */
        .stat-icon.accent { background: var(--accent-dim); border: 1px solid rgba(0,194,255,0.2); }
        .stat-icon.green  { background: var(--green-dim);  border: 1px solid rgba(0,224,160,0.2); }
        .stat-icon.amber  { background: var(--amber-dim);  border: 1px solid rgba(255,184,48,0.2); }

        .stat-label {
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.09em;
            color: var(--text-muted);
            margin-bottom: 5px;
        }

        /* [CHANGE] Tabular numbers — prevents layout shift when count updates */
        .stat-value {
            font-size: 26px;
            font-weight: 800;
            color: var(--text-primary);
            line-height: 1;
            font-variant-numeric: tabular-nums;
        }

        /* [CHANGE] Smaller monospace variant for the timestamp stat */
        .stat-value.mono {
            font-size: 13px;
            font-family: var(--font-mono);
            font-weight: 500;
        }

        /* ============================================================
           [CHANGE] TOOLBAR — Replaced .controls-section.
           Same functionality: search, export, auto-refresh.
           Key change: search input now has an inline SVG icon instead
           of an emoji in the placeholder string.
        ============================================================ */
        .toolbar {
            background: var(--surface);
            border-left: 1px solid var(--border);
            border-right: 1px solid var(--border);
            padding: 13px 28px;
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }

        /* [CHANGE] Position-relative wrapper allows absolute icon placement */
        .search-wrapper {
            flex: 1;
            min-width: 200px;
            position: relative;
        }

        .search-wrapper svg {
            position: absolute;
            left: 11px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-muted);
            pointer-events: none;
            width: 14px;
            height: 14px;
        }

        /*
            [CHANGE] Search input — replaced .search-box.
            Added focus ring using box-shadow instead of outline for
            a softer, more polished glow effect on focus.
        */
        .search-input {
            width: 100%;
            padding: 9px 14px 9px 34px;
            background: var(--surface-raised);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            color: var(--text-primary);
            font-family: var(--font-ui);
            font-size: 13px;
            transition: border-color var(--transition), box-shadow var(--transition);
        }

        .search-input::placeholder { color: var(--text-muted); }

        .search-input:focus {
            outline: none;
            border-color: var(--accent);
            box-shadow: 0 0 0 3px var(--accent-glow);
        }

        /*
            [CHANGE] Export button — replaced .export-btn.
            Added lift animation on hover (translateY + box-shadow).
            Color changed to green semantic color for "positive action".
            Original used a flat #27ae60 with only a background color change.
        */
        .btn-export {
            padding: 9px 18px;
            background: var(--green);
            color: #041a10;
            font-family: var(--font-ui);
            font-size: 12px;
            font-weight: 700;
            border: none;
            border-radius: var(--radius-sm);
            cursor: pointer;
            letter-spacing: 0.02em;
            transition: opacity var(--transition), transform var(--transition), box-shadow var(--transition);
            white-space: nowrap;
        }

        .btn-export:hover {
            opacity: 0.88;
            transform: translateY(-1px);
            box-shadow: 0 4px 14px rgba(0, 224, 160, 0.28);
        }

        .btn-export:active { transform: translateY(0); }

        /*
            [CHANGE] Auto-refresh toggle — complete visual overhaul.
            Same underlying HTML (<input type="checkbox" id="autoRefreshToggle">).
            Wrapped in a <label class="refresh-toggle"> for click targeting.
            The native checkbox is hidden via appearance:none and replaced
            with a CSS-animated pill track + thumb.
            Original was a plain unstyled checkbox in a div.
        */
        .refresh-toggle {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 7px 13px;
            background: var(--surface-raised);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            cursor: pointer;
            user-select: none;
            font-size: 12px;
            color: var(--text-secondary);
            font-weight: 600;
            white-space: nowrap;
            transition: border-color var(--transition);
        }

        .refresh-toggle:hover { border-color: var(--accent); }

        /* Hide the native checkbox — visual is pure CSS below */
        .refresh-toggle input[type="checkbox"] {
            appearance: none;
            width: 30px;
            height: 16px;
            background: var(--border);
            border-radius: 999px;
            position: relative;
            cursor: pointer;
            transition: background var(--transition);
            flex-shrink: 0;
        }

        /* The sliding thumb */
        .refresh-toggle input[type="checkbox"]::after {
            content: '';
            position: absolute;
            width: 12px;
            height: 12px;
            background: var(--text-secondary);
            border-radius: 50%;
            top: 2px;
            left: 2px;
            transition: transform var(--transition), background var(--transition);
        }

        .refresh-toggle input[type="checkbox"]:checked {
            background: var(--green);
        }

        .refresh-toggle input[type="checkbox"]:checked::after {
            background: #041a10;
            transform: translateX(14px);
        }

        /* ============================================================
           [CHANGE] STATUS BAR — Replaced .refresh-info.
           Original used a yellow/amber warning-style background which
           felt like an alert even when everything was fine.
           New version is a subtle monospace strip — unobtrusive.
        ============================================================ */
        .status-bar {
            background: var(--surface-raised);
            border-left: 1px solid var(--border);
            border-right: 1px solid var(--border);
            border-top: 1px solid var(--border-subtle);
            padding: 7px 28px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
            font-family: var(--font-mono);
            font-size: 10.5px;
            color: var(--text-muted);
        }

        /* [CHANGE] Accent highlight for dynamic counts in status bar */
        .status-bar .hl { color: var(--accent); font-weight: 600; }

        /* ============================================================
           [CHANGE] TABLE WRAPPER — Replaced .table-container.
           Key changes:
           - Custom scrollbar styled to match the theme
           - No extra padding around the table (table fills edge-to-edge)
           - max-height increased slightly to 540px
        ============================================================ */
        .table-wrapper {
            background: var(--surface);
            border: 1px solid var(--border);
            border-top: none;
            overflow-x: auto;
            overflow-y: auto;
            max-height: 540px;
            scrollbar-width: thin;
            scrollbar-color: var(--border) transparent;
        }

        .table-wrapper::-webkit-scrollbar { width: 5px; height: 5px; }
        .table-wrapper::-webkit-scrollbar-track { background: transparent; }
        .table-wrapper::-webkit-scrollbar-thumb {
            background: var(--border);
            border-radius: 999px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            min-width: 520px;
        }

        /* [CHANGE] Sticky header — original had position:sticky on th only,
           which doesn't work in all browsers. Moving it to thead tr is more reliable. */
        thead tr {
            position: sticky;
            top: 0;
            z-index: 10;
        }

        th {
            background: var(--surface-raised);
            border-bottom: 1px solid var(--border);
            padding: 10px 16px;
            text-align: left;
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--text-muted);
            white-space: nowrap;
        }

        /* [CHANGE] Left accent border on first column header — adds entry point for the eye */
        th:first-child {
            border-left: 3px solid var(--accent);
            padding-left: 13px;
        }

        td {
            padding: 10px 16px;
            border-bottom: 1px solid var(--border-subtle);
            font-size: 12.5px;
            color: var(--text-secondary);
            transition: background var(--transition);
        }

        /* [CHANGE] Row number and timestamp in monospace — data columns feel deliberate */
        td:first-child {
            font-family: var(--font-mono);
            font-size: 11px;
            color: var(--text-muted);
            border-left: 3px solid transparent;
            padding-left: 13px;
            transition: color var(--transition), border-color var(--transition);
        }

        td:nth-child(2) {
            font-family: var(--font-mono);
            font-size: 11.5px;
            white-space: nowrap;
        }

        /* [CHANGE] Row hover: entire row highlights AND left border glows accent */
        tr:hover td { background: var(--surface-hover); }
        tr:hover td:first-child {
            border-left-color: var(--accent);
            color: var(--accent);
        }

        /*
            [CHANGE] App badge — same concept as original .app-badge,
            redesigned to use the accent color system instead of flat #3498db.
            Added monospace font and a subtle border.
        */
        .app-badge {
            display: inline-flex;
            align-items: center;
            background: var(--accent-dim);
            color: var(--accent);
            border: 1px solid rgba(0, 194, 255, 0.18);
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-family: var(--font-mono);
            font-weight: 600;
            letter-spacing: 0.03em;
            white-space: nowrap;
        }

        /* ============================================================
           [CHANGE] EMPTY STATE — Replaced .no-results.
           Original was a single centered <div> with just text.
           New version has an icon, headline, and subtext slot.
           Used for both "no data" and "no search results" states.
        ============================================================ */
        .empty-state {
            padding: 64px 20px;
            text-align: center;
        }

        .empty-state .empty-icon {
            font-size: 36px;
            margin-bottom: 14px;
            opacity: 0.45;
        }

        .empty-state p {
            font-size: 13.5px;
            color: var(--text-secondary);
            margin-bottom: 6px;
        }

        .empty-state small {
            font-family: var(--font-mono);
            font-size: 11px;
            color: var(--text-muted);
        }

        /* ============================================================
           [CHANGE] FOOTER — Replaced original .footer.
           Tightened into a two-sided flex row with monospace text.
           Original was a centered single line.
        ============================================================ */
        .footer {
            background: var(--surface);
            border: 1px solid var(--border);
            border-top: none;
            border-radius: 0 0 var(--radius-lg) var(--radius-lg);
            padding: 11px 28px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 8px;
            font-size: 10.5px;
            color: var(--text-muted);
            font-family: var(--font-mono);
        }

        .footer .footer-mark {
            font-weight: 600;
            letter-spacing: 0.07em;
            text-transform: uppercase;
            font-size: 9.5px;
        }

        /* ============================================================
           RESPONSIVE — Collapse stats to single column on mobile.
           Original used 768px breakpoint — kept the same threshold.
        ============================================================ */
        @media (max-width: 768px) {
            body { padding: 10px; }

            .topbar { padding: 14px 16px; }
            .brand-text h1 { font-size: 16px; }

            /* [CHANGE] Stats grid collapses to 1 column on mobile */
            .stats-row { grid-template-columns: 1fr; }
            .stat-item { padding: 13px 16px; }

            .toolbar { padding: 11px 16px; }
            .status-bar { padding: 6px 16px; }

            th, td { padding: 9px 12px; }

            .footer {
                flex-direction: column;
                text-align: center;
                padding: 11px 16px;
            }
        }

        /* ============================================================
           [CHANGE v3 FIX] TABLE ROW ENTRANCE ANIMATION
           The @keyframes definition is kept, but the global rule
           `tbody tr { animation: ... }` has been REMOVED.
           
           Root cause of the bug: setting `tbody tr { animation: row-in }` 
           in CSS means EVERY time renderTable() replaces innerHTML — which 
           happens on every search keystroke and every 5s auto-refresh — ALL 
           rows re-animate from scratch. This made the entire list flash and 
           "stack in" repeatedly, which was jarring and looked broken.
           
           Fix: the animation is now applied ONLY in JS, and ONLY on the
           very first data load (state.firstLoad flag). Subsequent renders
           from search filtering or auto-refresh skip the animation entirely,
           so existing rows stay put and the list updates silently.
        ============================================================ */
        @keyframes row-in {
            from { opacity: 0; transform: translateY(5px); }
            to   { opacity: 1; transform: translateY(0); }
        }

        /* [CHANGE v3 FIX] Removed: tbody tr { animation: row-in 0.2s ease both; }
           Animation is now applied selectively via JS only on first load. */
        tbody tr.animate-in { animation: row-in 0.2s ease both; }
    </style>
</head>

<body>

    <!--
        [CHANGE] Top-level wrapper renamed from .container to .app-shell.
        The visual container is now implied by stacked bordered sections
        rather than a single rounded card with overflow:hidden.
        This allows more flexibility in how sections are styled independently.
    -->
    <div class="app-shell">

        <!-- ============================================================
             TOPBAR
             [CHANGE] Completely redesigned from the original <div class="header">.
             Now contains: brand icon (with pulse animation), wordmark,
             network pill (with live dot), and theme toggle.
        ============================================================ -->
        <header class="topbar">
            <div class="topbar__brand">
                <!-- [CHANGE] Brand icon — new element, adds visual anchor to the left -->
                <div class="brand-icon">📡</div>
                <div class="brand-text">
                    <!-- [CHANGE] <span> wraps "Watch" for accent color split on the wordmark -->
                    <h1>Cross<span>Watch</span></h1>
                    <p>Network Viewer &middot; Real-time activity tracking &middot; Project 4</p>
                </div>
            </div>

            <div class="topbar__controls">
                <!--
                    [CHANGE] Replaced .network-badge with .network-pill.
                    Added .live-dot for the animated blink effect.
                    Content populated by getNetworkInfo() — same JS logic.
                -->
                <div class="network-pill" id="networkBadge">
                    <span class="live-dot"></span>
                    <span>Connecting&hellip;</span>
                </div>

                <!--
                    [CHANGE] Replaced .dark-mode-btn (id="darkModeBtn") with .btn-theme.
                    ID kept identical so existing JS works without changes.
                    Default label changed to "Light Mode" since dark is now default.
                -->
                <button class="btn-theme" id="darkModeBtn">☀️ Light Mode</button>
            </div>
        </header>

        <!-- ============================================================
             STATS ROW
             [CHANGE] Replaced <div class="stats"> containing .stat-card elements.
             Same three metrics: Total Activities, Unique Apps, Last Update.
             Now uses a CSS grid layout with colored icon boxes per metric.
        ============================================================ -->
        <section class="stats-row" aria-label="Summary statistics">
            <div class="stat-item">
                <div class="stat-icon accent">📊</div>
                <div>
                    <div class="stat-label">Total Activities</div>
                    <!-- [CHANGE] ID preserved: totalCount — JS targets same ID -->
                    <div class="stat-value" id="totalCount">—</div>
                </div>
            </div>
            <div class="stat-item">
                <div class="stat-icon green"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color:var(--green)"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg></div>
                <div>
                    <div class="stat-label">Unique Apps</div>
                    <!-- [CHANGE] ID preserved: uniqueApps -->
                    <div class="stat-value" id="uniqueApps">—</div>
                </div>
            </div>
            <div class="stat-item">
                <div class="stat-icon amber">🕐</div>
                <div>
                    <div class="stat-label">Last Update</div>
                    <!--
                        [CHANGE] ID preserved: lastUpdate
                        Added class="mono" for monospace rendering of time string.
                        Original used inline style="font-size:14px" — moved to CSS class.
                    -->
                    <div class="stat-value mono" id="lastUpdate">—</div>
                </div>
            </div>
        </section>

        <!-- ============================================================
             TOOLBAR
             [CHANGE] Replaced <div class="controls-section">.
             Functionality identical: search, export, auto-refresh toggle.
             Search now has an inline SVG icon.
             Export button class changed from .export-btn to .btn-export.
             Auto-refresh wrapped in a <label> for full click targeting.
        ============================================================ -->
        <div class="toolbar">
            <div class="search-wrapper">
                <!-- [CHANGE] Inline SVG magnifier — more precise than emoji in placeholder -->
                <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.7">
                    <circle cx="6.5" cy="6.5" r="4.5"/>
                    <line x1="10.5" y1="10.5" x2="14" y2="14"/>
                </svg>
                <!--
                    [CHANGE] Class renamed search-input, placeholder updated.
                    ID preserved: searchInput — no JS changes needed.
                    Event changed from 'keyup' to 'input' in JS (catches paste/voice).
                -->
                <input
                    type="text"
                    id="searchInput"
                    class="search-input"
                    placeholder="Filter by app name or window title&hellip;"
                    autocomplete="off"
                    spellcheck="false"
                >
            </div>

            <!-- [CHANGE] Class renamed btn-export. ID preserved: exportBtn. -->
            <button class="btn-export" id="exportBtn">↓ Export CSV</button>

            <!--
                [CHANGE] Wrapped in <label class="refresh-toggle"> so clicking
                the label text also toggles the checkbox — better UX.
                ID preserved: autoRefreshToggle — JS unchanged.
            -->
            <label class="refresh-toggle">
                <input type="checkbox" id="autoRefreshToggle" checked>
                Auto-refresh (5s)
            </label>
        </div>

        <!-- ============================================================
             STATUS BAR
             [CHANGE] Replaced <div class="refresh-info">.
             Original had a yellow warning-style background.
             Now a subtle monospace strip — purely informational.
             IDs preserved so JS targets are unchanged.
        ============================================================ -->
        <div class="status-bar">
            <span>source: activity_log.csv</span>
            <span id="filterStatus">Loading&hellip;</span>
        </div>

        <!-- ============================================================
             DATA TABLE
             [CHANGE] Replaced <div class="table-container"> with .table-wrapper.
             The table itself is identical in structure — same columns.
             Styling changes only: custom scrollbar, sticky header fix,
             left-border row hover accent, monospace data columns.
        ============================================================ -->
        <div class="table-wrapper">
            <div id="logContent">
                <div class="empty-state">
                    <div class="empty-icon">📭</div>
                    <p>Waiting for data from server&hellip;</p>
                    <small>Make sure logger.py is running</small>
                </div>
            </div>
        </div>

        <!-- ============================================================
             FOOTER
             [CHANGE] Replaced original centered single-line footer.
             Now two-sided: brand mark on left, feature list on right.
        ============================================================ -->
        <footer class="footer">
            <span class="footer-mark">CrossWatch &mdash; Network Viewer</span>
            <span>Filter &middot; Export CSV &middot; Dark / Light Mode &middot; LAN Access</span>
        </footer>

    </div><!-- /.app-shell -->


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
        //
        // [CHANGE] Consolidated into a single `state` object.
        // Rationale: scattered `let` globals are easy to lose track of
        // in a larger file. A state object makes all mutable app state
        // visible in one place and easier to debug in devtools.
        // Original had: let allLogs, let autoRefreshEnabled, let refreshInterval.
        // ============================================

        // [CHANGE] Single state object instead of three separate globals
        // [CHANGE v3 FIX] Added firstLoad flag — used by renderTable() to decide
        // whether to run the entrance animation. Set to false after the first
        // successful render so auto-refresh and search never re-animate rows.
        let state = {
            allLogs:           [],    // Full dataset from the last server response
            autoRefresh:       true,  // Whether the polling interval should fire
            refreshIntervalId: null,  // setInterval handle — stored so we can cancel it
            firstLoad:         true   // True only until the first table render completes
        };

        // ============================================
        // FUNCTION: Get Network IP from Server
        // ============================================

        function getNetworkInfo() {
            fetch(networkUrl)
                .then(response => response.json())
                .then(data => {
                    const badge = document.getElementById('networkBadge');
                    if (data.ip) {
                        // [CHANGE] Updated HTML structure to use .live-dot + plain span
                        // instead of the old .ip span. Same data, new markup.
                        badge.innerHTML = `
                            <span class="live-dot"></span>
                            <span>${data.ip}:${data.port}</span>
                        `;
                    } else {
                        badge.innerHTML = `<span class="live-dot"></span><span>port ${data.port}</span>`;
                    }
                })
                .catch(error => {
                    console.error("Error getting network info:", error);
                    const badge = document.getElementById('networkBadge');
                    // [CHANGE] Fallback also uses new markup structure
                    badge.innerHTML = `<span class="live-dot"></span><span>port 8000</span>`;
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
                        // [CHANGE] Delegated to showError() helper instead of inline innerHTML
                        showError(data.error);
                        return;
                    }

                    if (!data.logs || data.logs.length === 0) {
                        // [CHANGE] Delegated to showEmptyState() helper
                        showEmptyState('No activity yet.', 'Run python logger.py to start recording.');
                        updateStats(0, 0);
                        return;
                    }

                    // [CHANGE] Stored in state.allLogs instead of global allLogs
                    state.allLogs = data.logs;

                    // [CHANGE] Delegated to updateStats() helper
                    updateStats(data.total, data.unique_apps);

                    applySearchFilter();
                })
                .catch(error => {
                    console.error("Error fetching logs:", error);
                    // [CHANGE] Delegated to showError() helper
                    showError('Cannot connect to server. Make sure server is running and you are using the correct URL with password.');
                });
        }

        // ============================================
        // [CHANGE] NEW HELPER: updateStats(total, uniqueApps)
        // Extracted from loadLogs() to avoid repetition.
        // Original had these three lines duplicated in two places.
        // ============================================

        function updateStats(total, uniqueApps) {
            // [CHANGE] toLocaleString() adds thousand separators (e.g. 1,234)
            document.getElementById('totalCount').textContent = total.toLocaleString();
            document.getElementById('uniqueApps').textContent = uniqueApps;
            document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
        }

        // ============================================
        // FUNCTION: Apply Search Filter
        // ============================================

        function applySearchFilter() {
            const searchInput = document.getElementById('searchInput');
            if (!searchInput) return;
            const searchTerm = searchInput.value.toLowerCase();

            // [CHANGE] Read from state.allLogs instead of global allLogs
            let filteredLogs = state.allLogs;

            if (searchTerm !== '') {
                filteredLogs = state.allLogs.filter(log => {
                    return (
                        (log.app && log.app.toLowerCase().includes(searchTerm)) ||
                        (log.window && log.window.toLowerCase().includes(searchTerm))
                    );
                });
            }
            const filterSpan = document.getElementById('filterStatus');
            if (filterSpan) {
                if (searchTerm !== '') {
                    // [CHANGE] Wrapped count in <span class="hl"> for accent highlight
                    filterSpan.innerHTML = `<span class="hl">${filteredLogs.length}</span> result${filteredLogs.length !== 1 ? 's' : ''} for &ldquo;${searchTerm}&rdquo;`;
                } else {
                    filterSpan.innerHTML = `Showing all <span class="hl">${filteredLogs.length}</span> activities`;
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
                // [CHANGE] Delegated to showEmptyState() helper
                showEmptyState('No matching activities found.', 'Try a different search term.');
                return;
            }

            // [CHANGE] Table structure is identical to original.
            // thead/tbody markup preserved exactly — only CSS changed.
            let html = `<table><thead><tr><th>#</th><th>Timestamp</th><th>Application</th><th>Window Title</th></tr></thead><tbody>`;
            for (let i = 0; i < logs.length; i++) {
                const log = logs[i];
                html += `<tr>
                    <td>${escapeHtml(log.counter || '')}</td>
                    <td>${escapeHtml(log.timestamp || '')}</td>
                    <td><span class="app-badge">${escapeHtml(log.app || 'Unknown')}</span></td>
                    <td>${escapeHtml(log.window || '')}</td>
                </tr>`;
            }
            html += `</tbody></table>`;

            // [CHANGE] Fixed bug in original: closing tag was `</div>` embedded in
            // a JSON-looking string `{"</div>"}` — that was a typo/artifact.
            // Correct closing is just </table> which is now above.
            logContent.innerHTML = html;

            // [CHANGE v3 FIX] Only animate on the very first load.
            // On search keystrokes and auto-refresh re-renders, skip animation
            // entirely — rows stay in place instead of re-stacking each time.
            // The .animate-in class (not tbody tr globally) carries the keyframe.
            if (state.firstLoad) {
                const rows = logContent.querySelectorAll('tbody tr');
                rows.forEach((row, i) => {
                    row.classList.add('animate-in');
                    row.style.animationDelay = `${Math.min(i * 16, 200)}ms`;
                });
                state.firstLoad = false; // Never animate again after this
            }
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
        // [CHANGE] NEW HELPER: showEmptyState(headline, sub)
        // Extracted to avoid duplicating the empty-state HTML in three places.
        // Original had inline '<div class="no-results">...' repeated each time.
        // ============================================

        function showEmptyState(headline, sub) {
            document.getElementById('logContent').innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📭</div>
                    <p>${headline}</p>
                    ${sub ? `<small>${sub}</small>` : ''}
                </div>
            `;
        }

        // ============================================
        // [CHANGE] NEW HELPER: showError(message)
        // Dedicated error state with warning icon.
        // Original used the same .no-results div for errors and empty states,
        // making it impossible to distinguish visually.
        // ============================================

        function showError(message) {
            document.getElementById('logContent').innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">⚠️</div>
                    <p>${message}</p>
                </div>
            `;
        }

        // ============================================
        // FUNCTION: Export to CSV
        // ============================================

        function exportToCSV() {
            const searchInput = document.getElementById('searchInput');
            const searchTerm = searchInput ? searchInput.value.toLowerCase() : '';

            // [CHANGE] Read from state.allLogs instead of global allLogs
            let logsToExport = state.allLogs;

            if (searchTerm !== '') {
                logsToExport = state.allLogs.filter(log => {
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
            // [CHANGE] Filename includes timestamp to prevent accidental overwrite.
            // Original always saved as 'crosswatch_export.csv'.
            a.download = `crosswatch_export_${Date.now()}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            alert("✅ CSV Export Complete!");
        }

        // ============================================
        // FUNCTION: Dark Mode Toggle
        //
        // [CHANGE] Renamed internally to toggleTheme() to reflect that dark
        // is now the default — "toggling dark mode" is semantically backwards.
        // External function name kept as toggleDarkMode for any outside references.
        // Class toggled changed from 'dark-mode' to 'light-mode'.
        // localStorage key changed from 'darkMode' to 'cwTheme' to avoid
        // collisions if other apps on the same origin use 'darkMode'.
        // ============================================

        function toggleDarkMode() {
            // [CHANGE] Toggle 'light-mode' instead of 'dark-mode' — dark is the default
            const isLight = document.body.classList.toggle('light-mode');
            const btn = document.getElementById('darkModeBtn');
            if (isLight) {
                btn.innerHTML = '🌙 Dark Mode';
                // [CHANGE] localStorage key changed to 'cwTheme' (namespaced)
                localStorage.setItem('cwTheme', 'light');
            } else {
                btn.innerHTML = '☀️ Light Mode';
                localStorage.setItem('cwTheme', 'dark');
            }
        }

        // ============================================
        // FUNCTION: Load Saved Dark Mode Preference
        //
        // [CHANGE] Now restores 'light' preference only (dark is default).
        // Original checked for 'enabled' on a 'darkMode' key.
        // ============================================

        function loadDarkModePreference() {
            // [CHANGE] Key changed to 'cwTheme', value check changed to 'light'
            if (localStorage.getItem('cwTheme') === 'light') {
                document.body.classList.add('light-mode');
                const btn = document.getElementById('darkModeBtn');
                if (btn) btn.innerHTML = '🌙 Dark Mode';
            }
            // If no preference saved, dark mode stays active (body default)
        }

        // ============================================
        // AUTO-REFRESH CONTROL
        // ============================================

        function startAutoRefresh() {
            // [CHANGE] Use state.refreshIntervalId instead of global refreshInterval
            if (state.refreshIntervalId) clearInterval(state.refreshIntervalId);
            state.refreshIntervalId = setInterval(() => {
                // [CHANGE] Read from state.autoRefresh instead of global autoRefreshEnabled
                if (state.autoRefresh) {
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
                // [CHANGE] 'input' event instead of 'keyup'.
                // 'input' fires on paste, voice input, and browser autofill
                // — 'keyup' only fires on physical key releases.
                searchInput.addEventListener('input', applySearchFilter);
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
                    // [CHANGE] Write to state.autoRefresh instead of global autoRefreshEnabled
                    state.autoRefresh = e.target.checked;
                    console.log("Auto-refresh:", state.autoRefresh ? "ON" : "OFF");
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

                # [CHANGE] Access denied page redesigned to match dark theme.
                # Uses the same CSS variable philosophy — deep navy background,
                # accent border, monospace IP code block.
                # Original used the same purple gradient as the old dashboard.
                error_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>CrossWatch — Access Denied</title>
                    <link rel="preconnect" href="https://fonts.googleapis.com">
                    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
                    <style>
                        /* [CHANGE] Dark theme for access denied page — matches dashboard */
                        body {{
                            font-family: 'Plus Jakarta Sans', sans-serif;
                            background: #080c14;
                            color: #dce8f5;
                            min-height: 100vh;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            padding: 20px;
                            margin: 0;
                        }}
                        .card {{
                            max-width: 480px;
                            width: 100%;
                            background: #0d1320;
                            border: 1px solid #1e2d42;
                            border-top: 3px solid #ff5270; /* [CHANGE] Danger accent on top border */
                            border-radius: 12px;
                            padding: 40px 36px;
                            text-align: center;
                        }}
                        .icon {{ font-size: 40px; margin-bottom: 18px; opacity: 0.8; }}
                        h1 {{
                            font-size: 22px;
                            font-weight: 800;
                            color: #ff5270;
                            margin-bottom: 10px;
                        }}
                        p {{
                            color: #6e8caa;
                            font-size: 13.5px;
                            line-height: 1.6;
                            margin-bottom: 10px;
                        }}
                        /* [CHANGE] Monospace code block for the URL — easier to copy */
                        code {{
                            display: block;
                            background: #111926;
                            border: 1px solid #1e2d42;
                            border-radius: 6px;
                            padding: 12px 16px;
                            font-family: 'JetBrains Mono', monospace;
                            font-size: 12px;
                            color: #00c2ff;
                            word-break: break-all;
                            margin: 20px 0;
                            text-align: left;
                        }}
                        small {{ color: #334d68; font-size: 11px; font-family: 'JetBrains Mono', monospace; }}
                    </style>
                </head>
                <body>
                    <div class="card">
                        <div class="icon">🔒</div>
                        <h1>Access Denied</h1>
                        <p>This dashboard is password protected. Add your password to the URL:</p>
                        <code>http://{self.headers.get('Host', 'IP_ADDRESS')}/?password={SECRET_PASSWORD}</code>
                        <small>Accessing from the same computer does not require a password.</small>
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