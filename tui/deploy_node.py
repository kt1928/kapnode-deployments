#!/usr/bin/env python3
"""
Kapnode Deployment Manager - Interactive TUI

Main entry point for the interactive Terminal UI for deploying and managing
Kapnode VMs across the distributed K3s cluster.

Usage:
    python deploy_node.py [--debug]

Options:
    --debug     Enable debug mode with verbose output
"""

import argparse
import sys
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding

from screens.main_menu import MainMenu


class KapnodeDeployApp(App):
    """Interactive TUI for Kapnode deployments."""

    CSS_PATH = "styles.css"
    TITLE = "Kapnode Deployment Manager"

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("d", "toggle_dark", "Toggle Dark Mode"),
    ]

    def __init__(self, debug: bool = False):
        super().__init__()
        self.debug_mode = debug

    def on_mount(self) -> None:
        """Load main menu on startup."""
        # Show welcome banner in debug mode
        if self.debug_mode:
            self.notify("Kapnode Deployment Manager started in debug mode", severity="information")

        # Push the main menu screen
        self.push_screen(MainMenu())

    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.dark = not self.dark


def main():
    """Entry point for deploy-node command."""
    parser = argparse.ArgumentParser(
        description="Kapnode Deployment Manager - Interactive TUI"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with verbose output"
    )
    args = parser.parse_args()

    # Verify we're in the right location
    script_dir = Path(__file__).parent
    if not (script_dir / "screens").exists():
        print("Error: Could not find TUI screens directory.", file=sys.stderr)
        print(f"Expected to find: {script_dir / 'screens'}", file=sys.stderr)
        sys.exit(1)

    # Create and run the app
    app = KapnodeDeployApp(debug=args.debug)

    try:
        app.run()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
