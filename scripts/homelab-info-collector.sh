#!/bin/bash

# Homelab Information Collector Script
# Run this on each system to gather comprehensive documentation data
# Usage: bash homelab-info-collector.sh > system-info-$(hostname).txt

echo "========================================="
echo "HOMELAB SYSTEM INFORMATION COLLECTOR"
echo "========================================="
echo "Hostname: $(hostname)"
echo "Date: $(date)"
echo "User: $(whoami)"
echo ""

# System Information
echo "========================================="
echo "SYSTEM INFORMATION"
echo "========================================="
echo "--- Basic System Info ---"
uname -a
echo ""
echo "--- OS Release ---"
if [ -f /etc/os-release ]; then
    cat /etc/os-release
elif [ -f /etc/redhat-release ]; then
    cat /etc/redhat-release
elif [ -f /etc/debian_version ]; then
    echo "Debian $(cat /etc/debian_version)"
fi
echo ""
echo "--- Uptime ---"
uptime
echo ""

# Hardware Information
echo "========================================="
echo "HARDWARE INFORMATION"
echo "========================================="
echo "--- CPU Information ---"
lscpu 2>/dev/null || cat /proc/cpuinfo | grep -E "(processor|model name|cpu MHz|cache size|cpu cores)" | head -20
echo ""
echo "--- Memory Information ---"
free -h
echo ""
echo "--- Memory Details ---"
cat /proc/meminfo | grep -E "(MemTotal|MemFree|MemAvailable|SwapTotal|SwapFree)"
echo ""
echo "--- Disk Information ---"
lsblk -f 2>/dev/null || df -h
echo ""
echo "--- Disk Usage ---"
df -h
echo ""
echo "--- Storage Details ---"
if command -v lshw >/dev/null 2>&1; then
    sudo lshw -class disk -short 2>/dev/null || echo "lshw not available or requires sudo"
fi
echo ""
echo "--- PCI Devices ---"
lspci 2>/dev/null | head -20
echo ""
echo "--- USB Devices ---"
lsusb 2>/dev/null || echo "lsusb not available"
echo ""

# Network Information
echo "========================================="
echo "NETWORK INFORMATION"
echo "========================================="
echo "--- Network Interfaces ---"
ip addr show 2>/dev/null || ifconfig -a
echo ""
echo "--- Routing Table ---"
ip route show 2>/dev/null || route -n
echo ""
echo "--- DNS Configuration ---"
cat /etc/resolv.conf 2>/dev/null
echo ""
echo "--- Network Connections ---"
ss -tuln 2>/dev/null || netstat -tuln | head -30
echo ""
echo "--- Tailscale Status ---"
if command -v tailscale >/dev/null 2>&1; then
    tailscale status 2>/dev/null || echo "Tailscale installed but status unavailable"
else
    echo "Tailscale not installed"
fi
echo ""

# Docker Information
echo "========================================="
echo "DOCKER INFORMATION"
echo "========================================="
if command -v docker >/dev/null 2>&1; then
    echo "--- Docker Version ---"
    docker --version 2>/dev/null
    echo ""
    echo "--- Docker System Info ---"
    docker system info 2>/dev/null | head -30
    echo ""
    echo "--- Running Containers ---"
    docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null
    echo ""
    echo "--- All Containers ---"
    docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null
    echo ""
    echo "--- Docker Images ---"
    docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" 2>/dev/null
    echo ""
    echo "--- Docker Networks ---"
    docker network ls 2>/dev/null
    echo ""
    echo "--- Docker Volumes ---"
    docker volume ls 2>/dev/null
    echo ""
    echo "--- Docker Compose Files ---"
    find /opt /home -name "docker-compose.yml" -o -name "docker-compose.yaml" 2>/dev/null | head -10
    echo ""
else
    echo "Docker not installed"
fi

# Services and Processes
echo "========================================="
echo "SERVICES AND PROCESSES"
echo "========================================="
echo "--- Systemd Services (Active) ---"
if command -v systemctl >/dev/null 2>&1; then
    systemctl list-units --type=service --state=active --no-pager | head -20
    echo ""
    echo "--- Enabled Services ---"
    systemctl list-unit-files --type=service --state=enabled --no-pager | head -20
else
    echo "Systemd not available"
fi
echo ""
echo "--- Top Processes by CPU ---"
ps aux --sort=-%cpu | head -15
echo ""
echo "--- Top Processes by Memory ---"
ps aux --sort=-%mem | head -15
echo ""

# Storage and Filesystem
echo "========================================="
echo "STORAGE AND FILESYSTEM"
echo "========================================="
echo "--- Mounted Filesystems ---"
mount | grep -v tmpfs | grep -v devpts | grep -v sysfs | grep -v proc
echo ""
echo "--- Disk I/O Statistics ---"
if command -v iostat >/dev/null 2>&1; then
    iostat -x 1 1 2>/dev/null
else
    echo "iostat not available"
fi
echo ""
echo "--- ZFS Pools (if available) ---"
if command -v zpool >/dev/null 2>&1; then
    zpool status 2>/dev/null
    zpool list 2>/dev/null
else
    echo "ZFS not available"
