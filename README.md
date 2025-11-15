# Kapnode Deployments

Automated deployment system for multi-location K3s cluster with interactive TUI and Ansible automation.

## Overview

This repository contains deployment tools for managing a distributed K3s Kubernetes cluster across 5 NYC locations, connected via Tailscale mesh VPN. The system provides both an interactive Terminal UI (TUI) for on-site deployments and Ansible playbooks for remote automation.

### Architecture

- **5 Geographic Locations**: Brooklyn, Manhattan, Staten Island, Forest Hills, Kapmox
- **Distributed K3s Cluster**: Single master (Minikapserver) + worker nodes across locations
- **Tailscale Mesh VPN**: Cross-location communication and routing
- **Proxmox Hypervisor**: VM management at Brooklyn location (Kapmox)
- **Local Storage**: Per-node persistent volumes (no cross-location replication)
- **Async Backups**: Restic snapshots to 4 backup nodes + Backblaze B2

## Quick Start

### Prerequisites

- Python 3.8+ (for TUI)
- SSH access to Proxmox host and deployment targets
- Tailscale account with auth key
- Git (for version control)

### Installation

```bash
# Clone repository
git clone https://github.com/[username]/kapnode-deployments.git
cd kapnode-deployments

# Install TUI dependencies
cd tui
pip install -r requirements.txt

# Run TUI
python deploy_node.py
```

### First Deployment

1. Run the TUI: `python tui/deploy_node.py`
2. Select "Deploy New Node"
3. Enter device details (username, IP/hostname)
4. SSH key will be auto-detected or generated
5. Fill deployment parameters (VMID, hostname, location, resources)
6. Review summary and confirm
7. Watch real-time deployment progress

## Repository Structure

```
kapnode-deployments/
├── scripts/               # Bash deployment scripts
│   ├── deploy-ubuntu-vm.sh       # Main Proxmox VM deployment script
│   ├── post-install-storage.sh   # Storage configuration helper
│   ├── deploy-examples.sh        # Example deployments
│   └── homelab-info-collector.sh # System info gathering
│
├── tui/                   # Terminal UI application
│   ├── deploy_node.py            # Main TUI entry point
│   ├── components/               # Reusable UI components
│   ├── screens/                  # TUI screen layouts
│   ├── lib/                      # Business logic (SSH, config, etc.)
│   ├── requirements.txt          # Python dependencies
│   └── pyproject.toml            # Project metadata
│
├── ansible/               # Ansible playbooks (coming soon)
│   ├── playbooks/                # Deployment automation
│   ├── roles/                    # Reusable Ansible roles
│   └── inventory.yml             # Ansible inventory
│
├── docs/                  # Documentation
│   ├── DEPLOYMENT-FIXES-REPORT.md    # Bug fixes and improvements
│   ├── TUI_USER_GUIDE.md             # TUI usage guide
│   ├── GIT_WORKFLOW.md               # Git best practices
│   ├── VM-DEPLOYMENT-README.md       # VM deployment details
│   ├── REVISED-ARCHITECTURE.md       # System architecture
│   └── CURRENT-STATE-AND-PLANS.md    # Roadmap and plans
│
├── examples/              # Deployment templates
│   └── deploy-templates/         # YAML templates for common scenarios
│
├── config/                # Configuration files
│   ├── inventory.example.yml     # Example Ansible inventory
│   └── .homelab-deploy.conf.example  # Example TUI config
│
├── lib/                   # Shared libraries
│
├── .claude/               # Claude Code skills
│   └── skills/
│       └── git-workflow.md       # Version control automation
│
├── .gitignore             # Git exclusions (secrets, keys, etc.)
└── README.md              # This file
```

## Features

### Terminal UI (TUI)

- **Interactive Deployment Wizard**: Step-by-step node deployment
- **SSH Key Auto-Setup**: Smart detection and configuration
- **Real-time Progress**: Live log streaming during deployment
- **Deployment History**: Track all deployed nodes
- **Update Mode**: Connect to existing nodes via Tailscale hostname
- **Cluster Status**: View K3s node and pod status
- **Ansible-Compatible**: Writes inventory for future automation

### Deployment Scripts

- **Automated VM Creation**: Proxmox VMs with cloud-init
- **Ubuntu 24.04 LTS**: Latest LTS with automatic updates
- **Tailscale Integration**: Auto-join mesh VPN (90-day auth keys)
- **K3s Auto-Join**: Automatic cluster joining with location labels
- **Storage Configuration**: Longhorn and backup storage support
- **Multi-Network Support**: Location-specific network configs
- **UEFI Boot**: Modern boot configuration with EFI disk

