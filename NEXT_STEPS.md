# Next Steps for Kapnode Deployments

This document outlines the immediate next steps to continue development of the kapnode-deployments TUI and automation system.

---

## Phase 1: Repository Setup ✅ COMPLETED

- ✅ Repository structure organized
- ✅ Git initialized with comprehensive .gitignore
- ✅ Version control skill created (.claude/skills/git-workflow.md)
- ✅ Main README.md written
- ✅ TUI project foundation (requirements.txt, pyproject.toml)
- ✅ Tailscale key reference updated in deployment scripts
- ✅ Initial commit created

---

## IMMEDIATE: Push to GitHub

### 1. Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `kapnode-deployments`
3. Description: "Automated deployment system for multi-location K3s cluster with interactive TUI"
4. Visibility: Private (recommended) or Public
5. **DO NOT** initialize with README, .gitignore, or license (we already have these)
6. Click "Create repository"

### 2. Push Local Repository to GitHub

```bash
cd "/Users/kappy/Documents/Projects/Home Lab/node-system"

# Add remote (replace [your-username] with your GitHub username)
git remote add origin https://github.com/[your-username]/kapnode-deployments.git

# Verify remote was added
git remote -v

# Push to GitHub
git push -u origin main

# Verify push successful
git log --oneline
```

### 3. Verify on GitHub

- Navigate to your repository on GitHub
- Confirm all files are present
- Check that .gitignore is working (no secrets/keys visible)
- Review README.md renders correctly

---

## Phase 2: TUI Development (Start Next Session)

### Priority 1: Core Business Logic

Create the foundational libraries that the TUI will use:

#### A. SSH Manager (`tui/lib/ssh_manager.py`)

**Purpose**: Handle SSH connections, key detection, and remote command execution

**Features**:
- Auto-detect SSH keys (~/.ssh/homelab_rsa, ~/.ssh/id_ed25519, ~/.ssh/id_rsa)
- Generate SSH key if none found
- Test SSH connection to target
- Execute ssh-copy-id for first-time setup
- Run remote commands with output streaming
- SCP file transfers

**Key Functions**:
```python
detect_ssh_key() -> Path
generate_ssh_key(path: Path) -> bool
test_connection(host: str, user: str, key: Path) -> bool
setup_ssh_key(host: str, user: str, key: Path, password: str) -> bool
execute_command(host: str, user: str, command: str) -> tuple[str, str, int]
scp_file(local_path: Path, remote_path: str, host: str, user: str) -> bool
```

#### B. Inventory Manager (`tui/lib/inventory.py`)

**Purpose**: Read/write Ansible-compatible inventory files

**Features**:
- Load inventory from ~/.homelab/inventory.yml
- Parse Ansible YAML format
- Add new nodes to inventory
- Update existing node information
- Query nodes by location, type, or name
- Save inventory with proper formatting

**Key Functions**:
```python
load_inventory(path: Path) -> dict
save_inventory(data: dict, path: Path) -> bool
add_node(hostname: str, ip: str, vmid: int, location: str, **kwargs) -> bool
get_node(hostname: str) -> dict | None
list_nodes(location: str = None, node_type: str = None) -> list[dict]
update_node(hostname: str, **kwargs) -> bool
```

#### C. Configuration Manager (`tui/lib/config_manager.py`)

**Purpose**: Manage TUI configuration and deployment history

**Features**:
- Load/save TUI config from ~/.homelab-deploy.conf
- Track last used VMID (for auto-increment)
- Store location defaults (network, gateway, DNS)
- Remember user preferences (SSH key path, Proxmox host, etc.)
- Deployment history tracking

**Key Functions**:
```python
load_config() -> dict
save_config(config: dict) -> bool
get_next_vmid() -> int
increment_vmid() -> int
get_location_defaults(location: str) -> dict
set_preference(key: str, value: any) -> bool
get_deployment_history(limit: int = 10) -> list[dict]
```

#### D. Script Executor (`tui/lib/script_executor.py`)

**Purpose**: Execute deployment scripts with live output streaming

