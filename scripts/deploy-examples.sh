#!/bin/bash
#
# Example deployment commands for different node types
# Copy and modify these commands as needed
#

set -euo pipefail

# Configuration variables - MODIFY THESE
PROXMOX_HOST="kapmox"  # or IP address
TAILSCALE_AUTH_KEY="tskey-auth-xxxxx"  # Get from Tailscale admin panel (use ephemeral keys)
SSH_KEY="$HOME/.ssh/id_rsa.pub"

echo "=========================================="
echo "Proxmox Ubuntu VM Deployment Examples"
echo "=========================================="
echo ""
echo "Before running, ensure you have:"
echo "  1. SSH access to Proxmox host ($PROXMOX_HOST)"
echo "  2. Tailscale auth key (ephemeral keys work best)"
echo "  3. SSH public key at $SSH_KEY"
echo ""
read -p "Press Enter to continue or Ctrl+C to exit..."

# Make deploy script executable
chmod +x deploy-ubuntu-vm.sh

# Read SSH public key content
if [[ ! -f "$SSH_KEY" ]]; then
    echo "Error: SSH key file not found: $SSH_KEY"
    exit 1
fi
SSH_PUBKEY=$(cat "$SSH_KEY")

echo ""
echo "=========================================="
echo "Example 1: K3s Worker Node (Brooklyn)"
echo "=========================================="
echo ""
echo "Deploying Node-BK-01 (Brooklyn K3s Worker)..."
echo ""

# Copy deployment script to Proxmox host
scp deploy-ubuntu-vm.sh root@$PROXMOX_HOST:/tmp/deploy-ubuntu-vm.sh

# Execute deployment
ssh root@$PROXMOX_HOST "bash /tmp/deploy-ubuntu-vm.sh \
  --name node-bk-01 \
  --vmid 101 \
  --ip 192.168.86.101 \
  --gateway 192.168.86.1 \
  --memory 16 \
  --cores 4 \
  --disk-size 200 \
  --storage local-lvm \
  --tailscale-key '$TAILSCALE_AUTH_KEY' \
  --ssh-pubkey '$SSH_PUBKEY' \
  --location Brooklyn \
  --node-type k3s-worker \
  --yes"

echo ""
echo "=========================================="
echo "Example 2: K3s Worker with Storage (Manhattan)"
echo "=========================================="
echo ""
echo "Deploying Node-MN-01 (Manhattan K3s Worker with Longhorn)..."
echo ""

# Copy deployment script to Proxmox host (if not already done)
scp deploy-ubuntu-vm.sh root@$PROXMOX_HOST:/tmp/deploy-ubuntu-vm.sh

# Execute deployment
ssh root@$PROXMOX_HOST "bash /tmp/deploy-ubuntu-vm.sh \
  --name node-mn-01 \
  --vmid 102 \
  --ip 192.168.50.102 \
  --gateway 192.168.50.1 \
  --dns 192.168.50.1,8.8.8.8 \
  --memory 16 \
  --cores 4 \
  --disk-size 200 \
  --storage local-lvm \
  --tailscale-key '$TAILSCALE_AUTH_KEY' \
  --ssh-pubkey '$SSH_PUBKEY' \
  --location Manhattan \
  --node-type k3s-worker \
  --longhorn-size 2048 \
  --backup-size 2048 \
  --yes"

echo ""
echo "=========================================="
echo "Example 3: Backup Node (Forest Hills)"
echo "=========================================="
echo ""
echo "Deploying Backup-Node-FH (Forest Hills Backup Node)..."
echo ""

# Copy deployment script to Proxmox host (if not already done)
scp deploy-ubuntu-vm.sh root@$PROXMOX_HOST:/tmp/deploy-ubuntu-vm.sh

# Execute deployment
ssh root@$PROXMOX_HOST "bash /tmp/deploy-ubuntu-vm.sh \
  --name backup-node-fh \
  --vmid 103 \
  --ip 192.168.50.103 \
  --gateway 192.168.50.1 \
  --dns 192.168.50.1,8.8.8.8 \
  --memory 32 \
  --cores 4 \
  --disk-size 500 \
  --storage local-lvm \
  --tailscale-key '$TAILSCALE_AUTH_KEY' \
  --ssh-pubkey '$SSH_PUBKEY' \
  --location Forest-Hills \
  --node-type backup \
  --backup-size 5000 \
  --yes"

