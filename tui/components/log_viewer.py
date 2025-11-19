"""Log Viewer - Real-time deployment log display."""

from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.screen import Screen
from textual.widgets import Header, Footer, Button, Static, RichLog
from textual import on, work
from rich.text import Text

from ..lib.script_executor import ScriptExecutor
from ..lib.ssh_manager import SSHManager
from ..lib.inventory import InventoryManager
from ..lib.config_manager import ConfigManager


class LogViewerScreen(Screen):
    """Screen for viewing real-time deployment logs."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("s", "save", "Save Log"),
    ]

    CSS = """
    LogViewerScreen {
        layout: vertical;
    }

    #log-container {
        height: 1fr;
        border: solid $primary;
        margin: 1 2;
    }

    #log-display {
        height: 100%;
    }

    #status-bar {
        height: 3;
        background: $surface;
        border: solid $primary;
        margin: 0 2;
        padding: 1 2;
    }

    #button-container {
        height: 5;
        align: center middle;
        margin: 1 2;
    }

    #button-container Button {
        margin: 0 2;
    }
    """

    def __init__(self, deployment_params: dict, parent_screen):
        super().__init__()
        self.params = deployment_params
        self.parent_screen = parent_screen
        self.executor = ScriptExecutor()
        self.ssh_manager = SSHManager()
        self.inventory = InventoryManager()
        self.config = ConfigManager()

        self.inventory.load_inventory()
        self.config.load_config()

        self.deployment_success = False
        self.log_lines = []

    def compose(self) -> ComposeResult:
        """Create child widgets for log viewer."""
        yield Header()

        with Container(id="log-container"):
            yield RichLog(id="log-display", wrap=True, highlight=True, markup=True)

        yield Static("Preparing deployment...", id="status-bar")

        with Container(id="button-container"):
            yield Button("Save Log", id="btn-save", disabled=True)
            yield Button("Close", id="btn-close", variant="error", disabled=True)

        yield Footer()

    def _safe_write_log(self, message: str) -> None:
        """Safely write to log from worker thread."""
        self.app.call_from_thread(
            self.query_one("#log-display", RichLog).write,
            message
        )

    def _safe_update_status(self, message: str) -> None:
        """Safely update status bar from worker thread."""
        self.app.call_from_thread(
            self.query_one("#status-bar", Static).update,
            message
        )

    def _safe_enable_button(self, button_id: str) -> None:
        """Safely enable button from worker thread."""
        def enable():
            self.query_one(button_id, Button).disabled = False
        self.app.call_from_thread(enable)

    @work
    async def on_mount(self) -> None:
        """Start deployment when screen mounts (thread-safe)."""
        # Log deployment parameters
        self._safe_write_log("=== Kapnode Deployment Starting ===")
        self._safe_write_log(f"Hostname: {self.params['name']}")
        self._safe_write_log(f"VMID: {self.params['vmid']}")
        self._safe_write_log(f"IP: {self.params['ip']}")
        self._safe_write_log(f"Location: {self.params['location']}")
        self._safe_write_log("=" * 40)
        self._safe_write_log("")

        # Step 1: Copy script to Proxmox host
        self._safe_update_status("Step 1/3: Copying deployment script...")
        self._safe_write_log("[yellow]Copying deployment script to Proxmox host...[/yellow]")

        script_path = Path(__file__).parent.parent.parent / "scripts" / "deploy-ubuntu-vm.sh"
        ssh_key = Path(self.params['ssh_key_path']).expanduser()

        success = self.executor.copy_script_to_host(
            script=script_path,
            host=self.params['proxmox_host'],
            user=self.params['proxmox_user'],
            key=ssh_key
        )

        if not success:
            self._safe_write_log("[bold red]✗ Failed to copy script to Proxmox host[/bold red]")
            self._safe_update_status("Deployment failed: Could not copy script")
            self._safe_enable_button("#btn-close")
            return

        self._safe_write_log("[green]✓ Script copied successfully[/green]")
        self._safe_write_log("")

        # Step 2: Prepare command
        self._safe_update_status("Step 2/3: Preparing deployment command...")
        self._safe_write_log("[yellow]Building deployment command...[/yellow]")

        command = self.executor.prepare_deployment(self.params)
        self._safe_write_log(f"Command: {command[:100]}...")
        self._safe_write_log("")

        # Step 3: Execute deployment
        self._safe_update_status("Step 3/3: Executing deployment...")
        self._safe_write_log("[yellow]Starting VM deployment...[/yellow]")
        self._safe_write_log("")

        try:
            output_iterator = self.executor.execute_deployment(
                command=command,
                host=self.params['proxmox_host'],
                user=self.params['proxmox_user'],
                key=ssh_key
            )

            for line in output_iterator:
                # Parse output
                parsed = self.executor.parse_output(line)

                # Store log line
                self.log_lines.append(line)

                # Color code based on type
                if parsed["type"] == "error":
                    self._safe_write_log(f"[bold red]{line}[/bold red]")
                elif parsed["type"] == "warning":
                    self._safe_write_log(f"[yellow]{line}[/yellow]")
                elif parsed["type"] == "success":
                    self._safe_write_log(f"[green]{line}[/green]")
                else:
                    self._safe_write_log(line)

                # Update status bar with stage info
                if parsed["stage"]:
                    self._safe_update_status(f"Stage: {parsed['stage']}")

            # Deployment completed
            if "error" not in "\n".join(self.log_lines).lower():
                self._safe_write_log("")
                self._safe_write_log("[bold green]✓ Deployment completed successfully![/bold green]")
                self._safe_update_status("Deployment successful!")
                self.deployment_success = True

                # Add to inventory
                self._add_to_inventory()

            else:
                self._safe_write_log("")
                self._safe_write_log("[bold red]✗ Deployment completed with errors[/bold red]")
                self._safe_update_status("Deployment failed")

        except Exception as e:
            self._safe_write_log("")
            self._safe_write_log(f"[bold red]✗ Deployment error: {str(e)}[/bold red]")
            self._safe_update_status(f"Error: {str(e)}")

        # Enable buttons (thread-safe)
        self._safe_enable_button("#btn-save")
        self._safe_enable_button("#btn-close")

    def _add_to_inventory(self) -> None:
        """Add deployed node to inventory."""
        try:
            self.inventory.add_node(
                hostname=self.params['name'],
                ip=self.params['ip'],
                vmid=self.params['vmid'],
                location=self.params['location'],
                node_type=self.params.get('node_type', 'k3s-worker'),
                initial_ip=self.params['ip'],
                resources={
                    'cores': self.params.get('cores', 4),
                    'ram_gb': self.params.get('memory', 16),
                    'disk_gb': self.params.get('disk_size', 200),
                    'longhorn_gb': self.params.get('longhorn_size', 0),
                }
            )

            # Add to deployment history
            self.config.add_deployment_history(
                hostname=self.params['name'],
                vmid=self.params['vmid'],
                location=self.params['location'],
                ip=self.params['ip'],
                node_type=self.params.get('node_type', 'k3s-worker'),
            )

            # Increment VMID
            self.config.increment_vmid()

            self._safe_write_log("[green]✓ Node added to inventory[/green]")

        except Exception as e:
            self._safe_write_log(f"[yellow]Warning: Failed to add to inventory: {str(e)}[/yellow]")

    @on(Button.Pressed, "#btn-save")
    def save_log(self) -> None:
        """Save log to file."""
        from datetime import datetime
        from pathlib import Path

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hostname = self.params.get('name', 'unknown')
        log_path = Path.home() / f"kapnode_deploy_{hostname}_{timestamp}.log"

        try:
            with open(log_path, 'w') as f:
                f.write("\n".join(self.log_lines))

            status_bar = self.query_one("#status-bar", Static)
            status_bar.update(f"✓ Log saved to {log_path}")

        except Exception as e:
            status_bar = self.query_one("#status-bar", Static)
            status_bar.update(f"Error saving log: {str(e)}")

    @on(Button.Pressed, "#btn-close")
    def action_cancel(self) -> None:
        """Close the log viewer."""
        self.app.pop_screen()
