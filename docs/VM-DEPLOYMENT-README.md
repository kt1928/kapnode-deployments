# Proxmox Ubuntu 24.04 VM Deployment Scripts

Automated scripts for quickly deploying Ubuntu 24.04 LTS VMs on Proxmox with pre-configured settings for K3s worker nodes.

## Files

- **`deploy-ubuntu-vm.sh`** - Main deployment script (run on Proxmox host)
- **`post-install-storage.sh`** - Storage configuration script (run inside VM after deployment)
- **`deploy-examples.sh`** - Example deployment commands
- **`VM-DEPLOYMENT-README.md`** - This file

## Prerequisites

1. **Proxmox VE** installed and accessible
2. **SSH access** to Proxmox host as root
3. **Tailscale auth key** (ephemeral key recommended)
   - Generate at: https://login.tailscale.com/admin/settings/keys
4. **SSH public key** for VM access (default: `~/.ssh/id_rsa.pub`)

## Quick Start

### 1. Deploy Basic K3s Worker Node

```bash
# On Proxmox host (ssh root@kapmox)
./deploy-ubuntu-vm.sh \
  --name node-bk-01 \
  --vmid 101 \
  --ip 192.168.86.101 \
  --tailscale-key tskey-auth-xxxxx \
  --location Brooklyn
```

### 2. Deploy with Storage Partitions

```bash
./deploy-ubuntu-vm.sh \
  --name node-mn-01 \
  --vmid 102 \
  --ip 192.168.50.102 \
  --gateway 192.168.50.1 \
  --tailscale-key tskey-auth-xxxxx \
  --location Manhattan \
  --longhorn-size 2048 \
  --backup-size 2048
```

### 3. Start VM and Wait for Cloud-Init

```bash
# Start the VM
qm start 101

# Monitor cloud-init (optional)
qm config 101 | grep cicustom
tail -f /var/log/cloud-init-output.log  # Inside VM
```

### 4. SSH into VM

```bash
# Wait 2-3 minutes for cloud-init to complete
ssh ubuntu@192.168.86.101
```

### 5. Configure Storage (if needed)

If you specified `--longhorn-size` or `--backup-size`, configure storage:

```bash
# Copy post-install-storage.sh to VM
scp post-install-storage.sh ubuntu@192.168.86.101:~/

# SSH into VM and run
ssh ubuntu@192.168.86.101
sudo ./post-install-storage.sh --longhorn-size 2048 --backup-size 2048
```

### 6. Join K3s Cluster

```bash
# Get K3s token from master node (minikapserver)
# On minikapserver:
sudo cat /var/lib/rancher/k3s/server/node-token

# On worker node:
curl -sfL https://get.k3s.io | \
  K3S_URL=https://minikapserver:6443 \
  K3S_TOKEN=<your-token> \
  sh -
```

## Script Options

### deploy-ubuntu-vm.sh

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--name` | ✅ Yes | - | VM hostname |
| `--vmid` | ✅ Yes | Auto | Proxmox VM ID (100-999) |
| `--ip` | ✅ Yes | - | Static IP address |
| `--tailscale-key` | ✅ Yes | - | Tailscale auth key |
| `--gateway` | No | 192.168.86.1 | Gateway IP |
| `--memory` | No | 16 | RAM in GB |
| `--cores` | No | 4 | CPU cores |
| `--disk-size` | No | 200 | OS disk size in GB |
| `--storage` | No | local-lvm | Proxmox storage pool |
| `--ssh-key` | No | ~/.ssh/id_rsa.pub | SSH public key file |
| `--location` | No | - | Location tag (Brooklyn, Manhattan, etc.) |
| `--node-type` | No | k3s-worker | Node type (k3s-worker or backup) |
| `--longhorn-size` | No | 0 | Longhorn storage size in GB |
| `--backup-size` | No | 0 | Backup storage size in GB |

### post-install-storage.sh

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--longhorn-size` | No | 0 | Longhorn storage size in GB |
| `--backup-size` | No | 0 | Backup storage size in GB |

## Deployment Examples

### Example 1: Basic K3s Worker (Brooklyn)
```bash
./deploy-ubuntu-vm.sh \
  --name k3s-worker-kapmox \
  --vmid 110 \
  --ip 192.168.86.110 \
  --gateway 192.168.86.1 \
  --memory 16 \
  --cores 4 \
  --disk-size 200 \
  --storage local-lvm \
  --tailscale-key tskey-auth-xxxxx \
  --ssh-key ~/.ssh/id_rsa.pub \
  --location Brooklyn \
  --node-type k3s-worker
```

