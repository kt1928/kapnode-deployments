#!/bin/bash
#
# Post-Install Storage Configuration Script
# Configures LVM partitions for Longhorn and Backup storage
#
# This script should be run inside the Ubuntu VM after initial deployment
# Usage: sudo ./post-install-storage.sh [--longhorn-size GB] [--backup-size GB]
#

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

LONGHORN_SIZE=0
BACKUP_SIZE=0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --longhorn-size)
            LONGHORN_SIZE="$2"
            shift 2
            ;;
        --backup-size)
            BACKUP_SIZE="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--longhorn-size GB] [--backup-size GB]"
            echo ""
            echo "Configures storage for Longhorn and backup partitions"
            echo ""
            echo "Options:"
            echo "  --longhorn-size GB    Size of Longhorn storage in GB"
            echo "  --backup-size GB      Size of backup storage in GB"
            echo "  --help                Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root${NC}" >&2
   exit 1
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Post-Install Storage Configuration${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Function to safely identify available disks
identify_available_disks() {
    local -a disks=()

    # Use lsblk to get JSON output for reliable parsing
    while IFS= read -r line; do
        local disk_name=$(echo "$line" | jq -r '.name')
        local disk_type=$(echo "$line" | jq -r '.type')
        local disk_size=$(echo "$line" | jq -r '.size')
        local mountpoint=$(echo "$line" | jq -r '.mountpoint // empty')
        local children=$(echo "$line" | jq -r '.children // [] | length')

        # Skip if:
        # - Not a disk type
        # - Has mountpoints (in use)
        # - Has partitions/children
        if [[ "$disk_type" == "disk" ]] && [[ -z "$mountpoint" ]] && [[ "$children" -eq 0 ]]; then
            # Double-check it's not the root disk
            if ! lsblk -n -o MOUNTPOINT "/dev/$disk_name" 2>/dev/null | grep -q "^/$"; then
                disks+=("/dev/$disk_name:$disk_size")
            fi
        fi
    done < <(lsblk -J -o NAME,TYPE,SIZE,MOUNTPOINT | jq -c '.blockdevices[]')

    echo "${disks[@]}"
}

# Check for jq (needed for reliable disk detection)
if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}Installing jq for reliable disk detection...${NC}"
    apt-get update -qq && apt-get install -y jq
fi

# Detect available disks using safe method
echo "Detecting available disks..."
AVAILABLE_DISKS=($(identify_available_disks))

