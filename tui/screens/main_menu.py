"""Main Menu - Entry point with navigation options."""

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.screen import Screen
from textual.widgets import Header, Footer, Button, Static
from textual import on


class MainMenu(Screen):
    """Main menu screen with navigation options."""

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "deploy", "Deploy"),
        ("u", "update", "Update"),
        ("h", "history", "History"),
    ]

    CSS = """
    MainMenu {
        align: center middle;
    }

    #menu-container {
        width: 60;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 2 4;
    }

    #title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 2;
    }

    Button {
        width: 100%;
        margin: 1 0;
    }

    #status {
        margin-top: 2;
        padding-top: 1;
        border-top: solid $primary;
        text-align: center;
        color: $text-muted;
    }
    """

    def compose(self) -> ComposeResult:
        """Create child widgets for the main menu."""
        yield Header()

        with Container(id="menu-container"):
            yield Static("Kapnode Deployment Manager", id="title")
            yield Button("Deploy New Node", id="btn-deploy", variant="primary")
            yield Button("Update Existing Node", id="btn-update")
            yield Button("View Deployment History", id="btn-history")
            yield Button("Cluster Status (Coming Soon)", id="btn-status", disabled=True)
            yield Button("Quit", id="btn-quit", variant="error")
            yield Static(self._get_status_text(), id="status")

        yield Footer()

    def _get_status_text(self) -> str:
        """Get current git branch and sync status."""
        import subprocess

        try:
            # Get current branch
            branch = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                timeout=2
            ).stdout.strip()

            # Check if there are uncommitted changes
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=2
            ).stdout.strip()

            sync_status = "✓ Clean" if not status else "⚠ Uncommitted changes"

            return f"Branch: {branch} | {sync_status}"

        except Exception:
            return "Git status: Unknown"

    @on(Button.Pressed, "#btn-deploy")
    def action_deploy(self) -> None:
        """Navigate to deploy screen."""
        from .deploy_screen import DeployScreen
        self.app.push_screen(DeployScreen())

    @on(Button.Pressed, "#btn-update")
    def action_update(self) -> None:
        """Navigate to update screen."""
        from .update_screen import UpdateScreen
        self.app.push_screen(UpdateScreen())

    @on(Button.Pressed, "#btn-history")
    def action_history(self) -> None:
        """Navigate to history screen."""
        from .history_screen import HistoryScreen
        self.app.push_screen(HistoryScreen())

    @on(Button.Pressed, "#btn-quit")
    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()
