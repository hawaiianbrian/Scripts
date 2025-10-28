# 🧸 childs-play.sh  
**Linux Host Health & Triage Collection Script**

---

## 📖 Overview

`childs-play.sh` is a lightweight bash script that performs comprehensive system triage and health checks on Linux devices.  
It’s designed for quick host visibility during incident response, audits, or troubleshooting.

All output is collected locally and archived for review — no network transmission, no system changes.

---

## ⚙️ Features

### 🧩 System & Identity
- `uname -a` – kernel and architecture info  
- `/etc/os-release` – OS version details  
- `whoami`, `id` – current user & group memberships  
- `uptime`, `last` – uptime and login history  

### 🌐 Network
- `ip addr show` / `ifconfig -a` – interface details  
- `ip route show` – routing table  
- `arp -n` – ARP cache  
- `netstat -tulnp` or `ss -tulnp` – open ports and listening processes  

### 🔎 DNS & Name Resolution
- `/etc/resolv.conf`, `/etc/hosts`  
- `nslookup localhost` or `dig localhost`  

### 👥 Users & Access
- `/etc/passwd`, `/etc/group` – local accounts  
- `who` – currently logged-in users  
- `groups` – current user’s groups  
- `sudo -l` – available sudo privileges  

### 📂 Filesystem, Services & Tasks
- Directory listings for `/` and home directory  
- `systemctl list-units --type=service` – active services  
- `service --status-all` – legacy service list  
- `crontab -l` & `/etc/cron*` – scheduled tasks  

### 🧰 Installed Software
- Auto-detects and uses:
  - `dpkg -l` (Debian/Ubuntu)
  - `rpm -qa` (RHEL/CentOS)
  - `pacman -Q` (Arch)

### 🧠 Hardware & Environment
- `env` – environment variables  
- `lscpu`, `lsblk`, `df -h`, `free -m` – system resource snapshot  

### 🪶 Running Processes *(bottom of report)*
- `ps auxww` – full process list  
- `top -b -n 1` – live CPU/memory snapshot  
- `pstree -A` – process hierarchy  

---

## 📁 Output Structure

All results are saved to:

