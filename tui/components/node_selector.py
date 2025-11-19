"""Node Selector - Select node from inventory."""

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Input, DataTable, Static, Button
from textual.widget import Widget
from textual import on
from rich.text import Text

from ..lib.inventory import InventoryManager


class NodeSelector(Widget):
    """Reusable node selector widget."""

    DEFAULT_CSS = """
    NodeSelector {
        height: auto;
        border: solid $primary;
        padding: 1 2;
    }

    #selector-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #selector-filter {
        margin: 1 0;
    }

    #selector-table {
        height: 20;
        border: solid $primary-darken-2;
        margin: 1 0;
    }

    #selector-info {
        margin-top: 1;
        padding-top: 1;
        border-top: solid $primary-darken-2;
        color: $text-muted;
    }

    #selector-buttons {
        height: 4;
        align: center middle;
        margin-top: 1;
    }

    #selector-buttons Button {
        margin: 0 2;
    }
    """

    def __init__(
        self,
        title: str = "Select Node",
        filter_location: str = None,
        filter_type: str = None
    ):
        super().__init__()
        self.title = title
        self.filter_location = filter_location
        self.filter_type = filter_type
        self.inventory = InventoryManager()
        self.inventory.load_inventory()
        self.selected_node = None

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Static(self.title, id="selector-title")
        yield Input(
            placeholder="Search by hostname...",
            id="selector-filter"
        )
        yield DataTable(id="selector-table", cursor_type="row")
        yield Static("No node selected", id="selector-info")
        with Container(id="selector-buttons"):
            yield Button("Select", id="btn-select", variant="primary", disabled=True)
            yield Button("Cancel", id="btn-cancel")

    def on_mount(self) -> None:
        """Initialize the data table when widget mounts."""
        table = self.query_one("#selector-table", DataTable)

        # Add columns
        table.add_columns("Hostname", "Location", "IP", "Type", "Status")

        # Load nodes
        self._refresh_table()

    def _refresh_table(self, search_text: str = "") -> None:
        """Refresh the nodes table."""
        table = self.query_one("#selector-table", DataTable)
        table.clear()

        # Get nodes with filters
        nodes = self.inventory.list_nodes(
            location=self.filter_location,
            node_type=self.filter_type
        )

        # Apply search filter
        if search_text:
            nodes = [
                n for n in nodes
                if search_text.lower() in n.get("hostname", "").lower()
            ]

        # Populate table
        for node in nodes:
            hostname = node.get("hostname", "")
            tailscale_name = node.get("tailscale_name", "N/A")
            status = "🟢 Online" if tailscale_name != "N/A" else "⚪ Unknown"

            table.add_row(
                hostname,
                node.get("location", ""),
                node.get("ansible_host", ""),
                node.get("node_type", ""),
                status,
                key=hostname
            )

        # Update info
        info_widget = self.query_one("#selector-info", Static)
        info_widget.update(f"Found {len(nodes)} nodes")

    @on(Input.Changed, "#selector-filter")
    def on_search_change(self, event: Input.Changed) -> None:
        """Filter nodes when search input changes."""
        self._refresh_table(event.value)

    @on(DataTable.RowSelected)
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection."""
        hostname = event.row_key.value if hasattr(event.row_key, 'value') else str(event.row_key)

        self.selected_node = self.inventory.get_node(hostname)

        if self.selected_node:
            # Enable select button
            self.query_one("#btn-select", Button).disabled = False

            # Update info display
            info_text = Text()
            info_text.append("Selected: ", style="bold")
            info_text.append(f"{hostname}\n")
            info_text.append("IP: ", style="dim")
            info_text.append(f"{self.selected_node.get('ansible_host', 'N/A')}\n")
            info_text.append("Location: ", style="dim")
            info_text.append(f"{self.selected_node.get('location', 'N/A')}\n")

            if "tailscale_name" in self.selected_node:
                info_text.append("Tailscale: ", style="dim")
                info_text.append(f"{self.selected_node['tailscale_name']}\n")

            info_widget = self.query_one("#selector-info", Static)
            info_widget.update(info_text)

    def get_selected_node(self):
        """Get the currently selected node."""
        return self.selected_node


class NodeSelectorModal(Container):
    """
    Modal dialog for node selection.
    """

    DEFAULT_CSS = """
    NodeSelectorModal {
        align: center middle;
        background: $background 90%;
    }

    #modal-container {
        width: 80;
        height: 40;
        border: thick $primary;
        background: $surface;
        padding: 2;
    }
    """

    def __init__(self, **kwargs):
        super().__init__()
        self.selector_kwargs = kwargs

    def compose(self) -> ComposeResult:
        """Create modal content."""
        with Container(id="modal-container"):
            yield NodeSelector(**self.selector_kwargs)

    @on(Button.Pressed, "#btn-select")
    def on_select(self) -> None:
        """Handle node selection."""
        selector = self.query_one(NodeSelector)
        selected_node = selector.get_selected_node()

        if selected_node:
            # Post message with selected node
            self.post_message(self.NodeSelected(selected_node))

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        """Handle cancellation."""
        self.post_message(self.Cancelled())

    class NodeSelected(Widget.MessageSent):
        """Message sent when a node is selected."""

        def __init__(self, node: dict):
            super().__init__()
            self.node = node

    class Cancelled(Widget.MessageSent):
        """Message sent when selection is cancelled."""
        pass