### Version Control

- **Git Workflow Skill**: Automated git operations
- **Session Start**: Auto-pull latest changes
- **Session End**: Auto-commit and push with meaningful messages
- **Secret Detection**: Pre-commit validation for sensitive data
- **Conventional Commits**: Consistent commit message format

## Usage

### Deploy a New K3s Worker Node

#### Using TUI (Recommended)

```bash
python tui/deploy_node.py
# Follow interactive prompts
```

#### Using Script Directly

```bash
# Copy script to Proxmox host
scp scripts/deploy-ubuntu-vm.sh root@kapmox:/tmp/

# SSH and execute
ssh root@kapmox

./deploy-ubuntu-vm.sh \
  --name kapnode6 \
  --vmid 206 \
  --ip 192.168.86.206 \
  --gateway 192.168.86.1 \
  --dns "192.168.86.1,8.8.8.8" \
  --tailscale-key "tskey-auth-XXXX" \
  --ssh-pubkey "$(cat ~/.ssh/homelab_rsa.pub)" \
  --location Brooklyn \
  --node-type k3s-worker \
  --longhorn-size 2048 \
  --k3s-master "https://minikapserver:6443" \
  --k3s-token "K10xxx::server:xxx" \
  --yes

# Start VM
qm start 206

# Wait 2-3 minutes for cloud-init
ssh ubuntu@192.168.86.206

# After Tailscale joins, use hostname
ssh ubuntu@kapnode6
```

### Update an Existing Node

```bash
# Using TUI
python tui/deploy_node.py
# Select "Update Existing Node"
# Choose node from list (e.g., kapnode6)

# Using SSH directly (after Tailscale configured)
ssh ubuntu@kapnode6

# Update packages
sudo apt update && sudo apt upgrade -y

# Reconfigure storage
sudo ./post-install-storage.sh --longhorn-size 2048
```

### View Cluster Status

```bash
# Using TUI
python tui/deploy_node.py
# Select "Cluster Status"

# Using kubectl directly
kubectl get nodes -o wide
kubectl get pods -A
kubectl top nodes
```

## Configuration

### Tailscale Auth Key

The deployment scripts use a 90-day expiration auth key. Update in:
- TUI: Automatically uses configured key
- Scripts: Pass via `--tailscale-key` parameter

Current key (example only): `tskey-auth-XXXX`

### SSH Keys

Recommended setup:
```bash
# Generate dedicated homelab key
ssh-keygen -t ed25519 -f ~/.ssh/homelab_rsa -C "homelab-deployments"

# TUI will auto-detect this key
# Or specify manually in scripts
```

### Inventory Management

The TUI maintains an Ansible-compatible inventory at `~/.homelab/inventory.yml`:

```yaml
all:
  children:
    k3s_workers:
      hosts:
        kapnode1:
          ansible_host: 100.x.x.x  # Tailscale IP
          initial_ip: 192.168.86.201
          vmid: 201
          location: brooklyn
          deployed: 2025-11-15T10:30:00Z
```

## Network Configuration

### Location-Specific Networks

| Location | Network | Gateway | DNS |
|----------|---------|---------|-----|
| Brooklyn | 192.168.86.0/24 | 192.168.86.1 | 192.168.86.1, 8.8.8.8 |
| Manhattan | 192.168.50.0/24 | 192.168.50.1 | 192.168.50.1, 8.8.8.8 |
| Staten Island | 192.168.70.0/24 | 192.168.70.1 | 192.168.70.1, 8.8.8.8 |
| Forest Hills | 192.168.50.0/24 | 192.168.50.1 | 192.168.50.1, 8.8.8.8 |

### Tailscale Mesh

All nodes join Tailscale VPN for cross-location communication:
- **Subnet Routing**: Accept routes from other locations
- **Hostname-Based Access**: `ssh ubuntu@kapnode1` (instead of IP)
- **K3s API**: Master accessible via Tailscale IP
- **Persistent Connections**: Auto-reconnect on network changes

## Storage

### Local Volumes

Each node has local storage for persistent volumes:
- **OS Disk (scsi0)**: 200GB default (configurable)
- **Longhorn Storage (scsi1)**: Optional, 2TB+ recommended
- **Backup Storage (scsi2)**: Optional, 2TB+ for backup nodes

### Backup Strategy

- **Restic Snapshots**: Async backups every 6 hours
- **4 Backup Nodes**: Distributed across locations
- **Cloud Backup**: Backblaze B2 for off-site storage
- **RPO**: 6 hours (time between backups)
- **RTO**: <30 minutes (restoration time)

## Git Workflow

### Session Start (Automatic)