if [[ ${#AVAILABLE_DISKS[@]} -eq 0 ]]; then
    echo -e "${YELLOW}No additional disks detected. Trying fallback method...${NC}"

    # Fallback to manual detection
    for disk_path in /dev/sd[b-z] /dev/vd[b-z] /dev/nvme[0-9]n[1-9]; do
        if [[ -b "$disk_path" ]]; then
            # Check if disk is not mounted and has no partitions
            if ! lsblk -n -o MOUNTPOINT "$disk_path" 2>/dev/null | grep -q .; then
                if ! lsblk -n -o TYPE "$disk_path" 2>/dev/null | grep -q "part"; then
                    disk_size=$(lsblk -n -o SIZE "$disk_path" | head -1)
                    AVAILABLE_DISKS+=("$disk_path:$disk_size")
                fi
            fi
        fi
    done
fi

echo ""
echo "Detected available disks:"
if [[ ${#AVAILABLE_DISKS[@]} -eq 0 ]]; then
    echo -e "${YELLOW}  No additional disks detected.${NC}"
    echo ""
    echo "This could mean:"
    echo "  1. No additional disks were attached during VM creation"
    echo "  2. Disks are already partitioned/mounted"
    echo "  3. Disks haven't been detected yet (try rebooting)"
    echo ""
    exit 0
fi

for disk_info in "${AVAILABLE_DISKS[@]}"; do
    disk_path="${disk_info%:*}"
    disk_size="${disk_info#*:}"
    echo "  - $disk_path ($disk_size)"
done
echo ""

DISK_INDEX=0

# Configure Longhorn storage
if [[ $LONGHORN_SIZE -gt 0 ]] && [[ $DISK_INDEX -lt ${#AVAILABLE_DISKS[@]} ]]; then
    DISK_INFO="${AVAILABLE_DISKS[$DISK_INDEX]}"
    DISK="${DISK_INFO%:*}"
    echo -e "${YELLOW}Configuring Longhorn storage on $DISK (${LONGHORN_SIZE}GB)...${NC}"

    # Wipe existing partition table
    wipefs -a "$DISK" 2>/dev/null || true

    # Create partition
    parted -s "$DISK" mklabel gpt
    parted -s "$DISK" mkpart primary ext4 0% 100%
    partprobe "$DISK"
    sleep 2

    # Determine partition name (handle both sd/vd and nvme naming)
    if [[ "$DISK" =~ nvme ]]; then
        PARTITION="${DISK}p1"
    else
        PARTITION="${DISK}1"
    fi

    # Wait for partition to appear
    for i in {1..10}; do
        if [[ -b "$PARTITION" ]]; then
            break
        fi
        sleep 1
    done

    if [[ ! -b "$PARTITION" ]]; then
        echo -e "${RED}Error: Partition $PARTITION not found after creation${NC}" >&2
        exit 1
    fi

    # Format as ext4
    mkfs.ext4 -F -L longhorn "$PARTITION"

    # Create mount point
    mkdir -p /var/lib/longhorn

    # Add to fstab
    UUID=$(blkid -s UUID -o value "$PARTITION")
    if ! grep -q "$UUID" /etc/fstab; then
        echo "UUID=$UUID /var/lib/longhorn ext4 defaults,noatime 0 2" >> /etc/fstab
    fi

    # Mount
    mount "$PARTITION" /var/lib/longhorn

    echo -e "${GREEN}✓ Longhorn storage configured on $PARTITION${NC}"
    DISK_INDEX=$((DISK_INDEX + 1))
fi

# Configure Backup storage
if [[ $BACKUP_SIZE -gt 0 ]] && [[ $DISK_INDEX -lt ${#AVAILABLE_DISKS[@]} ]]; then
    DISK_INFO="${AVAILABLE_DISKS[$DISK_INDEX]}"
    DISK="${DISK_INFO%:*}"
    echo -e "${YELLOW}Configuring Backup storage on $DISK (${BACKUP_SIZE}GB)...${NC}"

    # Wipe existing partition table
    wipefs -a "$DISK" 2>/dev/null || true

    # Create partition
    parted -s "$DISK" mklabel gpt
    parted -s "$DISK" mkpart primary ext4 0% 100%
    partprobe "$DISK"
    sleep 2

    # Determine partition name (handle both sd/vd and nvme naming)
    if [[ "$DISK" =~ nvme ]]; then
        PARTITION="${DISK}p1"
    else
        PARTITION="${DISK}1"
    fi

    # Wait for partition to appear
    for i in {1..10}; do
        if [[ -b "$PARTITION" ]]; then
            break
        fi
        sleep 1
    done

    if [[ ! -b "$PARTITION" ]]; then
        echo -e "${RED}Error: Partition $PARTITION not found after creation${NC}" >&2
        exit 1
    fi

    # Format as ext4
    mkfs.ext4 -F -L backups "$PARTITION"

    # Create mount point
    mkdir -p /var/lib/backups

    # Add to fstab
    UUID=$(blkid -s UUID -o value "$PARTITION")
    if ! grep -q "$UUID" /etc/fstab; then
        echo "UUID=$UUID /var/lib/backups ext4 defaults,noatime 0 2" >> /etc/fstab
    fi

    # Mount
    mount "$PARTITION" /var/lib/backups

    echo -e "${GREEN}✓ Backup storage configured on $PARTITION${NC}"
    DISK_INDEX=$((DISK_INDEX + 1))
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Storage configuration complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Mounted filesystems:"
df -h | grep -E "longhorn|backups" || echo "  No additional storage mounted"
echo ""
echo "Storage summary:"
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT,LABEL | grep -E "longhorn|backups|NAME" || true