### Example 2: K3s Worker with Storage (Manhattan)
```bash
./deploy-ubuntu-vm.sh \
  --name node-mn-01 \
  --vmid 102 \
  --ip 192.168.50.102 \
  --gateway 192.168.50.1 \
  --memory 16 \
  --cores 4 \
  --disk-size 200 \
  --storage local-lvm \
  --tailscale-key tskey-auth-xxxxx \
  --location Manhattan \
  --node-type k3s-worker \
  --longhorn-size 2048 \
  --backup-size 2048
```

### Example 3: Backup Node (Forest Hills)
```bash
./deploy-ubuntu-vm.sh \
  --name backup-node-fh \
  --vmid 103 \
  --ip 192.168.50.103 \
  --gateway 192.168.50.1 \
  --memory 32 \
  --cores 4 \
  --disk-size 500 \
  --storage local-lvm \
  --tailscale-key tskey-auth-xxxxx \
  --location "Forest Hills" \
  --node-type backup \
  --backup-size 5000
```

## What Gets Configured Automatically

### Cloud-Init Configuration
- ✅ Static IP address (Netplan)
- ✅ Tailscale installation and configuration
- ✅ SSH key-based authentication
- ✅ System updates
- ✅ Essential packages (curl, wget, git, vim, htop, lvm2, parted, tailscale)
- ✅ Password authentication disabled
- ✅ Root login disabled

### Storage Configuration (via post-install-storage.sh)
- ✅ Longhorn storage partition (if specified)
  - Mounted at: `/var/lib/longhorn`
  - Labeled: `longhorn`
- ✅ Backup storage partition (if specified)
  - Mounted at: `/var/lib/backups`
  - Labeled: `backups`

## Troubleshooting

### VM Won't Start
```bash
# Check VM status
qm status <VMID>

# Check VM configuration
qm config <VMID>

# Check logs
journalctl -u qemu-server@<VMID>
```

### Cloud-Init Not Working
```bash
# Check cloud-init logs inside VM
sudo cat /var/log/cloud-init-output.log
sudo cat /var/log/cloud-init.log
```

### Tailscale Not Connected
```bash
# Inside VM, check Tailscale status
tailscale status

# Re-authenticate if needed
sudo tailscale up --authkey=<your-key>
```

### Storage Not Configured
```bash
# Check available disks
lsblk

# Manually run storage script
sudo ./post-install-storage.sh --longhorn-size 2048 --backup-size 2048

# Check mounts
df -h | grep -E "longhorn|backups"
```

## Network Configuration

The script automatically configures:
- **Static IP** via Netplan
- **Gateway** routing
- **DNS servers** (gateway + 8.8.8.8)
- **Tailscale** mesh VPN connection

Adjust network settings in the script or via `--gateway` option.

## Storage Pools

Available Proxmox storage pools on Kapmox:
- `local-lvm` - LVM-thin pool (recommended, 3.5TB available)
- `local` - Directory storage (if configured)

Check available storage:
```bash
pvesm status
```

## Security Notes

1. **SSH Keys**: Script uses SSH key authentication (password auth disabled)
2. **Tailscale Auth Keys**: Use ephemeral keys that expire automatically
3. **Root Access**: Root login is disabled; use `ubuntu` user with sudo
4. **Firewall**: Consider configuring UFW inside VMs for additional security

## Next Steps After Deployment

1. ✅ VM deployed and cloud-init complete
2. ✅ Storage configured (if needed)
3. ✅ Tailscale connected
4. ⬜ Join K3s cluster
5. ⬜ Configure Longhorn (if needed)
6. ⬜ Setup monitoring (Prometheus Node Exporter)
7. ⬜ Configure backups (Restic)

## Integration with REFINED-Structure.md

This deployment script aligns with your node deployment plan:
- ✅ Ubuntu 24.04 LTS base
- ✅ Static IP configuration
- ✅ Tailscale mesh network
- ✅ Storage partitioning for Longhorn/Backups
- ✅ Ready for K3s worker deployment

## Script Location

After deployment, you can keep the script on Proxmox host:
```bash
# Recommended location on Proxmox host
/usr/local/bin/deploy-ubuntu-vm.sh

# Or in your home directory
~/scripts/deploy-ubuntu-vm.sh
```

## Contributing

To modify the script for your specific needs:
1. Edit `deploy-ubuntu-vm.sh` - Main deployment logic
2. Edit `post-install-storage.sh` - Storage partitioning logic
3. Test on a non-production VM first

## Support

For issues or questions:
1. Check Proxmox logs: `journalctl -u qemu-server@<VMID>`
2. Check cloud-init logs inside VM
3. Verify network connectivity
4. Verify storage pool availability

---

**Last Updated:** 2025-01-XX  
**Compatible with:** Proxmox VE 9.0+, Ubuntu 24.04 LTS

