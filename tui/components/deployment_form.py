"""Deployment Form - Reusable form for deployment parameters."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Input, Label, Static, Select, Collapsible
from textual.widget import Widget
from textual import on
from rich.text import Text

from ..lib.validators import Validators
from ..lib.config_manager import ConfigManager


class DeploymentForm(Widget):
    """Reusable deployment parameter form."""

    DEFAULT_CSS = """
    DeploymentForm {
        height: auto;
        border: solid $primary;
        padding: 1 2;
    }

    .form-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    .form-section {
        margin: 1 0;
        padding: 1 0;
        border-bottom: solid $primary-darken-2;
    }

    .form-field {
        margin: 0 0 1 0;
        height: 3;
    }

    .field-label {
        width: 30%;
        padding: 1 1;
        content-align: left middle;
    }

    .field-input {
        width: 70%;
    }

    .field-error {
        color: $error;
        text-style: italic;
        padding: 0 1;
    }

    .field-valid {
        color: $success;
        padding: 0 1;
    }

    #advanced-options {
        margin-top: 1;
    }
    """

    def __init__(self, config: ConfigManager = None):
        super().__init__()
        self.config = config or ConfigManager()
        self.config.load_config()
        self.validators = Validators()
        self.validation_errors = {}

    def compose(self) -> ComposeResult:
        """Create form widgets."""
        yield Static("Deployment Parameters", classes="form-title")

        # Basic Configuration Section
        with Container(classes="form-section"):
            yield Static("Basic Configuration", classes="form-title")

            with Horizontal(classes="form-field"):
                yield Label("Hostname *", classes="field-label")
                yield Input(
                    placeholder="kapnode7",
                    id="form-hostname",
                    classes="field-input"
                )

            with Horizontal(classes="form-field"):
                yield Label("VMID *", classes="field-label")
                yield Input(
                    value=str(self.config.get_next_vmid()),
                    placeholder="207",
                    id="form-vmid",
                    classes="field-input"
                )

            with Horizontal(classes="form-field"):
                yield Label("Location *", classes="field-label")
                yield Select(
                    options=[
                        ("Brooklyn", "brooklyn"),
                        ("Manhattan", "manhattan"),
                        ("Staten Island", "staten_island"),
                        ("Forest Hills", "forest_hills"),
                    ],
                    id="form-location",
                    classes="field-input"
                )

        # Network Configuration Section
        with Container(classes="form-section"):
            yield Static("Network Configuration", classes="form-title")

            with Horizontal(classes="form-field"):
                yield Label("IP Address *", classes="field-label")
                yield Input(
                    placeholder="192.168.86.207",
                    id="form-ip",
                    classes="field-input"
                )

            with Horizontal(classes="form-field"):
                yield Label("Gateway *", classes="field-label")
                yield Input(
                    value="192.168.86.1",
                    placeholder="192.168.86.1",
                    id="form-gateway",
                    classes="field-input"
                )

            with Horizontal(classes="form-field"):
                yield Label("DNS Servers *", classes="field-label")
                yield Input(
                    value="192.168.86.1,8.8.8.8",
                    placeholder="192.168.86.1,8.8.8.8",
                    id="form-dns",
                    classes="field-input"
                )

        # Resources Section
        with Container(classes="form-section"):
            yield Static("Resources", classes="form-title")

            with Horizontal(classes="form-field"):
                yield Label("CPU Cores *", classes="field-label")
                yield Input(
                    value=str(self.config.get_preference("defaults.cores", 4)),
                    placeholder="4",
                    id="form-cores",
                    classes="field-input"
                )

            with Horizontal(classes="form-field"):
                yield Label("RAM (GB) *", classes="field-label")
                yield Input(
                    value=str(self.config.get_preference("defaults.ram_gb", 16)),
                    placeholder="16",
                    id="form-memory",
                    classes="field-input"
                )

            with Horizontal(classes="form-field"):
                yield Label("Disk (GB) *", classes="field-label")
                yield Input(
                    value=str(self.config.get_preference("defaults.disk_gb", 200)),
                    placeholder="200",
                    id="form-disk",
                    classes="field-input"
                )

        # Advanced Options (Collapsible)
        with Collapsible(title="Advanced Options", id="advanced-options"):
            with Horizontal(classes="form-field"):
                yield Label("Node Type", classes="field-label")
                yield Select(
                    options=[
                        ("K3s Worker", "k3s-worker"),
                        ("K3s Master", "k3s-master"),
                        ("Backup Node", "backup"),
                    ],
                    value="k3s-worker",
                    id="form-node-type",
                    classes="field-input"
                )

            with Horizontal(classes="form-field"):
                yield Label("Longhorn Size (GB)", classes="field-label")
                yield Input(
                    value="0",
                    placeholder="0 (disabled)",
                    id="form-longhorn",
                    classes="field-input"
                )

            with Horizontal(classes="form-field"):
                yield Label("Backup Size (GB)", classes="field-label")
                yield Input(
                    value="0",
                    placeholder="0 (disabled)",
                    id="form-backup",
                    classes="field-input"
                )

            with Horizontal(classes="form-field"):
                yield Label("K3s Master URL", classes="field-label")
                yield Input(
                    value=self.config.get_preference("k3s_master", ""),
                    placeholder="https://minikapserver:6443",
                    id="form-k3s-master",
                    classes="field-input"
                )

            with Horizontal(classes="form-field"):
                yield Label("K3s Token", classes="field-label")
                yield Input(
                    value=self.config.get_preference("k3s_token", ""),
                    placeholder="K10xxx::server:xxx",
                    password=True,
                    id="form-k3s-token",
                    classes="field-input"
                )

        # Validation Summary
        yield Static("", id="form-validation-summary")

    @on(Select.Changed, "#form-location")
    def on_location_change(self, event: Select.Changed) -> None:
        """Update network defaults when location changes."""
        location = event.value
        defaults = self.config.get_location_defaults(location)

        self.query_one("#form-gateway", Input).value = defaults.get("gateway", "")
        self.query_one("#form-dns", Input).value = defaults.get("dns", "")

    @on(Input.Changed)
    def on_input_change(self, event: Input.Changed) -> None:
        """Validate input as it changes."""
        input_id = event.input.id

        # Clear previous validation for this field
        if input_id in self.validation_errors:
            del self.validation_errors[input_id]

        # Validate based on field
        value = event.value

        if input_id == "form-hostname":
            valid, error = self.validators.validate_hostname(value)
            if not valid:
                self.validation_errors[input_id] = error

        elif input_id == "form-vmid":
            try:
                vmid = int(value)
                valid, error = self.validators.validate_vmid(vmid)
                if not valid:
                    self.validation_errors[input_id] = error
            except ValueError:
                self.validation_errors[input_id] = "VMID must be a number"

        elif input_id == "form-ip":
            valid, error = self.validators.validate_ip(value)
            if not valid:
                self.validation_errors[input_id] = error

        elif input_id == "form-gateway":
            valid, error = self.validators.validate_ip(value)
            if not valid:
                self.validation_errors[input_id] = error

        elif input_id == "form-dns":
            valid, error = self.validators.validate_dns(value)
            if not valid:
                self.validation_errors[input_id] = error

        # Update validation summary
        self._update_validation_summary()

    def _update_validation_summary(self) -> None:
        """Update the validation summary display."""
        summary_widget = self.query_one("#form-validation-summary", Static)

        if self.validation_errors:
            error_text = Text()
            error_text.append("Validation errors:\n", style="bold red")
            for field, error in self.validation_errors.items():
                field_name = field.replace("form-", "").replace("-", " ").title()
                error_text.append(f"  • {field_name}: {error}\n", style="red")

            summary_widget.update(error_text)
        else:
            summary_widget.update("")

    def validate_all(self) -> tuple[bool, dict]:
        """
        Validate all form fields.

        Returns:
            Tuple of (is_valid: bool, errors: dict)
        """
        self.validation_errors = {}
        params = self.get_values()

        # Validate all parameters
        valid, error_list = self.validators.validate_all_deployment_params(params)

        if not valid:
            for error in error_list:
                # Parse error to get field name
                if ":" in error:
                    field, msg = error.split(":", 1)
                    self.validation_errors[field.lower().strip()] = msg.strip()

        self._update_validation_summary()

        return len(self.validation_errors) == 0, self.validation_errors

    def get_values(self) -> dict:
        """
        Get all form values as a dictionary.

        Returns:
            Dictionary of form values
        """
        return {
            "name": self.query_one("#form-hostname", Input).value,
            "vmid": int(self.query_one("#form-vmid", Input).value or 0),
            "ip": self.query_one("#form-ip", Input).value,
            "gateway": self.query_one("#form-gateway", Input).value,
            "dns": self.query_one("#form-dns", Input).value,
            "cores": int(self.query_one("#form-cores", Input).value or 0),
            "memory": int(self.query_one("#form-memory", Input).value or 0),
            "disk_size": int(self.query_one("#form-disk", Input).value or 0),
            "location": self.query_one("#form-location", Select).value,
            "node_type": self.query_one("#form-node-type", Select).value,
            "longhorn_size": int(self.query_one("#form-longhorn", Input).value or 0),
            "backup_size": int(self.query_one("#form-backup", Input).value or 0),
            "k3s_master": self.query_one("#form-k3s-master", Input).value,
            "k3s_token": self.query_one("#form-k3s-token", Input).value,
            "network": self.config.get_location_defaults(
                self.query_one("#form-location", Select).value
            ).get("network", "192.168.86.0/24"),
        }

    def set_values(self, values: dict) -> None:
        """
        Set form values from a dictionary.

        Args:
            values: Dictionary of values to set
        """
        if "name" in values:
            self.query_one("#form-hostname", Input).value = values["name"]
        if "vmid" in values:
            self.query_one("#form-vmid", Input).value = str(values["vmid"])
        if "ip" in values:
            self.query_one("#form-ip", Input).value = values["ip"]
        if "gateway" in values:
            self.query_one("#form-gateway", Input).value = values["gateway"]
        if "dns" in values:
            self.query_one("#form-dns", Input).value = values["dns"]
        if "cores" in values:
            self.query_one("#form-cores", Input).value = str(values["cores"])
        if "memory" in values:
            self.query_one("#form-memory", Input).value = str(values["memory"])
        if "disk_size" in values:
            self.query_one("#form-disk", Input).value = str(values["disk_size"])