**Features**:
- SCP deploy-ubuntu-vm.sh to Proxmox host
- Build command with proper parameters
- Execute via SSH with real-time output capture
- Parse output for errors and progress
- Handle script failures gracefully
- Return structured results

**Key Functions**:
```python
prepare_deployment(params: dict) -> str  # Build command string
copy_script_to_host(script: Path, host: str, user: str) -> bool
execute_deployment(command: str, host: str, user: str) -> Iterator[str]
parse_output(line: str) -> dict  # Extract progress, errors, etc.
wait_for_completion(process) -> tuple[bool, str]
```

#### E. Validators (`tui/lib/validators.py`)

**Purpose**: Input validation for deployment parameters

**Features**:
- Validate IP addresses (IPv4 format)
- Validate VMID (numeric, range 100-999)
- Validate hostname (DNS-compatible)
- Validate resource values (cores, RAM, disk)
- Validate Tailscale key format
- Network configuration validation

**Key Functions**:
```python
validate_ip(ip: str) -> bool
validate_vmid(vmid: int) -> bool
validate_hostname(hostname: str) -> bool
validate_resources(cores: int, ram: int, disk: int) -> bool
validate_tailscale_key(key: str) -> bool
validate_network_config(ip: str, gateway: str, netmask: str) -> bool
```

---

### Priority 2: TUI Screens

Create the interactive screens users will navigate:

#### A. Main Menu (`tui/screens/main_menu.py`)

**Purpose**: Entry point with navigation options

**Features**:
- "Deploy New Node" → Deploy Screen
- "Update Existing Node" → Update Screen
- "View Deployment History" → History Screen
- "Cluster Status" → Status Screen (future)
- "Quit"
- Show current git branch and sync status

#### B. Deploy Screen (`tui/screens/deploy_screen.py`)

**Purpose**: Interactive deployment wizard

**Workflow**:
1. Device Connection Setup
   - Prompt for username (default: ubuntu)
   - Prompt for hostname/IP
   - Auto-detect SSH key (or prompt)
   - Test SSH connection
   - If fails: offer to setup SSH key

2. VM Configuration
   - VMID (suggest next available)
   - Hostname
   - Location (dropdown: Brooklyn, Manhattan, etc.)
   - IP Address (with location-based validation)
   - Gateway (auto-fill from location)
   - DNS (auto-fill from location)

3. Resources
   - CPU Cores (default: 4)
   - RAM GB (default: 16)
   - Disk Size GB (default: 200)
   - Longhorn Size GB (optional, default: 0)
   - Backup Size GB (optional, default: 0)

4. K3s Configuration
   - Node Type (worker/backup)
   - K3s Master URL (optional)
   - K3s Token (optional)

5. Review & Deploy
   - Show summary of all parameters
   - Confirm deployment
   - Show real-time progress
   - Save to inventory on success

#### C. Update Screen (`tui/screens/update_screen.py`)

**Purpose**: Update existing nodes

**Features**:
- List known nodes from inventory
- Filter by location or type
- Select node (shows Tailscale hostname if available)
- Connect via Tailscale hostname or IP
- Options:
  - Update packages (apt update/upgrade)
  - Reconfigure storage
  - Update K3s configuration
  - Run custom commands

#### D. History Screen (`tui/screens/history_screen.py`)

**Purpose**: View deployment history

**Features**:
- Table of deployed nodes
- Columns: Hostname, VMID, Location, IP, Tailscale Name, Deployed Date
- Filter by location
- Sort by date, hostname, VMID
- Click to view full details
- Export to CSV

---

### Priority 3: TUI Components

Create reusable UI widgets:

#### A. Deployment Form (`tui/components/deployment_form.py`)

**Purpose**: Reusable form for deployment parameters

**Features**:
- Text inputs with validation
- Dropdowns for locations, node types
- Number inputs for resources
- Smart defaults based on config
- Real-time validation feedback
- "Advanced Options" collapsible section

#### B. Node Selector (`tui/components/node_selector.py`)

**Purpose**: Select node from inventory

**Features**:
- Searchable list of nodes
- Display: hostname, location, IP, Tailscale status
- Filter by location or type
- Keyboard navigation (arrow keys, vim bindings)
- Double-click or Enter to select

