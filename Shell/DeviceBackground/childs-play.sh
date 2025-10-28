#!/bin/bash
# ================================================
# childs-play.sh
# Linux Host Health & Triage Collector
# ================================================
# Author: Brian Maroney
# Purpose: Rapid on-host triage and system health inspection for Linux endpoints
#
# Captures:
#   - System & user info
#   - Network config, routes, DNS
#   - Group membership, logged in users
#   - Directory listings
#   - Installed software, services
#   - Running processes (at bottom)
#
# Output:
#   ~/childs_play/<HOSTNAME>_<YYYYMMDD-HHMMSS>/
#   + tar.gz archive for easy sharing
# ================================================

# Ensure running as root (some commands need privilege)
if [[ $EUID -ne 0 ]]; then
  echo "[*] Elevation required. Please run as root (sudo ./childs-play.sh)"
  exit 1
fi

HOST=$(hostname)
TS=$(date +"%Y%m%d-%H%M%S")
OUTDIR="$HOME/childs_play/${HOST}_${TS}"
mkdir -p "$OUTDIR"

LOGFILE="$OUTDIR/childs_play_log.txt"
exec > >(tee -a "$LOGFILE") 2>&1

echo "=== childs-play host snapshot ==="
echo "Host      : $HOST"
echo "User      : $(whoami)"
echo "Time      : $(date -u)"
echo "OS        : $(grep PRETTY_NAME /etc/os-release | cut -d= -f2 | tr -d '\"')"
echo "Kernel    : $(uname -r)"
echo "================================="

# -----------------------------------
# 1. SYSTEM / IDENTITY INFO (TOP)
# -----------------------------------
echo "[*] Collecting system and identity info..."
uname -a > "$OUTDIR/uname.txt"
cat /etc/os-release > "$OUTDIR/os-release.txt"
whoami > "$OUTDIR/whoami.txt"
id > "$OUTDIR/id.txt"
uptime -p > "$OUTDIR/uptime.txt"
last -n 10 > "$OUTDIR/last_logins.txt"

# -----------------------------------
# 2. NETWORK INFO
# -----------------------------------
echo "[*] Collecting network info..."
ip addr show > "$OUTDIR/ip_addr.txt"
ip route show > "$OUTDIR/ip_route.txt"
arp -n > "$OUTDIR/arp_cache.txt" 2>/dev/null
netstat -tulnp > "$OUTDIR/netstat.txt" 2>/dev/null || ss -tulnp > "$OUTDIR/netstat.txt"
ifconfig -a > "$OUTDIR/ifconfig.txt" 2>/dev/null || ip -brief addr show > "$OUTDIR/ifconfig.txt"

# -----------------------------------
# 3. DNS & HOSTS
# -----------------------------------
echo "[*] Collecting DNS and name resolution info..."
cat /etc/resolv.conf > "$OUTDIR/resolv_conf.txt"
cat /etc/hosts > "$OUTDIR/hosts.txt"
nslookup localhost > "$OUTDIR/nslookup_localhost.txt" 2>&1 || dig localhost > "$OUTDIR/dig_localhost.txt"

# -----------------------------------
# 4. USERS, GROUPS, POLICY-LIKE DATA
# -----------------------------------
echo "[*] Collecting users and groups..."
cat /etc/passwd > "$OUTDIR/etc_passwd.txt"
cat /etc/group > "$OUTDIR/etc_group.txt"
groups > "$OUTDIR/current_user_groups.txt"
who > "$OUTDIR/current_logged_in_users.txt"
sudo -l > "$OUTDIR/sudo_privileges.txt" 2>/dev/null

# -----------------------------------
# 5. FILESYSTEM, SERVICES, CRON JOBS
# -----------------------------------
echo "[*] Collecting filesystem and service info..."
ls -alh / > "$OUTDIR/dir_root.txt"
ls -alh ~ > "$OUTDIR/dir_home.txt"
systemctl list-units --type=service --all > "$OUTDIR/systemd_services.txt" 2>/dev/null
service --status-all > "$OUTDIR/service_status.txt" 2>/dev/null
crontab -l > "$OUTDIR/user_crontab.txt" 2>/dev/null
ls /etc/cron* > "$OUTDIR/system_cron_locations.txt" 2>/dev/null

# -----------------------------------
# 6. SOFTWARE / PACKAGE INVENTORY
# -----------------------------------
echo "[*] Collecting installed software list..."
if command -v dpkg >/dev/null; then
  dpkg -l > "$OUTDIR/packages_dpkg.txt"
elif command -v rpm >/dev/null; then
  rpm -qa > "$OUTDIR/packages_rpm.txt"
elif command -v pacman >/dev/null; then
  pacman -Q > "$OUTDIR/packages_pacman.txt"
else
  echo "No package manager found" > "$OUTDIR/packages.txt"
fi

# -----------------------------------
# 7. ENVIRONMENT & HARDWARE SNAPSHOT
# -----------------------------------
echo "[*] Collecting environment and hardware info..."
env > "$OUTDIR/environment.txt"
lscpu > "$OUTDIR/lscpu.txt"
lsblk > "$OUTDIR/lsblk.txt"
df -h > "$OUTDIR/disk_usage.txt"
free -m > "$OUTDIR/memory_usage.txt"

# -----------------------------------
# 8. RUNNING PROCESSES (BOTTOM)
# -----------------------------------
echo "[*] Collecting running processes..."
ps auxww > "$OUTDIR/ps_aux.txt"
top -b -n 1 > "$OUTDIR/top_snapshot.txt"
pstree -A > "$OUTDIR/pstree.txt" 2>/dev/null

# -----------------------------------
# 9. WRAP-UP
# -----------------------------------
echo "[*] Generating hashes and compressing output..."
cd "$(dirname "$OUTDIR")" || exit
(
  cd "$OUTDIR" || exit
  sha256sum * > file_hashes_sha256.txt 2>/dev/null
)
tar -czf "${OUTDIR}.tar.gz" -C "$(dirname "$OUTDIR")" "$(basename "$OUTDIR")"

echo "[*] Archive created: ${OUTDIR}.tar.gz"
echo "[*] Done. Output directory: $OUTDIR"
