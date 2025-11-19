"""Progress Indicator - Show deployment progress."""

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import ProgressBar, Static, Button
from textual.widget import Widget
from rich.text import Text


class ProgressIndicator(Widget):
    """Reusable progress indicator widget."""

    DEFAULT_CSS = """
    ProgressIndicator {
        height: auto;
        border: solid $primary;
        padding: 1 2;
        margin: 1 0;
    }

    #progress-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #progress-bar {
        margin: 1 0;
    }

    #progress-stage {
        color: $text-muted;
        margin: 1 0;
    }

    #progress-time {
        color: $text-muted;
        text-align: right;
    }

    .error-state {
        color: $error;
        text-style: bold;
    }

    .success-state {
        color: $success;
        text-style: bold;
    }
    """

    def __init__(self, title: str = "Progress", total: int = 100):
        super().__init__()
        self.title = title
        self.total = total
        self.current = 0
        self.stage = "Starting..."
        self.error_message = None
        self.success = False

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Static(self.title, id="progress-title")
        yield ProgressBar(total=self.total, show_eta=True, id="progress-bar")
        yield Static(self.stage, id="progress-stage")
        yield Static("Estimated time: Calculating...", id="progress-time")

    def update_progress(self, current: int, stage: str = None) -> None:
        """
        Update progress value and stage.

        Args:
            current: Current progress value
            stage: Optional stage description
        """
        self.current = current

        progress_bar = self.query_one("#progress-bar", ProgressBar)
        progress_bar.update(progress=current)

        if stage:
            self.stage = stage
            stage_widget = self.query_one("#progress-stage", Static)
            stage_widget.update(stage)

    def set_stage(self, stage: str) -> None:
        """
        Set current stage description.

        Args:
            stage: Stage description
        """
        self.stage = stage
        stage_widget = self.query_one("#progress-stage", Static)
        stage_widget.update(stage)

    def set_error(self, error_message: str) -> None:
        """
        Set error state.

        Args:
            error_message: Error message to display
        """
        self.error_message = error_message

        stage_widget = self.query_one("#progress-stage", Static)
        stage_widget.add_class("error-state")
        stage_widget.update(f"Error: {error_message}")

        progress_bar = self.query_one("#progress-bar", ProgressBar)
        progress_bar.update(progress=0)

    def set_complete(self, success_message: str = "Completed successfully") -> None:
        """
        Set completion state.

        Args:
            success_message: Success message to display
        """
        self.success = True

        stage_widget = self.query_one("#progress-stage", Static)
        stage_widget.add_class("success-state")
        stage_widget.update(f"✓ {success_message}")

        progress_bar = self.query_one("#progress-bar", ProgressBar)
        progress_bar.update(progress=self.total)

    def set_eta(self, eta_seconds: int) -> None:
        """
        Set estimated time remaining.

        Args:
            eta_seconds: Estimated seconds remaining
        """
        minutes, seconds = divmod(eta_seconds, 60)
        eta_text = f"Estimated time: {minutes}m {seconds}s"

        time_widget = self.query_one("#progress-time", Static)
        time_widget.update(eta_text)


class DeploymentProgress(Container):
    """
    Complete deployment progress display with stages.
    """

    DEFAULT_CSS = """
    DeploymentProgress {
        height: auto;
        border: thick $primary;
        padding: 2;
        margin: 1 2;
    }

    #deployment-title {
        text-style: bold;
        text-align: center;
        color: $accent;
        margin-bottom: 2;
    }

    .stage-item {
        margin: 1 0;
        padding: 0 2;
    }

    .stage-pending {
        color: $text-muted;
    }

    .stage-active {
        color: $accent;
        text-style: bold;
    }

    .stage-complete {
        color: $success;
    }

    .stage-error {
        color: $error;
        text-style: bold;
    }

    #cancel-button {
        margin-top: 2;
        width: 100%;
    }
    """

    def __init__(self, hostname: str):
        super().__init__()
        self.hostname = hostname
        self.stages = [
            "Downloading image",
            "Creating VM",
            "Configuring cloud-init",
            "Starting VM",
            "Waiting for boot",
            "Installing K3s",
            "Configuring Tailscale",
            "Joining cluster",
        ]
        self.current_stage = 0

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Static(f"Deploying {self.hostname}", id="deployment-title")

        for i, stage in enumerate(self.stages):
            stage_text = f"{'⏳' if i == 0 else '⬜'} {stage}"
            yield Static(
                stage_text,
                id=f"stage-{i}",
                classes="stage-item stage-pending"
            )

        yield Button("Cancel Deployment", id="cancel-button", variant="error")

    def set_stage(self, stage_index: int) -> None:
        """
        Set the current active stage.

        Args:
            stage_index: Index of the current stage
        """
        if stage_index < 0 or stage_index >= len(self.stages):
            return

        # Mark previous stages as complete
        for i in range(stage_index):
            stage_widget = self.query_one(f"#stage-{i}", Static)
            stage_widget.remove_class("stage-pending")
            stage_widget.remove_class("stage-active")
            stage_widget.add_class("stage-complete")
            stage_widget.update(f"✓ {self.stages[i]}")

        # Mark current stage as active
        stage_widget = self.query_one(f"#stage-{stage_index}", Static)
        stage_widget.remove_class("stage-pending")
        stage_widget.add_class("stage-active")
        stage_widget.update(f"⏳ {self.stages[stage_index]}")

        # Mark future stages as pending
        for i in range(stage_index + 1, len(self.stages)):
            stage_widget = self.query_one(f"#stage-{i}", Static)
            stage_widget.remove_class("stage-active")
            stage_widget.remove_class("stage-complete")
            stage_widget.add_class("stage-pending")
            stage_widget.update(f"⬜ {self.stages[i]}")

        self.current_stage = stage_index

    def set_stage_error(self, stage_index: int, error: str) -> None:
        """
        Mark a stage as failed.

        Args:
            stage_index: Index of the failed stage
            error: Error message
        """
        stage_widget = self.query_one(f"#stage-{stage_index}", Static)
        stage_widget.remove_class("stage-pending")
        stage_widget.remove_class("stage-active")
        stage_widget.add_class("stage-error")
        stage_widget.update(f"✗ {self.stages[stage_index]}: {error}")

    def set_complete(self) -> None:
        """Mark all stages as complete."""
        for i in range(len(self.stages)):
            stage_widget = self.query_one(f"#stage-{i}", Static)
            stage_widget.remove_class("stage-pending")
            stage_widget.remove_class("stage-active")
            stage_widget.add_class("stage-complete")
            stage_widget.update(f"✓ {self.stages[i]}")

        title_widget = self.query_one("#deployment-title", Static)
        title_widget.update(f"✓ {self.hostname} deployed successfully!")

        cancel_button = self.query_one("#cancel-button", Button)
        cancel_button.label = "Close"
        cancel_button.variant = "primary"
