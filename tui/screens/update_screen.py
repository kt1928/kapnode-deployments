"""Update Screen - Update existing nodes."""

from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import Header, Footer, Button, Static, DataTable, Input
from textual import on
from rich.text import Text

from ..lib.inventory import InventoryManager
from ..lib.config_manager import ConfigManager
from ..lib.ssh_manager import SSHManager


class UpdateScreen(Screen):
    """Screen for updating existing nodes."""

    BINDINGS = [
        ("escape", "back", "Back"),
    ]

    CSS = """
    UpdateScreen {
        layout: vertical;
    }

    #update-container {
        width: 100%;
        height: 100%;
        padding: 1 2;
    }

    .section {
        border: solid $primary;
        margin: 1 0;
        padding: 1 2;
    }

    .section-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #filter-container {
        height: 5;
        margin: 1 0;
    }

    #filter-container Input {
        width: 50%;
        margin: 0 2;
    }

    #nodes-table {
        height: 1fr;
        border: solid $primary;
    }

    #button-container {
        height: 5;
        align: center middle;
        margin: 1 0;
    }

    #button-container Button {
        margin: 0 2;
    }
    """

    def __init__(self):
        super().__init__()
        self.inventory = InventoryManager()
        self.config = ConfigManager()
        self.ssh_manager = SSHManager()

        self.inventory.load_inventory()
        self.config.load_config()

        self.selected_node = None

    def compose(self) -> ComposeResult:
        """Create child widgets for update screen."""
        yield Header()

        with Container(id="update-container"):
            with Container(classes="section"):
                yield Static("Update Existing Node", classes="section-title")
                yield Static("Select a node from the inventory to update")

            with Horizontal(id="filter-container"):
                yield Input(placeholder="Filter by hostname...", id="input-filter")

            yield DataTable(id="nodes-table", cursor_type="row")

            with Horizontal(id="button-container"):
                yield Button("Connect to Node", id="btn-connect", variant="primary", disabled=True)
                yield Button("Update Packages", id="btn-update-packages", disabled=True)
                yield Button("Reconfigure Storage", id="btn-storage", disabled=True)
                yield Button("Back", id="btn-back", variant="error")

            yield Static("", id="status-message")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the data table when screen mounts."""
        table = self.query_one("#nodes-table", DataTable)

        # Add columns
        table.add_columns("Hostname", "VMID", "Location", "IP", "Type", "Deployed")

        # Load nodes
        self._refresh_table()

    def _refresh_table(self, filter_text: str = "") -> None:
        """Refresh the nodes table with inventory data."""
        table = self.query_one("#nodes-table", DataTable)
        table.clear()

        nodes = self.inventory.list_nodes()

        for node in nodes:
            hostname = node.get("hostname", "")

            # Apply filter
            if filter_text and filter_text.lower() not in hostname.lower():
                continue

            table.add_row(
                hostname,
                str(node.get("vmid", "")),
                node.get("location", ""),
                node.get("ansible_host", ""),
                node.get("node_type", ""),
                node.get("deployed", "")[:10],  # Just date part
                key=hostname
            )

    @on(Input.Changed, "#input-filter")
    def on_filter_change(self, event: Input.Changed) -> None:
        """Filter table when search input changes."""
        self._refresh_table(event.value)

    @on(DataTable.RowSelected)
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the table."""
        # Get the selected hostname
        hostname = event.row_key.value if hasattr(event.row_key, 'value') else str(event.row_key)

        self.selected_node = self.inventory.get_node(hostname)

        # Enable action buttons
        self.query_one("#btn-connect", Button).disabled = False
        self.query_one("#btn-update-packages", Button).disabled = False
        self.query_one("#btn-storage", Button).disabled = False

        # Update status message
        if self.selected_node:
            status = Text()
            status.append(f"Selected: {hostname}\n", style="bold green")
            status.append(f"IP: {self.selected_node.get('ansible_host', 'N/A')}\n")
            status.append(f"Location: {self.selected_node.get('location', 'N/A')}\n")
            self.query_one("#status-message", Static).update(status)

    @on(Button.Pressed, "#btn-connect")
    def connect_to_node(self) -> None:
        """Open SSH connection to selected node."""
        if not self.selected_node:
            return

        hostname = self.selected_node.get("hostname")
        ip = self.selected_node.get("ansible_host")
        tailscale_name = self.selected_node.get("tailscale_name", hostname)

        status = Text()
        status.append(f"Connecting to {tailscale_name or hostname}...\n", style="yellow")
        status.append(f"SSH command: ssh ubuntu@{tailscale_name or ip}\n")
        status.append("\nNote: TUI cannot open interactive SSH. Use the command above in your terminal.\n", style="dim")

        self.query_one("#status-message", Static).update(status)

    @on(Button.Pressed, "#btn-update-packages")
    def update_packages(self) -> None:
        """Update packages on selected node."""
        if not self.selected_node:
            return

        hostname = self.selected_node.get("hostname")
        ip = self.selected_node.get("ansible_host")
        ssh_key = Path(self.config.get_preference("ssh_key", "~/.ssh/homelab_rsa")).expanduser()

        status_widget = self.query_one("#status-message", Static)
        status_widget.update(Text(f"Updating packages on {hostname}...", style="yellow"))

        # Execute update command
        commands = [
            "sudo apt update",
            "sudo apt upgrade -y",
            "sudo apt autoremove -y"
        ]

        try:
            for cmd in commands:
                stdout, stderr, exit_code = self.ssh_manager.execute_command(
                    host=ip,
                    user="ubuntu",
                    command=cmd,
                    key=ssh_key
                )

                if exit_code != 0:
                    status_widget.update(Text(
                        f"Error executing '{cmd}':\n{stderr}",
                        style="bold red"
                    ))
                    return

            status_widget.update(Text(
                f"✓ Successfully updated packages on {hostname}",
                style="bold green"
            ))

        except Exception as e:
            status_widget.update(Text(
                f"Error updating packages: {str(e)}",
                style="bold red"
            ))

    @on(Button.Pressed, "#btn-storage")
    def reconfigure_storage(self) -> None:
        """Reconfigure storage on selected node."""
        if not self.selected_node:
            return

        hostname = self.selected_node.get("hostname")

        status = Text()
        status.append(f"Storage reconfiguration for {hostname}\n", style="yellow")
        status.append("\nThis feature requires the post-install-storage.sh script.\n")
        status.append("Run manually: ssh ubuntu@{hostname} 'sudo ./post-install-storage.sh'\n", style="dim")

        self.query_one("#status-message", Static).update(status)

    @on(Button.Pressed, "#btn-back")
    def action_back(self) -> None:
        """Go back to main menu."""
        self.app.pop_screen()