#### C. Log Viewer (`tui/components/log_viewer.py`)

**Purpose**: Real-time deployment log display

**Features**:
- Stream output from deployment script
- Syntax highlighting (errors in red, success in green)
- Auto-scroll to bottom
- Pause/resume scrolling
- Copy to clipboard
- Save to file
- Search in logs

#### D. Progress Indicator (`tui/components/progress.py`)

**Purpose**: Show deployment progress

**Features**:
- Progress bar with percentage
- Stage indicators (Downloading image, Creating VM, etc.)
- Estimated time remaining
- Cancel button
- Error state display

---

### Priority 4: Main Entry Point

#### `tui/deploy_node.py`

**Purpose**: Application entry point

**Structure**:
```python
from textual.app import App
from screens.main_menu import MainMenu

class KapnodeDeployApp(App):
    """Interactive TUI for kapnode deployments"""

    CSS_PATH = "styles.css"
    TITLE = "Kapnode Deployment Manager"

    def on_mount(self) -> None:
        """Load main menu on startup"""
        self.push_screen(MainMenu())

def main():
    """Entry point for deploy-node command"""
    app = KapnodeDeployApp()
    app.run()

if __name__ == "__main__":
    main()
```

**Features**:
- Initialize Textual app
- Load configuration
- Check git sync status
- Show main menu
- Handle global keyboard shortcuts (Ctrl+C to quit, etc.)

---

## Phase 3: Configuration Examples

### A. Create `config/inventory.example.yml`

Example Ansible inventory with multiple locations:

```yaml
all:
  children:
    proxmox_hosts:
      hosts:
        kapmox:
          ansible_host: 192.168.86.100
          ansible_user: root
          location: brooklyn

    k3s_masters:
      hosts:
        minikapserver:
          ansible_host: 100.x.x.x  # Tailscale IP
          initial_ip: 192.168.50.10
          location: forest_hills

    k3s_workers:
      hosts:
        kapnode1:
          ansible_host: 100.x.x.x
          initial_ip: 192.168.86.201
          vmid: 201
          location: brooklyn
          deployed: 2025-11-15T10:30:00Z
          tailscale_name: kapnode1
          node_type: k3s-worker
          resources:
            cores: 4
            ram_gb: 16
            disk_gb: 200
            longhorn_gb: 2048
```

### B. Create `config/.homelab-deploy.conf.example`

Example TUI configuration:

```json
{
  "last_vmid": 205,
  "ssh_key": "~/.ssh/homelab_rsa",
  "proxmox_host": "kapmox",
  "proxmox_user": "root",
  "tailscale_key": "tskey-auth-XXXX",
  "locations": {
    "brooklyn": {
      "network": "192.168.86.0/24",
      "gateway": "192.168.86.1",
      "dns": "192.168.86.1,8.8.8.8"
    },
    "manhattan": {
      "network": "192.168.50.0/24",
      "gateway": "192.168.50.1",
      "dns": "192.168.50.1,8.8.8.8"
    },
    "staten_island": {
      "network": "192.168.70.0/24",
      "gateway": "192.168.70.1",
      "dns": "192.168.70.1,8.8.8.8"
    },
    "forest_hills": {
      "network": "192.168.50.0/24",
      "gateway": "192.168.50.1",
      "dns": "192.168.50.1,8.8.8.8"
    }
  },
  "k3s_master": "https://minikapserver:6443",
  "defaults": {
    "cores": 4,
    "ram_gb": 16,
    "disk_gb": 200,
    "node_type": "k3s-worker"
  }
}
```

---

## Phase 4: Deployment Templates

Create example deployment scenarios in `examples/deploy-templates/`:

### A. `k3s-worker.yml`

Standard K3s worker node deployment

### B. `backup-node.yml`

Backup storage node with large disk

### C. `storage-worker.yml`

Worker with Longhorn storage enabled

### D. `multi-location-cluster.yml`

Complete multi-location deployment (all 5 locations)

---

## Phase 5: Documentation Updates

### A. Create `docs/TUI_USER_GUIDE.md`

