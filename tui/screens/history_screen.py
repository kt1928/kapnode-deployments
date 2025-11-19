"""History Screen - View deployment history."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Header, Footer, Button, Static, DataTable, Input, Select
from textual import on
from rich.text import Text

from ..lib.config_manager import ConfigManager
from ..lib.inventory import InventoryManager


class HistoryScreen(Screen):
    """Screen for viewing deployment history."""

    BINDINGS = [
        ("escape", "back", "Back"),
        ("r", "refresh", "Refresh"),
    ]

    CSS = """
    HistoryScreen {
        layout: vertical;
    }

    #history-container {
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

    #filter-container Input,
    #filter-container Select {
        width: 30%;
        margin: 0 2;
    }

    #history-table {
        height: 1fr;
        border: solid $primary;
    }

    #detail-panel {
        height: 15;
        border: solid $primary;
        padding: 1 2;
        margin: 1 0;
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
        self.config = ConfigManager()
        self.inventory = InventoryManager()

        self.config.load_config()
        self.inventory.load_inventory()

        self.selected_deployment = None
        self.sort_by = "date"
        self.sort_reverse = True

    def compose(self) -> ComposeResult:
        """Create child widgets for history screen."""
        yield Header()

        with Container(id="history-container"):
            with Container(classes="section"):
                yield Static("Deployment History", classes="section-title")
                yield Static("View all deployed nodes and their details")

            with Horizontal(id="filter-container"):
                yield Input(placeholder="Filter by hostname...", id="input-filter")
                yield Select(
                    options=[
                        ("All Locations", "all"),
                        ("Brooklyn", "brooklyn"),
                        ("Manhattan", "manhattan"),
                        ("Staten Island", "staten_island"),
                        ("Forest Hills", "forest_hills"),
                    ],
                    value="all",
                    id="select-location-filter"
                )
                yield Select(
                    options=[
                        ("Sort by Date", "date"),
                        ("Sort by Hostname", "hostname"),
                        ("Sort by VMID", "vmid"),
                        ("Sort by Location", "location"),
                    ],
                    value="date",
                    id="select-sort"
                )

            yield DataTable(id="history-table", cursor_type="row")

            with Container(id="detail-panel"):
                yield Static("Select a deployment to view details", id="detail-content")

            with Horizontal(id="button-container"):
                yield Button("Refresh", id="btn-refresh", variant="primary")
                yield Button("Export CSV", id="btn-export", disabled=True)
                yield Button("Back", id="btn-back", variant="error")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the data table when screen mounts."""
        table = self.query_one("#history-table", DataTable)

        # Add columns
        table.add_columns(
            "Hostname",
            "VMID",
            "Location",
            "IP Address",
            "Tailscale",
            "Deployed"
        )

        # Load history
        self._refresh_table()

    def _refresh_table(self, filter_text: str = "", location_filter: str = "all") -> None:
        """Refresh the history table with inventory data."""
        table = self.query_one("#history-table", DataTable)
        table.clear()

        # Get all nodes from inventory
        nodes = self.inventory.list_nodes()

        # Apply location filter
        if location_filter != "all":
            nodes = [n for n in nodes if n.get("location") == location_filter]

        # Apply hostname filter
        if filter_text:
            nodes = [n for n in nodes if filter_text.lower() in n.get("hostname", "").lower()]

        # Sort nodes
        sort_key = self.sort_by
        if sort_key == "date":
            nodes.sort(key=lambda x: x.get("deployed", ""), reverse=self.sort_reverse)
        elif sort_key == "hostname":
            nodes.sort(key=lambda x: x.get("hostname", ""))
        elif sort_key == "vmid":
            nodes.sort(key=lambda x: x.get("vmid", 0))
        elif sort_key == "location":
            nodes.sort(key=lambda x: x.get("location", ""))

        # Populate table
        for node in nodes:
            hostname = node.get("hostname", "")
            deployed_date = node.get("deployed", "")
            if deployed_date:
                deployed_date = deployed_date[:10]  # Just date part

            table.add_row(
                hostname,
                str(node.get("vmid", "")),
                node.get("location", ""),
                node.get("ansible_host", ""),
                node.get("tailscale_name", "N/A"),
                deployed_date,
                key=hostname
            )

        # Update stats
        self._update_stats(len(nodes))

    def _update_stats(self, count: int) -> None:
        """Update statistics in the section header."""
        section_title = self.query_one(".section-title", Static)
        section_title.update(f"Deployment History ({count} nodes)")

    @on(Input.Changed, "#input-filter")
    def on_filter_change(self, event: Input.Changed) -> None:
        """Filter table when search input changes."""
        location = self.query_one("#select-location-filter", Select).value
        self._refresh_table(event.value, location)

    @on(Select.Changed, "#select-location-filter")
    def on_location_filter_change(self, event: Select.Changed) -> None:
        """Filter by location."""
        filter_text = self.query_one("#input-filter", Input).value
        self._refresh_table(filter_text, event.value)

    @on(Select.Changed, "#select-sort")
    def on_sort_change(self, event: Select.Changed) -> None:
        """Change sort order."""
        self.sort_by = event.value
        filter_text = self.query_one("#input-filter", Input).value
        location = self.query_one("#select-location-filter", Select).value
        self._refresh_table(filter_text, location)

    @on(DataTable.RowSelected)
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the table."""
        # Get the selected hostname
        hostname = event.row_key.value if hasattr(event.row_key, 'value') else str(event.row_key)

        node = self.inventory.get_node(hostname)

        if node:
            self.selected_deployment = node

            # Build detail view
            detail = Text()
            detail.append(f"Hostname: ", style="bold")
            detail.append(f"{node.get('hostname', 'N/A')}\n")

            detail.append(f"VMID: ", style="bold")
            detail.append(f"{node.get('vmid', 'N/A')}\n")

            detail.append(f"Location: ", style="bold")
            detail.append(f"{node.get('location', 'N/A')}\n")

            detail.append(f"IP Address: ", style="bold")
            detail.append(f"{node.get('ansible_host', 'N/A')}\n")

            if "initial_ip" in node:
                detail.append(f"Initial IP: ", style="bold")
                detail.append(f"{node.get('initial_ip', 'N/A')}\n")

            detail.append(f"Node Type: ", style="bold")
            detail.append(f"{node.get('node_type', 'N/A')}\n")

            if "tailscale_name" in node:
                detail.append(f"Tailscale Name: ", style="bold")
                detail.append(f"{node.get('tailscale_name', 'N/A')}\n")

            detail.append(f"Deployed: ", style="bold")
            detail.append(f"{node.get('deployed', 'N/A')}\n")

            if "resources" in node:
                resources = node["resources"]
                detail.append(f"Resources: ", style="bold")
                detail.append(
                    f"{resources.get('cores', 'N/A')} cores, "
                    f"{resources.get('ram_gb', 'N/A')} GB RAM, "
                    f"{resources.get('disk_gb', 'N/A')} GB disk\n"
                )

            self.query_one("#detail-content", Static).update(detail)

    @on(Button.Pressed, "#btn-refresh")
    def action_refresh(self) -> None:
        """Refresh the history data."""
        self.inventory.load_inventory()
        filter_text = self.query_one("#input-filter", Input).value
        location = self.query_one("#select-location-filter", Select).value
        self._refresh_table(filter_text, location)

    @on(Button.Pressed, "#btn-export")
    def export_csv(self) -> None:
        """Export deployment history to CSV."""
        import csv
        from datetime import datetime
        from pathlib import Path

        nodes = self.inventory.list_nodes()

        if not nodes:
            return

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = Path.home() / f"kapnode_history_{timestamp}.csv"

        try:
            with open(csv_path, 'w', newline='') as csvfile:
                fieldnames = ['hostname', 'vmid', 'location', 'ip', 'tailscale_name', 'node_type', 'deployed']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for node in nodes:
                    writer.writerow({
                        'hostname': node.get('hostname', ''),
                        'vmid': node.get('vmid', ''),
                        'location': node.get('location', ''),
                        'ip': node.get('ansible_host', ''),
                        'tailscale_name': node.get('tailscale_name', ''),
                        'node_type': node.get('node_type', ''),
                        'deployed': node.get('deployed', ''),
                    })

            detail_widget = self.query_one("#detail-content", Static)
            detail_widget.update(Text(f"✓ Exported to {csv_path}", style="bold green"))

        except Exception as e:
            detail_widget = self.query_one("#detail-content", Static)
            detail_widget.update(Text(f"Error exporting: {str(e)}", style="bold red"))

    @on(Button.Pressed, "#btn-back")
    def action_back(self) -> None:
        """Go back to main menu."""
        self.app.pop_screen()
