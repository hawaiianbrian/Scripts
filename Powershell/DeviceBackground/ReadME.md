# 🧸 childs-play.ps1  
**Windows Host Health & Triage Collection Script**

---

## 📖 Overview

**childs-play.ps1** is a lightweight PowerShell script designed for quick on-host health and situational awareness checks during incident response or triage.  
It gathers system, network, and configuration details — plus running process information — and outputs neatly organized reports for analysis.

The goal is to make **initial host inspection “child’s play”**: fast, consistent, and reliable.

---

## ⚙️ Features

The script automatically elevates privileges (prompts for Administrator rights if needed) and captures:

### 🧩 System & Identity
- `systeminfo` – OS, build, uptime, patch level, etc.  
- `whoami /all` – current user, groups, privileges  

### 🌐 Network
- `ipconfig /all` – interface configurations  
- `arp -a` – ARP cache for nearby hosts  
- `netstat -abno` – open network connections with owning processes  
- `Get-NetTCPConnection` – PowerShell equivalent for structured output  
- `route print` – local routing table  

### 🔎 DNS & Name Resolution
- `nslookup <hostname>`  
- `nslookup microsoft.com`  

### 🧱 Policy, Users, & Groups
- `gpresult /r /scope user`  
- `gpresult /r /scope computer`  
- `net user` – local accounts  
- `net localgroup administrators` – members of local admin group  

### 📂 File System, Services, & Tasks
- Directory listings for `C:\` and the current user profile  
- `Get-Service` – service status and startup configuration  
- `Get-ScheduledTask` – scheduled tasks (names, paths, states)  

### 🧩 Software Inventory
- Installed programs from registry (HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall)

### 🧠 Running Processes *(bottom of report for clarity)*
- `tasklist /v /fo list`  
- `Get-Process` – sorted by CPU usage  

---

## 📁 Output Structure

All collected data is saved to:

