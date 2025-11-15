#!/bin/bash
#
# Proxmox Ubuntu 24.04 LTS VM Deployment Script
# Automates VM creation with cloud-init for K3s worker nodes
#
# Usage: ./deploy-ubuntu-vm.sh [options]
#   --name NAME           VM name (required)
#   --vmid VMID           VM ID (required, or auto-increment)
#   --ip IP_ADDRESS       Static IP address (required)
#   --gateway GATEWAY     Gateway IP (default: 192.168.86.1)
#   --dns DNS_SERVERS     DNS servers comma-separated (default: 192.168.86.1,8.8.8.8)
#   --memory RAM_GB       RAM in GB (default: 16)
#   --cores CORES         CPU cores (default: 4)
#   --disk-size DISK_GB   Disk size in GB (default: 200)
#   --storage STORAGE     Proxmox storage pool (default: local-lvm)
#   --tailscale-key KEY   Tailscale auth key (required)
#   --ssh-pubkey KEY      SSH public key content (required)
#   --location LOCATION   Location tag (Brooklyn, Manhattan, etc.)
#   --node-type TYPE      Type: k3s-worker or backup (default: k3s-worker)
#   --longhorn-size GB    Longhorn storage size in GB (default: 0, disabled)
#   --backup-size GB      Backup storage size in GB (default: 0, disabled)
#   --k3s-master URL      K3s master URL (optional, for auto-join)
#   --k3s-token TOKEN     K3s join token (optional, for auto-join)
#   --yes                 Skip confirmation prompt
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
VM_NAME=""
VMID=""
IP_ADDRESS=""
GATEWAY="192.168.86.1"
MEMORY=16
CORES=4
DISK_SIZE=200
STORAGE="local-lvm"
TAILSCALE_KEY=""
SSH_PUBKEY=""
LOCATION=""
NODE_TYPE="k3s-worker"
LONGHORN_SIZE=0
BACKUP_SIZE=0
NETWORK="192.168.86.0/24"
DNS_SERVERS="192.168.86.1,8.8.8.8"
K3S_MASTER=""
K3S_TOKEN=""
SKIP_CONFIRM=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --name)
            VM_NAME="$2"
            shift 2
            ;;
        --vmid)
            VMID="$2"
            shift 2
            ;;
        --ip)
            IP_ADDRESS="$2"
            shift 2
            ;;
        --gateway)
            GATEWAY="$2"
            shift 2
            ;;
        --dns)
            DNS_SERVERS="$2"
            shift 2
            ;;
        --memory)
            MEMORY="$2"
            shift 2
            ;;
        --cores)
            CORES="$2"
            shift 2
            ;;
        --disk-size)
            DISK_SIZE="$2"
            shift 2
            ;;
        --storage)
            STORAGE="$2"
            shift 2
            ;;
        --tailscale-key)
            TAILSCALE_KEY="$2"
            shift 2
            ;;
        --ssh-pubkey)
            SSH_PUBKEY="$2"
            shift 2
            ;;
        --location)
            LOCATION="$2"
            shift 2
            ;;
        --node-type)
            NODE_TYPE="$2"
            shift 2
            ;;
        --longhorn-size)
            LONGHORN_SIZE="$2"
            shift 2
            ;;
        --backup-size)
            BACKUP_SIZE="$2"
            shift 2
            ;;
        --k3s-master)
            K3S_MASTER="$2"
            shift 2
            ;;
        --k3s-token)
            K3S_TOKEN="$2"
            shift 2
            ;;
        --yes)
            SKIP_CONFIRM=true
            shift
            ;;
        --help)
            cat << EOF
Proxmox Ubuntu 24.04 LTS VM Deployment Script

Usage: $0 [options]

Required:
  --name NAME              VM hostname (e.g., node-bk-01)
  --vmid VMID              Proxmox VM ID (100-999)
  --ip IP_ADDRESS          Static IP address
  --tailscale-key KEY      Tailscale auth key (use ephemeral keys)
  --ssh-pubkey KEY         SSH public key content

Optional:
  --gateway GATEWAY        Gateway IP (default: 192.168.86.1)
  --dns DNS_SERVERS        DNS servers comma-separated (default: 192.168.86.1,8.8.8.8)
  --memory RAM_GB          RAM in GB (default: 16)
  --cores CORES            CPU cores (default: 4)
  --disk-size DISK_GB      OS disk size in GB (default: 200)
  --storage STORAGE        Proxmox storage pool (default: local-lvm)
  --location LOCATION      Location tag (Brooklyn, Manhattan, etc.)
  --node-type TYPE         k3s-worker or backup (default: k3s-worker)
  --longhorn-size GB       Longhorn storage size in GB (0 = disabled)
  --backup-size GB         Backup storage size in GB (0 = disabled)
  --k3s-master URL         K3s master URL for auto-join (e.g., https://minikapserver:6443)
  --k3s-token TOKEN        K3s join token for auto-join
  --yes                    Skip confirmation prompt

Examples:
  # Deploy K3s worker node
  $0 --name node-bk-01 --vmid 101 --ip 192.168.86.101 \\
     --tailscale-key tskey-auth-xxx --ssh-pubkey "\$(cat ~/.ssh/id_rsa.pub)" \\
     --location Brooklyn --yes

  # Deploy backup node with storage
  $0 --name backup-node-fh --vmid 102 --ip 192.168.50.102 \\
     --tailscale-key tskey-auth-xxx --ssh-pubkey "\$(cat ~/.ssh/id_rsa.pub)" \\
     --location "Forest Hills" --node-type backup --disk-size 500 --yes

EOF
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}" >&2
            exit 1
            ;;
    esac
done

# Validate required parameters
if [[ -z "$VM_NAME" ]]; then
    echo -e "${RED}Error: --name is required${NC}" >&2
    exit 1
fi

if [[ -z "$VMID" ]]; then
    echo -e "${YELLOW}Warning: --vmid not specified, auto-detecting next available VMID...${NC}"
    VMID=$(pvesh get /cluster/nextid 2>/dev/null || echo "100")
fi

if [[ -z "$IP_ADDRESS" ]]; then
    echo -e "${RED}Error: --ip is required${NC}" >&2
    exit 1
fi

if [[ -z "$TAILSCALE_KEY" ]]; then
    echo -e "${RED}Error: --tailscale-key is required${NC}" >&2
    exit 1
fi

if [[ -z "$SSH_PUBKEY" ]]; then
    echo -e "${RED}Error: --ssh-pubkey is required${NC}" >&2
    exit 1
fi

# Validate VMID is numeric
if ! [[ "$VMID" =~ ^[0-9]+$ ]]; then
    echo -e "${RED}Error: VMID must be numeric${NC}" >&2
    exit 1
fi

# Check if VMID already exists
if qm status "$VMID" &>/dev/null; then
    echo -e "${RED}Error: VMID $VMID already exists${NC}" >&2
    exit 1
fi

# Sanitize location for tags (replace spaces with hyphens)
LOCATION_TAG="${LOCATION// /-}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Proxmox Ubuntu 24.04 VM Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "VM Name:         $VM_NAME"
echo "VMID:            $VMID"
echo "IP Address:      $IP_ADDRESS"
echo "Gateway:         $GATEWAY"
echo "DNS Servers:     $DNS_SERVERS"
echo "Memory:          ${MEMORY}GB"
echo "CPU Cores:       $CORES"
echo "Disk Size:       ${DISK_SIZE}GB"
echo "Storage Pool:    $STORAGE"
echo "Location:        ${LOCATION:-Not specified}"
echo "Node Type:       $NODE_TYPE"
if [[ $LONGHORN_SIZE -gt 0 ]]; then
    echo "Longhorn:        ${LONGHORN_SIZE}GB"
fi
if [[ $BACKUP_SIZE -gt 0 ]]; then
    echo "Backup Storage:  ${BACKUP_SIZE}GB"
fi
if [[ -n "$K3S_MASTER" ]]; then
    echo "K3s Auto-Join:   Enabled ($K3S_MASTER)"
fi
echo ""

if [[ "$SKIP_CONFIRM" != true ]]; then
    read -p "Continue with deployment? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled."
        exit 1
    fi
fi

# Generate cloud-init user-data with proper variable handling
USER_DATA=$(cat <<EOF
#cloud-config
hostname: $VM_NAME
fqdn: $VM_NAME.local
manage_etc_hosts: true

users:
  - name: ubuntu
    groups: [adm, audio, cdrom, dialout, dip, floppy, lxd, netdev, plugdev, sudo, video]
    lock_passwd: false
    shell: /bin/bash
    sudo: ['ALL=(ALL) NOPASSWD:ALL']
    ssh_authorized_keys:
      - $SSH_PUBKEY

# Disable password authentication
ssh_pwauth: false
disable_root: true

# Update system on first boot
package_update: true
package_upgrade: true

# Install essential packages
packages:
  - curl
  - wget
  - git
  - vim
  - htop
  - net-tools
  - lvm2
  - parted
  - tailscale
  - open-iscsi
  - nfs-common

# Write files
write_files:
  - path: /etc/netplan/00-installer-config.yaml
    content: |
      network:
        version: 2
        renderer: networkd
        ethernets:
          eth0:
            dhcp4: false
            addresses:
              - $IP_ADDRESS/24
            routes:
              - to: default
                via: $GATEWAY
            nameservers:
              addresses: [$DNS_SERVERS]
    permissions: '0644'
  - path: /usr/local/bin/configure-tailscale.sh
    content: |
      #!/bin/bash
      set -e
      echo "Configuring Tailscale..."
      # Using 90-day expiration auth key
      tailscale up --authkey=$TAILSCALE_KEY --accept-routes --hostname=$VM_NAME
      systemctl enable tailscaled
      echo "Tailscale configured successfully"
    permissions: '0755'
  - path: /usr/local/bin/configure-storage.sh
    content: |
      #!/bin/bash
      set -e

      # Wait for disks to be detected
      sleep 10

      # Configure storage - will be run by post-install-storage.sh
      LONGHORN_SIZE=$LONGHORN_SIZE
      BACKUP_SIZE=$BACKUP_SIZE

      if [[ \$LONGHORN_SIZE -gt 0 ]] || [[ \$BACKUP_SIZE -gt 0 ]]; then
        echo "Storage configuration needed. Run post-install-storage.sh manually."
      fi
    permissions: '0755'
  - path: /usr/local/bin/join-k3s.sh
    content: |
      #!/bin/bash
      set -e

      K3S_MASTER="$K3S_MASTER"
      K3S_TOKEN="$K3S_TOKEN"

      if [[ -n "\$K3S_MASTER" ]] && [[ -n "\$K3S_TOKEN" ]]; then
        echo "Joining K3s cluster at \$K3S_MASTER..."
        curl -sfL https://get.k3s.io | K3S_URL="\$K3S_MASTER" K3S_TOKEN="\$K3S_TOKEN" sh -

        # Label node with location
        if [[ -n "$LOCATION_TAG" ]]; then
          kubectl label node $VM_NAME topology.kubernetes.io/zone=$LOCATION_TAG --overwrite || true
        fi
      fi
    permissions: '0755'
  - path: /etc/systemd/system/configure-tailscale.service
    content: |
      [Unit]
      Description=Configure Tailscale
      After=network-online.target
      Wants=network-online.target

      [Service]
      Type=oneshot
      ExecStart=/usr/local/bin/configure-tailscale.sh
      RemainAfterExit=yes

      [Install]
      WantedBy=multi-user.target
    permissions: '0644'

# Run commands on first boot
runcmd:
  - systemctl enable configure-tailscale.service
  - systemctl start configure-tailscale.service
  - systemctl enable iscsid
  - systemctl start iscsid
  - |
    if [[ -n "$K3S_MASTER" ]] && [[ -n "$K3S_TOKEN" ]]; then
      /usr/local/bin/join-k3s.sh || echo "K3s join failed, run manually"
    fi

# Final message
final_message: |
  Ubuntu 24.04 LTS VM deployment complete!
  Hostname: $VM_NAME
  IP: $IP_ADDRESS
  Location: ${LOCATION:-Not specified}
  Tailscale: Configured
  Next steps:
    1. SSH into the VM: ssh ubuntu@$IP_ADDRESS
    2. Run post-install-storage.sh if storage was configured
    3. Join K3s cluster if not auto-joined
EOF
)

# Generate cloud-init meta-data
META_DATA=$(cat <<EOF
instance-id: $VMID
local-hostname: $VM_NAME
EOF
)

# Generate network-config (Netplan v2 format)
NETWORK_CONFIG=$(cat <<EOF
version: 2
ethernets:
  eth0:
    dhcp4: false
    addresses:
      - $IP_ADDRESS/24
    routes:
      - to: default
        via: $GATEWAY
    nameservers:
      addresses: [$DNS_SERVERS]
EOF
)

echo -e "${YELLOW}Creating VM $VMID...${NC}"

# Download Ubuntu 24.04 cloud image if not already cached
UBUNTU_IMG="ubuntu-24.04-server-cloudimg-amd64.img"
UBUNTU_URL="https://cloud-images.ubuntu.com/releases/24.04/release/ubuntu-24.04-server-cloudimg-amd64.img"

if [[ ! -f "/var/lib/vz/template/iso/$UBUNTU_IMG" ]]; then
    echo -e "${YELLOW}Downloading Ubuntu 24.04 cloud image...${NC}"
    wget -q --show-progress -O "/var/lib/vz/template/iso/$UBUNTU_IMG" "$UBUNTU_URL" || {
        echo -e "${RED}Error: Failed to download Ubuntu image${NC}" >&2
        exit 1
    }
else
    echo -e "${GREEN}Using cached Ubuntu image${NC}"
fi

# Create VM
echo -e "${YELLOW}Creating VM configuration...${NC}"
qm create "$VMID" \
    --name "$VM_NAME" \
    --memory "$((MEMORY * 1024))" \
    --cores "$CORES" \
    --net0 virtio,bridge=vmbr0 \
    --scsihw virtio-scsi-pci \
    --agent enabled=1,fstrim_cloned_disks=1 \
    --onboot 1 \
    --ostype l26 \
    --cpu host \
    --machine q35 \
    --bios ovmf \
    --efidisk0 "$STORAGE:1,format=raw,efitype=4m,pre-enrolled-keys=1" \
    --boot order=scsi0 \
    --ide2 "$STORAGE:cloudinit" \
    --serial0 socket --vga serial0 \
    --tags "${LOCATION_TAG:-},${NODE_TYPE},ubuntu-24.04"

# Create snippets directory if it doesn't exist
mkdir -p /var/lib/vz/snippets

# Write cloud-init files to snippets
echo -e "${YELLOW}Configuring cloud-init...${NC}"
echo "$USER_DATA" > "/var/lib/vz/snippets/user-data-$VMID.yaml"
echo "$META_DATA" > "/var/lib/vz/snippets/meta-data-$VMID.yaml"
echo "$NETWORK_CONFIG" > "/var/lib/vz/snippets/network-config-$VMID.yaml"

# Set cloud-init configuration
qm set "$VMID" --cicustom "user=local:snippets/user-data-$VMID.yaml,meta=local:snippets/meta-data-$VMID.yaml,network=local:snippets/network-config-$VMID.yaml"

# Import Ubuntu cloud image to unused disk
echo -e "${YELLOW}Importing Ubuntu cloud image...${NC}"
qm disk import "$VMID" "/var/lib/vz/template/iso/$UBUNTU_IMG" "$STORAGE" --format raw

# Attach imported disk as scsi0
echo -e "${YELLOW}Attaching OS disk...${NC}"
qm set "$VMID" --scsi0 "$STORAGE:vm-$VMID-disk-0,size=${DISK_SIZE}G"

# Add additional storage for Longhorn if specified
if [[ $LONGHORN_SIZE -gt 0 ]]; then
    echo -e "${YELLOW}Adding ${LONGHORN_SIZE}GB disk for Longhorn storage...${NC}"
    qm set "$VMID" --scsi1 "$STORAGE:${LONGHORN_SIZE},format=raw"
fi

# Add additional storage for Backup if specified
if [[ $BACKUP_SIZE -gt 0 ]]; then
    echo -e "${YELLOW}Adding ${BACKUP_SIZE}GB disk for backup storage...${NC}"
    qm set "$VMID" --scsi2 "$STORAGE:${BACKUP_SIZE},format=raw"
fi

echo -e "${GREEN}VM created successfully!${NC}"
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "1. Start the VM: qm start $VMID"
echo "2. Wait for cloud-init to complete (~2-3 minutes)"
echo "3. Monitor boot: qm terminal $VMID (Ctrl+O to exit)"
echo "4. SSH into the VM: ssh ubuntu@$IP_ADDRESS"
if [[ $LONGHORN_SIZE -gt 0 ]] || [[ $BACKUP_SIZE -gt 0 ]]; then
    echo "5. Copy and run post-install-storage.sh for storage configuration:"
    echo "   scp post-install-storage.sh ubuntu@$IP_ADDRESS:~/"
    echo "   ssh ubuntu@$IP_ADDRESS 'sudo ./post-install-storage.sh --longhorn-size $LONGHORN_SIZE --backup-size $BACKUP_SIZE'"
fi
if [[ -z "$K3S_MASTER" ]] && [[ "$NODE_TYPE" == "k3s-worker" ]]; then
    echo "6. Join K3s cluster manually:"
    echo "   curl -sfL https://get.k3s.io | K3S_URL=https://minikapserver:6443 K3S_TOKEN=<token> sh -"
fi
echo ""
echo -e "${YELLOW}To start the VM now, run: qm start $VMID${NC}"
