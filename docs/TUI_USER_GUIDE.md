# TUI User Guide

Comprehensive guide for using the Kapnode Deployment Manager interactive Terminal UI.

## Table of Contents

- [Installation](#installation)
- [First-Time Setup](#first-time-setup)
- [Deploying a Node](#deploying-a-node)
- [Updating Nodes](#updating-nodes)
- [Viewing History](#viewing-history)
- [Troubleshooting](#troubleshooting)
- [Keyboard Shortcuts](#keyboard-shortcuts)

---

## Installation

### Prerequisites

- Python 3.8 or higher
- SSH access to Proxmox host (Kapmox)
- Tailscale account with auth key
- Git (optional, for version control)

### Install Dependencies

```bash
cd /path/to/kapnode-deployments/tui
pip install -r requirements.txt
```

### Verify Installation

```bash
python deploy_node.py --help
```

---

## First-Time Setup

### 1. Generate SSH Key (if needed)

```bash
ssh-keygen -t ed25519 -f ~/.ssh/homelab_rsa -C "homelab-deployments"
```

### 2. Copy Configuration Examples

```bash
# Copy TUI configuration
cp config/.homelab-deploy.conf.example ~/.homelab-deploy.conf

# Edit with your settings
nano ~/.homelab-deploy.conf
```

**Important**: Update `tailscale_key` and `k3s_token` in the configuration.

### 3. Create Inventory Directory

```bash
mkdir -p ~/.homelab
cp config/inventory.example.yml ~/.homelab/inventory.yml
```

### 4. Test SSH Connection to Proxmox

```bash
ssh -i ~/.ssh/homelab_rsa root@kapmox
```

---

## Deploying a Node

### Step-by-Step Deployment

#### 1. Launch TUI

```bash
python tui/deploy_node.py
```

#### 2. Select "Deploy New Node"

Press `d` or click "Deploy New Node"

#### 3. Configure SSH Connection

The TUI will auto-detect your SSH key from `~/.ssh/homelab_rsa`. If not found:

1. Enter the path to your SSH key
2. Click "Test Connection" to verify connectivity
3. If connection fails, the TUI will offer to setup SSH key authentication

**Fields:**
- **Proxmox Host**: Hostname or IP of your Proxmox server (default: `kapmox`)
- **Username**: SSH username (default: `root`)
- **SSH Key Path**: Path to your private SSH key

#### 4. Configure VM Settings

**Required Fields:**
- **Hostname**: DNS-compatible hostname (e.g., `kapnode7`)
- **VMID**: Unique VM ID between 100-999 (auto-suggested)
- **Location**: Select from dropdown (Brooklyn, Manhattan, etc.)
- **IP Address**: Static IP for the VM
- **Gateway**: Network gateway (auto-filled based on location)
- **DNS Servers**: Comma-separated DNS servers

**Example:**
```
Hostname: kapnode7
VMID: 207
Location: Brooklyn
IP: 192.168.86.207
Gateway: 192.168.86.1
DNS: 192.168.86.1,8.8.8.8
```

#### 5. Configure Resources

**Fields:**
- **CPU Cores**: Number of CPU cores (default: 4)
- **RAM (GB)**: Memory in GB (default: 16)
- **Disk Size (GB)**: OS disk size (default: 200)
- **Longhorn Size (GB)**: Optional storage disk for Longhorn (default: 0)
- **Backup Size (GB)**: Optional backup storage disk (default: 0)

**Recommendations:**
- **Standard Worker**: 4 cores, 16 GB RAM, 200 GB disk, 2048 GB Longhorn
- **Storage Worker**: 6 cores, 32 GB RAM, 200 GB disk, 8192 GB Longhorn
- **Backup Node**: 2 cores, 8 GB RAM, 100 GB disk, 4096 GB backup

#### 6. Configure K3s Settings

**Fields:**
- **Node Type**: Select `k3s-worker` or `backup`
- **K3s Master URL**: URL of K3s master (e.g., `https://minikapserver:6443`)
- **K3s Token**: Join token from master node (optional)

**Getting K3s Token:**
```bash
ssh ubuntu@minikapserver
sudo cat /var/lib/rancher/k3s/server/node-token
```

#### 7. Validate and Deploy

1. Click **"Validate"** to check all parameters
2. Review the validation summary
3. If all parameters are valid, **"Deploy"** button will be enabled
4. Click **"Deploy"** to start the deployment

#### 8. Monitor Deployment

The TUI will switch to a log viewer showing real-time deployment progress:

- ✅ Green lines: Successful operations
- ⚠️ Yellow lines: Warnings
- ❌ Red lines: Errors
- ℹ️ White lines: Information

**Typical deployment takes 5-10 minutes:**
1. Copying script to Proxmox (5 seconds)
2. Downloading Ubuntu cloud image (1-2 minutes)
3. Creating VM (30 seconds)
4. Booting VM (1-2 minutes)
5. Running cloud-init (2-3 minutes)
6. Installing K3s (1-2 minutes)
7. Joining cluster (30 seconds)

#### 9. Post-Deployment

Once deployment completes:
- Node is automatically added to inventory (`~/.homelab/inventory.yml`)
- Deployment is recorded in history
- VMID counter is incremented

**Verify Deployment:**
```bash
# SSH to new node
ssh ubuntu@kapnode7

# Or use Tailscale hostname
ssh ubuntu@kapnode7  # After Tailscale joins

# Check K3s status
kubectl get nodes
```

---

## Updating Nodes

### Package Updates

1. Select **"Update Existing Node"** from main menu
2. Filter or search for the node
3. Select the node from the table
4. Click **"Update Packages"**
5. Wait for update to complete

**What it does:**
```bash
sudo apt update
sudo apt upgrade -y
sudo apt autoremove -y
```

### Storage Reconfiguration

1. Select the node
2. Click **"Reconfigure Storage"**
3. Follow on-screen instructions

**Note**: Storage reconfiguration requires manual steps with `post-install-storage.sh`

### SSH Connection

1. Select the node
2. Click **"Connect to Node"**
3. TUI will display the SSH command
4. Run the command in your terminal

**Example:**
```bash
ssh ubuntu@kapnode7
```

---

## Viewing History

### Deployment History

1. Select **"View Deployment History"** from main menu
2. Browse the table of all deployed nodes

**Features:**
- **Filter by hostname**: Type in the search box
- **Filter by location**: Select from dropdown
- **Sort options**: By date, hostname, VMID, or location
- **View details**: Click on a row to see full node information

### Export to CSV

1. View history screen
2. Click **"Export CSV"**
3. CSV file will be saved to `~/kapnode_history_YYYYMMDD_HHMMSS.csv`

**CSV Contains:**
- Hostname
- VMID
- Location
- IP Address
- Tailscale Name
- Node Type
- Deployment Date

---

## Troubleshooting

### TUI Won't Start

**Error: ModuleNotFoundError**

```bash
cd tui
pip install -r requirements.txt
```

**Error: Permission Denied**

```bash
chmod +x deploy_node.py
```

### SSH Connection Fails

**Issue: SSH key not found**

1. Check SSH key path in configuration
2. Generate new key if needed:
   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/homelab_rsa
   ```

**Issue: Connection refused**

1. Verify Proxmox host is reachable:
   ```bash
   ping kapmox
   ```
2. Check SSH service:
   ```bash
   ssh -v root@kapmox
   ```

**Issue: Permission denied (publickey)**

1. Copy SSH key to Proxmox:
   ```bash
   ssh-copy-id -i ~/.ssh/homelab_rsa root@kapmox
   ```

### Deployment Fails

**Issue: VMID already exists**

- Change VMID to an unused number
- Check existing VMs: `qm list`

**Issue: Insufficient storage**

- Check storage availability: `pvesm status`
- Reduce disk size or free up space

**Issue: Network IP conflict**

- Verify IP is not in use: `ping 192.168.86.207`
- Use different IP address

**Issue: Tailscale key expired**

1. Generate new auth key from Tailscale admin console
2. Update in `~/.homelab-deploy.conf`

### Node Won't Join Cluster

**Issue: K3s token invalid**

1. Get fresh token from master:
   ```bash
   ssh ubuntu@minikapserver
   sudo cat /var/lib/rancher/k3s/server/node-token
   ```
2. Update in TUI or configuration

**Issue: Network connectivity**

1. Verify Tailscale is connected:
   ```bash
   ssh ubuntu@kapnode7
   tailscale status
   ```
2. Ping K3s master:
   ```bash
   ping minikapserver
   ```

**Issue: Firewall blocking**

1. Check firewall rules on both nodes
2. Ensure K3s ports are open (6443, 10250, etc.)

---

## Keyboard Shortcuts

### Global Shortcuts

| Key | Action |
|-----|--------|
| `q` | Quit application |
| `Esc` | Go back / Cancel |
| `d` | Toggle dark mode |
| `Ctrl+C` | Force quit |

### Main Menu

| Key | Action |
|-----|--------|
| `d` | Deploy New Node |
| `u` | Update Existing Node |
| `h` | View History |

### Deploy Screen

| Key | Action |
|-----|--------|
| `Tab` | Navigate between fields |
| `Enter` | Confirm selection |
| `Ctrl+D` | Start deployment |

### Update Screen

| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate table |
| `Enter` | Select node |
| `r` | Refresh list |

### History Screen

| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate table |
| `r` | Refresh data |

---

## Advanced Features

### Debug Mode

Run TUI in debug mode for verbose output:

```bash
python deploy_node.py --debug
```

### Custom Configuration

Create custom deployment templates in `examples/deploy-templates/`:

```yaml
deployment:
  type: custom
  # Your custom configuration
```

### Batch Deployments

For deploying multiple nodes, use the deployment templates with a script:

```bash
for template in examples/deploy-templates/*.yml; do
    # Parse template and deploy
    # (Future feature)
done
```

### Integration with Ansible

The TUI maintains an Ansible-compatible inventory:

```bash
ansible-playbook -i ~/.homelab/inventory.yml playbook.yml
```

---

## Best Practices

1. **Always test SSH connection** before deploying
2. **Use sequential VMIDs** for easier management
3. **Document custom configurations** in node metadata
4. **Export deployment history** regularly as backup
5. **Keep Tailscale key** rotated (90-day expiry)
6. **Monitor deployment logs** for any warnings
7. **Verify cluster health** after each deployment

---

## Getting Help

- Review this guide
- Check `README.md` for overview
- Read `docs/DEPLOYMENT-FIXES-REPORT.md` for known issues
- Examine deployment templates in `examples/deploy-templates/`

---

**Last Updated**: 2025-11-19
**Version**: 1.0.0
**Maintained by**: Kapnode Team
