"""Deploy Screen - Interactive deployment wizard."""

from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Header, Footer, Button, Input, Static, Label, Select
from textual import on, work
from rich.text import Text

from ..lib.ssh_manager import SSHManager
from ..lib.inventory import InventoryManager
from ..lib.config_manager import ConfigManager
from ..lib.script_executor import ScriptExecutor
from ..lib.validators import Validators


class DeployScreen(Screen):
    """Interactive deployment wizard screen."""

    BINDINGS = [
        ("escape", "back", "Back"),
        ("ctrl+d", "deploy", "Deploy"),
    ]

    CSS = """
    DeployScreen {
        layout: vertical;
    }

    #deploy-container {
        width: 100%;
        height: 100%;
        overflow-y: auto;
    }

    .section {
        border: solid $primary;
        margin: 1 2;
        padding: 1 2;
    }

    .section-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    .form-field {
        margin: 0 0 1 0;
    }

    .field-label {
        width: 30%;
        padding: 1 1;
    }

    .field-input {
        width: 70%;
    }

    #button-container {
        height: 5;
        align: center middle;
        margin: 1 2;
    }

    #button-container Button {
        margin: 0 2;
    }

    .error {
        color: $error;
        text-style: bold;
    }

    .success {
        color: $success;
        text-style: bold;
    }
    """

    def __init__(self):
        super().__init__()
        self.ssh_manager = SSHManager()
        self.inventory = InventoryManager()
        self.config = ConfigManager()
        self.executor = ScriptExecutor(self.ssh_manager)

        self.config.load_config()
        self.inventory.load_inventory()

    def compose(self) -> ComposeResult:
        """Create child widgets for deploy screen."""
        yield Header()

        with VerticalScroll(id="deploy-container"):
            # Section 1: SSH Connection
            with Container(classes="section"):
                yield Static("1. Device Connection", classes="section-title")
                with Horizontal(classes="form-field"):
                    yield Label("Proxmox Host:", classes="field-label")
                    yield Input(
                        value=self.config.get_preference("proxmox_host", "kapmox"),
                        placeholder="hostname or IP",
                        id="input-host",
                        classes="field-input"
                    )
                with Horizontal(classes="form-field"):
                    yield Label("Username:", classes="field-label")
                    yield Input(
                        value=self.config.get_preference("proxmox_user", "root"),
                        placeholder="root",
                        id="input-user",
                        classes="field-input"
                    )
                with Horizontal(classes="form-field"):
                    yield Label("SSH Key Path:", classes="field-label")
                    yield Input(
                        value=self.config.get_preference("ssh_key", "~/.ssh/homelab_rsa"),
                        placeholder="~/.ssh/homelab_rsa",
                        id="input-ssh-key",
                        classes="field-input"
                    )
                yield Static("", id="ssh-status")
                yield Button("Test Connection", id="btn-test-ssh")

            # Section 2: VM Configuration
            with Container(classes="section"):
                yield Static("2. VM Configuration", classes="section-title")
                with Horizontal(classes="form-field"):
                    yield Label("Hostname:", classes="field-label")
                    yield Input(
                        placeholder="kapnode7",
                        id="input-hostname",
                        classes="field-input"
                    )
                with Horizontal(classes="form-field"):
                    yield Label("VMID:", classes="field-label")
                    yield Input(
                        value=str(self.inventory.get_next_vmid()),
                        placeholder="207",
                        id="input-vmid",
                        classes="field-input"
                    )
                with Horizontal(classes="form-field"):
                    yield Label("Location:", classes="field-label")
                    yield Select(
                        options=[
                            ("Brooklyn", "brooklyn"),
                            ("Manhattan", "manhattan"),
                            ("Staten Island", "staten_island"),
                            ("Forest Hills", "forest_hills"),
                        ],
                        id="select-location",
                        classes="field-input"
                    )
                with Horizontal(classes="form-field"):
                    yield Label("IP Address:", classes="field-label")
                    yield Input(
                        placeholder="192.168.86.207",
                        id="input-ip",
                        classes="field-input"
                    )
                with Horizontal(classes="form-field"):
                    yield Label("Gateway:", classes="field-label")
                    yield Input(
                        value="192.168.86.1",
                        placeholder="192.168.86.1",
                        id="input-gateway",
                        classes="field-input"
                    )
                with Horizontal(classes="form-field"):
                    yield Label("DNS Servers:", classes="field-label")
                    yield Input(
                        value="192.168.86.1,8.8.8.8",
                        placeholder="192.168.86.1,8.8.8.8",
                        id="input-dns",
                        classes="field-input"
                    )

            # Section 3: Resources
            with Container(classes="section"):
                yield Static("3. Resources", classes="section-title")
                with Horizontal(classes="form-field"):
                    yield Label("CPU Cores:", classes="field-label")
                    yield Input(
                        value=str(self.config.get_preference("defaults.cores", 4)),
                        placeholder="4",
                        id="input-cores",
                        classes="field-input"
                    )
                with Horizontal(classes="form-field"):
                    yield Label("RAM (GB):", classes="field-label")
                    yield Input(
                        value=str(self.config.get_preference("defaults.ram_gb", 16)),
                        placeholder="16",
                        id="input-memory",
                        classes="field-input"
                    )
                with Horizontal(classes="form-field"):
                    yield Label("Disk Size (GB):", classes="field-label")
                    yield Input(
                        value=str(self.config.get_preference("defaults.disk_gb", 200)),
                        placeholder="200",
                        id="input-disk",
                        classes="field-input"
                    )
                with Horizontal(classes="form-field"):
                    yield Label("Longhorn Size (GB):", classes="field-label")
                    yield Input(
                        value="0",
                        placeholder="0 (disabled)",
                        id="input-longhorn",
                        classes="field-input"
                    )
                with Horizontal(classes="form-field"):
                    yield Label("Backup Size (GB):", classes="field-label")
                    yield Input(
                        value="0",
                        placeholder="0 (disabled)",
                        id="input-backup",
                        classes="field-input"
                    )

            # Section 4: K3s Configuration
            with Container(classes="section"):
                yield Static("4. K3s Configuration", classes="section-title")
                with Horizontal(classes="form-field"):
                    yield Label("Node Type:", classes="field-label")
                    yield Select(
                        options=[
                            ("K3s Worker", "k3s-worker"),
                            ("Backup Node", "backup"),
                        ],
                        value="k3s-worker",
                        id="select-node-type",
                        classes="field-input"
                    )
                with Horizontal(classes="form-field"):
                    yield Label("K3s Master URL:", classes="field-label")
                    yield Input(
                        value=self.config.get_preference("k3s_master", ""),
                        placeholder="https://minikapserver:6443",
                        id="input-k3s-master",
                        classes="field-input"
                    )
                with Horizontal(classes="form-field"):
                    yield Label("K3s Token:", classes="field-label")
                    yield Input(
                        value=self.config.get_preference("k3s_token", ""),
                        placeholder="K10xxx::server:xxx",
                        password=True,
                        id="input-k3s-token",
                        classes="field-input"
                    )

            # Section 5: Review & Deploy
            with Container(classes="section"):
                yield Static("5. Review & Deploy", classes="section-title")
                yield Static("", id="validation-summary")

            # Action buttons
            with Horizontal(id="button-container"):
                yield Button("Validate", id="btn-validate", variant="primary")
                yield Button("Deploy", id="btn-deploy", variant="success", disabled=True)
                yield Button("Cancel", id="btn-cancel", variant="error")

        yield Footer()

    @on(Select.Changed, "#select-location")
    def on_location_change(self, event: Select.Changed) -> None:
        """Update network defaults when location changes."""
        location = event.value
        defaults = self.config.get_location_defaults(location)

        self.query_one("#input-gateway", Input).value = defaults.get("gateway", "")
        self.query_one("#input-dns", Input).value = defaults.get("dns", "")

    @on(Button.Pressed, "#btn-test-ssh")
    def test_ssh_connection(self) -> None:
        """Test SSH connection to Proxmox host."""
        host = self.query_one("#input-host", Input).value
        user = self.query_one("#input-user", Input).value
        key_path = Path(self.query_one("#input-ssh-key", Input).value).expanduser()

        status_widget = self.query_one("#ssh-status", Static)

        if not key_path.exists():
            status_widget.update(Text("❌ SSH key not found", style="bold red"))
            return

        # Test connection
        if self.ssh_manager.test_connection(host, user, key_path):
            status_widget.update(Text("✓ Connection successful", style="bold green"))
        else:
            status_widget.update(Text("❌ Connection failed", style="bold red"))

    @on(Button.Pressed, "#btn-validate")
    def validate_deployment(self) -> None:
        """Validate all deployment parameters."""
        params = self._collect_parameters()

        valid, errors = Validators.validate_all_deployment_params(params)

        summary_widget = self.query_one("#validation-summary", Static)
        deploy_button = self.query_one("#btn-deploy", Button)

        if valid:
            summary = Text()
            summary.append("✓ All parameters valid\n\n", style="bold green")
            summary.append(f"Hostname: {params['name']}\n")
            summary.append(f"VMID: {params['vmid']}\n")
            summary.append(f"IP: {params['ip']}\n")
            summary.append(f"Location: {params['location']}\n")
            summary.append(f"Resources: {params['cores']} cores, {params['memory']} GB RAM, {params['disk_size']} GB disk\n")

            summary_widget.update(summary)
            deploy_button.disabled = False
        else:
            error_text = Text()
            error_text.append("❌ Validation errors:\n\n", style="bold red")
            for error in errors:
                error_text.append(f"  • {error}\n", style="red")

            summary_widget.update(error_text)
            deploy_button.disabled = True

    @on(Button.Pressed, "#btn-deploy")
    @work
    async def start_deployment(self) -> None:
        """Start the deployment process."""
        params = self._collect_parameters()

        # Switch to log viewer screen
        from ..components.log_viewer import LogViewerScreen

        await self.app.push_screen(LogViewerScreen(params, self))

    @on(Button.Pressed, "#btn-cancel")
    def action_back(self) -> None:
        """Go back to main menu."""
        self.app.pop_screen()

    def _collect_parameters(self) -> dict:
        """Collect all parameters from form inputs."""
        return {
            "name": self.query_one("#input-hostname", Input).value,
            "vmid": int(self.query_one("#input-vmid", Input).value or 0),
            "ip": self.query_one("#input-ip", Input).value,
            "gateway": self.query_one("#input-gateway", Input).value,
            "dns": self.query_one("#input-dns", Input).value,
            "memory": int(self.query_one("#input-memory", Input).value or 0),
            "cores": int(self.query_one("#input-cores", Input).value or 0),
            "disk_size": int(self.query_one("#input-disk", Input).value or 0),
            "longhorn_size": int(self.query_one("#input-longhorn", Input).value or 0),
            "backup_size": int(self.query_one("#input-backup", Input).value or 0),
            "location": self.query_one("#select-location", Select).value,
            "node_type": self.query_one("#select-node-type", Select).value,
            "k3s_master": self.query_one("#input-k3s-master", Input).value,
            "k3s_token": self.query_one("#input-k3s-token", Input).value,
            "tailscale_key": self.config.get_preference("tailscale_key", ""),
            "ssh_pubkey": self.ssh_manager.get_public_key(
                Path(self.query_one("#input-ssh-key", Input).value).expanduser()
            ),
            "storage": self.config.get_preference("defaults.storage", "local-lvm"),
            "network": self.config.get_location_defaults(
                self.query_one("#select-location", Select).value
            ).get("network", "192.168.86.0/24"),
            "proxmox_host": self.query_one("#input-host", Input).value,
            "proxmox_user": self.query_one("#input-user", Input).value,
            "ssh_key_path": self.query_one("#input-ssh-key", Input).value,
        }
