# 🔍 Event Log Keyword Search (PowerShell)

**Author:** Brian Maroney  
**Script:** `eventSearch_keywords.ps1`  
**Version:** 1.0.0  

---

## 📘 Overview

`eventSearch_keywords.ps1` is a PowerShell utility that allows security analysts, incident responders, and system administrators to **search Windows Event Logs for specific keywords**.  
The script interactively prompts for:
- Keywords (comma-separated)
- Event Log to search (default: Security)
- Time range (days to look back, default: 7)
- Option to export results to CSV  

This script is ideal for quick triage, threat hunting, or forensic analysis when investigating suspicious activity on Windows systems.

---

## ⚙️ Features

- ✅ Interactive keyword input (supports multiple, comma-separated values)
- ✅ Searches **Security**, **System**, or **Application** logs (customizable)
- ✅ Optional date filter (e.g., search last 7 or 30 days)
- ✅ Displays matching events in a formatted table
- ✅ Optionally exports findings to a CSV report
- ✅ Error handling for invalid or restricted log access

---

## 🧩 Usage

### 1. Run PowerShell as Administrator
Security logs require elevated permissions.  
Right-click PowerShell → “Run as Administrator”

### 2. Execute the Script
```powershell
PS C:\> .\eventSearch_keywords.ps1