fi
echo ""
echo "--- LVM Information ---"
if command -v lvs >/dev/null 2>&1; then
    sudo lvs 2>/dev/null || echo "LVM commands require sudo"
    sudo vgs 2>/dev/null || echo "LVM commands require sudo"
    sudo pvs 2>/dev/null || echo "LVM commands require sudo"
else
    echo "LVM not available"
fi
echo ""

# Configuration Files
echo "========================================="
echo "CONFIGURATION FILES"
echo "========================================="
echo "--- Crontab ---"
crontab -l 2>/dev/null || echo "No crontab for current user"
echo ""
echo "--- System Crontab ---"
cat /etc/crontab 2>/dev/null || echo "/etc/crontab not readable"
echo ""
echo "--- SSH Configuration ---"
if [ -f /etc/ssh/sshd_config ]; then
    grep -E "^(Port|PermitRootLogin|PasswordAuthentication|PubkeyAuthentication)" /etc/ssh/sshd_config 2>/dev/null
fi
echo ""
echo "--- Firewall Status ---"
if command -v ufw >/dev/null 2>&1; then
    sudo ufw status verbose 2>/dev/null || echo "UFW status requires sudo"
elif command -v firewall-cmd >/dev/null 2>&1; then
    firewall-cmd --list-all 2>/dev/null || echo "Firewall-cmd requires privileges"
elif command -v iptables >/dev/null 2>&1; then
    sudo iptables -L -n 2>/dev/null | head -20 || echo "iptables requires sudo"
fi
echo ""

# Application-Specific Information
echo "========================================="
echo "APPLICATION-SPECIFIC INFORMATION"
echo "========================================="
echo "--- Proxmox (if available) ---"
if [ -f /etc/pve/local/pve-ssl.pem ]; then
    echo "Proxmox detected"
    pvesh get /version 2>/dev/null || echo "Proxmox CLI not available"
    qm list 2>/dev/null || echo "VM list not available"
    pct list 2>/dev/null || echo "Container list not available"
fi
echo ""
echo "--- Pi-hole (if available) ---"
if [ -f /etc/pihole/setupVars.conf ]; then
    echo "Pi-hole detected"
    cat /etc/pihole/setupVars.conf 2>/dev/null | grep -v PASSWORD
    pihole status 2>/dev/null || echo "Pi-hole command not available"
fi
echo ""
echo "--- Home Assistant (if available) ---"
if [ -d /home/homeassistant ] || [ -d /opt/homeassistant ]; then
    echo "Home Assistant directory found"
    find /home /opt -name "configuration.yaml" 2>/dev/null | head -5
fi
echo ""

# Environment and Variables
echo "========================================="
echo "ENVIRONMENT INFORMATION"
echo "========================================="
echo "--- Environment Variables (filtered) ---"
env | grep -E "(PATH|HOME|USER|SHELL|DOCKER|COMPOSE)" | sort
echo ""
echo "--- Installed Packages (sample) ---"
if command -v dpkg >/dev/null 2>&1; then
    dpkg -l | grep -E "(docker|nginx|apache|mysql|postgres|redis|git)" 2>/dev/null
elif command -v rpm >/dev/null 2>&1; then
    rpm -qa | grep -E "(docker|nginx|apache|mysql|postgres|redis|git)" 2>/dev/null
elif command -v pacman >/dev/null 2>&1; then
    pacman -Q | grep -E "(docker|nginx|apache|mysql|postgres|redis|git)" 2>/dev/null
fi
echo ""

# Log Information
echo "========================================="
echo "LOG INFORMATION"
echo "========================================="
echo "--- Recent System Logs ---"
if command -v journalctl >/dev/null 2>&1; then
    journalctl --since "1 hour ago" --no-pager | tail -20 2>/dev/null
else
    tail -20 /var/log/syslog 2>/dev/null || tail -20 /var/log/messages 2>/dev/null || echo "System logs not accessible"
fi
echo ""
echo "--- Docker Logs (if available) ---"
if command -v docker >/dev/null 2>&1; then
    echo "Recent container logs:"
    docker ps --format "{{.Names}}" 2>/dev/null | head -5 | while read container; do
        echo "--- $container ---"
        docker logs --tail 5 "$container" 2>/dev/null || echo "Cannot access logs for $container"
    done
fi
echo ""

# Security Information
echo "========================================="
echo "SECURITY INFORMATION"
echo "========================================="
echo "--- SSL Certificates ---"
find /etc/ssl /etc/pki /opt -name "*.crt" -o -name "*.pem" 2>/dev/null | head -10
echo ""
echo "--- Users with Shell Access ---"
grep -E "/(bash|zsh|sh)$" /etc/passwd 2>/dev/null
echo ""
echo "--- Sudo Configuration ---"
if [ -f /etc/sudoers ]; then
    grep -v "^#" /etc/sudoers 2>/dev/null | grep -v "^$" | head -10
fi
echo ""

echo "========================================="
echo "COLLECTION COMPLETE"
echo "========================================="
echo "System: $(hostname)"
echo "Completed: $(date)"
echo ""
echo "Please save this output and share it for documentation enhancement."
echo "Note: Some commands may require sudo privileges for complete information."