echo ""
echo "=========================================="
echo "Example 4: Kapmox K3s Worker VM"
echo "=========================================="
echo ""
echo "Deploying K3s Worker VM on Kapmox..."
echo ""

# Copy deployment script to Kapmox
scp deploy-ubuntu-vm.sh root@kapmox:/tmp/deploy-ubuntu-vm.sh

# Execute deployment
ssh root@kapmox "bash /tmp/deploy-ubuntu-vm.sh \
  --name k3s-worker-kapmox \
  --vmid 110 \
  --ip 192.168.86.110 \
  --gateway 192.168.86.1 \
  --memory 16 \
  --cores 4 \
  --disk-size 200 \
  --storage local-lvm \
  --tailscale-key '$TAILSCALE_AUTH_KEY' \
  --ssh-pubkey '$SSH_PUBKEY' \
  --location Brooklyn \
  --node-type k3s-worker \
  --yes"

echo ""
echo "=========================================="
echo "Manual Deployment Commands"
echo "=========================================="
echo ""
echo "Copy these commands and modify as needed:"
echo ""
echo "# First, copy the deployment script to Proxmox:"
echo "scp deploy-ubuntu-vm.sh root@<PROXMOX_HOST>:/tmp/"
echo ""
echo "# Deploy basic K3s worker:"
echo "ssh root@<PROXMOX_HOST> 'bash /tmp/deploy-ubuntu-vm.sh \\"
echo "  --name <hostname> \\"
echo "  --vmid <VMID> \\"
echo "  --ip <IP_ADDRESS> \\"
echo "  --tailscale-key <AUTH_KEY> \\"
echo "  --ssh-pubkey \"<SSH_PUBLIC_KEY_CONTENT>\" \\"
echo "  --location <LOCATION> \\"
echo "  --yes'"
echo ""
echo "# Deploy with Longhorn storage (2TB):"
echo "ssh root@<PROXMOX_HOST> 'bash /tmp/deploy-ubuntu-vm.sh \\"
echo "  --name <hostname> \\"
echo "  --vmid <VMID> \\"
echo "  --ip <IP_ADDRESS> \\"
echo "  --tailscale-key <AUTH_KEY> \\"
echo "  --ssh-pubkey \"<SSH_PUBLIC_KEY_CONTENT>\" \\"
echo "  --location <LOCATION> \\"
echo "  --longhorn-size 2048 \\"
echo "  --yes'"
echo ""
echo "# Deploy with both Longhorn and Backup storage:"
echo "ssh root@<PROXMOX_HOST> 'bash /tmp/deploy-ubuntu-vm.sh \\"
echo "  --name <hostname> \\"
echo "  --vmid <VMID> \\"
echo "  --ip <IP_ADDRESS> \\"
echo "  --tailscale-key <AUTH_KEY> \\"
echo "  --ssh-pubkey \"<SSH_PUBLIC_KEY_CONTENT>\" \\"
echo "  --location <LOCATION> \\"
echo "  --longhorn-size 2048 \\"
echo "  --backup-size 2048 \\"
echo "  --yes'"
echo ""
echo "=========================================="
echo "Post-Deployment Steps"
echo "=========================================="
echo ""
echo "1. Start the VM:"
echo "   ssh root@<PROXMOX_HOST> 'qm start <VMID>'"
echo ""
echo "2. Wait 2-3 minutes for cloud-init to complete"
echo ""
echo "3. SSH into the VM:"
echo "   ssh ubuntu@<IP_ADDRESS>"
echo ""
echo "4. If you specified --longhorn-size or --backup-size,"
echo "   the storage will be automatically configured during first boot"
echo ""
echo "5. Join K3s cluster (if worker node):"
echo "   curl -sfL https://get.k3s.io | K3S_URL=https://minikapserver:6443 K3S_TOKEN=<token> sh -"
echo ""