```bash
# Pull latest changes
git fetch origin
git pull --ff-only origin main

# Show recent changes
git log --oneline -5
```

### Session End (Automatic)

```bash
# Scan for secrets
# Stage changes
git add .

# Generate commit message
# Commit with conventional format
git commit -m "feat(tui): add new feature"

# Push to remote
git push origin main
```

### Manual Git Operations

```bash
# Use git-workflow skill
/git-workflow

# Or invoke directly
invoke-skill git-workflow "commit and push changes"
```

## Troubleshooting

### TUI won't start

```bash
# Check Python version
python --version  # Should be 3.8+

# Install dependencies
cd tui
pip install -r requirements.txt

# Run with verbose output
python deploy_node.py --debug
```

### SSH connection fails

```bash
# Test SSH key
ssh -i ~/.ssh/homelab_rsa ubuntu@192.168.86.201

# Copy SSH key manually
ssh-copy-id -i ~/.ssh/homelab_rsa ubuntu@192.168.86.201

# Check Tailscale status
tailscale status
```

### VM deployment fails

```bash
# Check Proxmox connection
ssh root@kapmox

# Verify storage pool
pvesm status

# Check VM logs
qm terminal 206
```

### Git operations fail

```bash
# Check repository status
git status

# Pull with rebase if diverged
git pull --rebase origin main

# Force push (only if necessary)
git push --force-with-lease origin main
```

## Development

### Adding New TUI Features

```bash
# Create feature branch
git checkout -b feature/kubectl-integration

# Make changes in tui/
# Test thoroughly

# Commit with conventional format
git commit -m "feat(tui): add kubectl cluster status view"

# Push and create PR
git push origin feature/kubectl-integration
```

### Testing Deployment Scripts

```bash
# Use --yes flag to skip confirmation
./deploy-ubuntu-vm.sh \
  --name test-node \
  --vmid 999 \
  --ip 192.168.86.250 \
  --tailscale-key "tskey-auth-test" \
  --ssh-pubkey "$(cat ~/.ssh/homelab_rsa.pub)" \
  --yes

# Verify VM created
qm status 999

# Cleanup
qm stop 999 && qm destroy 999
```

## Contributing

### Claude Code Sessions

Every Claude Code session should:

1. **Start**: Pull latest changes (automatic via git-workflow skill)
2. **Work**: Make incremental changes with frequent commits
3. **End**: Commit and push all changes (automatic via git-workflow skill)

### Commit Message Format

Follow Conventional Commits:

```
<type>(<scope>): <description>

[optional body]

Session: Claude Code YYYY-MM-DD
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Scopes: `tui`, `scripts`, `ansible`, `docs`, `config`

## Documentation

- [Deployment Fixes Report](docs/DEPLOYMENT-FIXES-REPORT.md) - Bug fixes and improvements
- [TUI User Guide](docs/TUI_USER_GUIDE.md) - Comprehensive TUI usage
- [Git Workflow](docs/GIT_WORKFLOW.md) - Version control best practices
- [VM Deployment](docs/VM-DEPLOYMENT-README.md) - Detailed deployment process
- [Architecture](docs/REVISED-ARCHITECTURE.md) - System design and constraints
- [Roadmap](docs/CURRENT-STATE-AND-PLANS.md) - Future plans and priorities

## Roadmap

### Phase 1: TUI Foundation (Current)
- ✅ Repository organization
- ✅ Git workflow skill
- ✅ Deployment script updates
- 🚧 TUI implementation
- 🚧 SSH key auto-setup
- 🚧 Deployment wizard

### Phase 2: Enhanced TUI
- ⏳ kubectl integration
- ⏳ Cluster status dashboard
- ⏳ Backup management
- ⏳ Log viewer
- ⏳ Batch deployments

### Phase 3: Ansible Automation
- ⏳ Ansible playbook development
- ⏳ Role-based deployment
- ⏳ Configuration management
- ⏳ Inventory synchronization
- ⏳ TUI calls Ansible playbooks

### Phase 4: Web UI (Future)
- ⏳ Flask/FastAPI web interface
- ⏳ Real-time WebSocket updates
- ⏳ Mobile-friendly design
- ⏳ Multi-user support
- ⏳ Remote deployment from anywhere

## License

This is a personal homelab project. Use at your own risk.

## Support

For issues, questions, or contributions:
- Review documentation in `docs/`
- Check troubleshooting section above
- Create an issue in GitHub repository
- Consult Claude Code with questions

---

**Built with**: Python, Textual, Bash, Proxmox, K3s, Tailscale, Ansible

**Maintained by**: Claude Code sessions

**Last Updated**: 2025-11-15