Comprehensive guide:
- Installation instructions
- First-time setup
- Deploying a node (step-by-step with screenshots)
- Updating nodes
- Viewing history
- Troubleshooting common issues
- Keyboard shortcuts reference

### B. Create `docs/GIT_WORKFLOW.md`

Version control guide:
- How the git-workflow skill works
- Manual git operations
- Commit message conventions
- Branching strategy
- Handling conflicts

### C. Update `docs/DEPLOYMENT-FIXES-REPORT.md`

Add new section:
- TUI Implementation
- Features added
- Integration with existing scripts
- Benefits over manual deployment

---

## Testing Checklist

Before considering Phase 2 complete:

### Unit Tests
- [ ] SSH key detection works
- [ ] Inventory loading/saving works
- [ ] Configuration management works
- [ ] Input validation works
- [ ] Script execution works

### Integration Tests
- [ ] End-to-end deployment (local test)
- [ ] SSH key auto-setup
- [ ] Inventory updates correctly
- [ ] Tailscale hostname connection works
- [ ] Error handling graceful

### User Acceptance Tests
- [ ] TUI is responsive and intuitive
- [ ] Forms validate input properly
- [ ] Real-time logs display correctly
- [ ] Deployment completes successfully
- [ ] Update mode works as expected

---

## Development Environment Setup

### Install Dependencies

```bash
cd tui
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
pip install -r requirements.txt
```

### Run TUI in Development

```bash
python deploy_node.py
```

### Run Tests

```bash
pytest tests/ -v
```

### Code Formatting

```bash
black .
flake8 .
mypy .
```

---

## Estimated Timeline

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| Phase 2A | Business Logic Libraries | 2-3 days |
| Phase 2B | TUI Screens | 2-3 days |
| Phase 2C | TUI Components | 1-2 days |
| Phase 2D | Main Entry Point | 1 day |
| Phase 3 | Configuration Examples | 1 day |
| Phase 4 | Deployment Templates | 1 day |
| Phase 5 | Documentation | 1-2 days |
| **Total** | | **9-13 days** |

---

## Success Criteria

TUI Phase 2 is complete when:

- ✅ User can run `python tui/deploy_node.py` and see main menu
- ✅ User can deploy a new node with interactive wizard
- ✅ SSH key is auto-detected or setup automatically
- ✅ Deployment executes deploy-ubuntu-vm.sh successfully
- ✅ Real-time logs display during deployment
- ✅ Node is added to inventory automatically
- ✅ User can update existing node via Tailscale hostname
- ✅ Deployment history is viewable
- ✅ All inputs are validated with helpful errors
- ✅ Documentation is complete and accurate

---

## Commands Reference

### Git Operations

```bash
# Session start (pull latest)
git fetch origin
git pull --ff-only origin main

# During session (commit frequently)
git add .
git commit -m "feat(tui): add ssh manager with key detection"

# Session end (push changes)
git push origin main
```

### TUI Development

```bash
# Activate virtual environment
cd tui && source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run TUI
python deploy_node.py

# Run with debug mode
python deploy_node.py --debug

# Run tests
pytest tests/ -v --cov

# Format code
black . && flake8 .
```

### Testing Deployment

```bash
# Test SSH connection
ssh -i ~/.ssh/homelab_rsa ubuntu@192.168.86.201

# Test script directly
cd scripts
./deploy-ubuntu-vm.sh --help

# Test inventory loading
python -c "from tui.lib.inventory import load_inventory; print(load_inventory('~/.homelab/inventory.yml'))"
```

---

## Notes

- **Tailscale Auth Key**: Set via environment variable `TAILSCALE_AUTH_KEY` (never commit keys to version control)
- **SSH Key**: Recommended to use dedicated `~/.ssh/homelab_rsa` for deployments
- **Inventory Location**: `~/.homelab/inventory.yml` (Ansible-compatible)
- **Config Location**: `~/.homelab-deploy.conf` (TUI-specific)
- **Git Workflow**: Use `/git-workflow` skill for automatic version control

---

**Last Updated**: 2025-11-15
**Current Phase**: Phase 1 Complete, Ready for Phase 2
**Next Session**: Push to GitHub, then start TUI development
