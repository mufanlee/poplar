"""Workspace trust modal — shown on startup when workspace is not yet trusted."""

from pathlib import Path
from textual.screen import ModalScreen
from textual.widgets import Static, Button
from textual.containers import Vertical, Horizontal
from textual.binding import Binding


class TrustScreen(ModalScreen[bool]):
    """Modal shown when accessing an untrusted workspace.

    Returns True if the user trusts the workspace, False to exit.
    """

    BINDINGS = [
        Binding("escape", "reject", "No", show=False, priority=True),
    ]

    def __init__(self, workspace_path: Path):
        super().__init__()
        self._workspace_path = workspace_path

    def compose(self):
        display_path = str(self._workspace_path)
        # Truncate if too long
        if len(display_path) > 60:
            display_path = "..." + display_path[-57:]

        with Vertical(id="trust-box"):
            yield Static(" ⚠ Workspace Trust ", id="trust-title")
            yield Static(
                f"Poplar is about to access:\n\n"
                f"[bold]{display_path}[/bold]\n\n"
                f"Poplar can read, write files and execute commands here.\n"
                f"Do you trust this workspace?",
                id="trust-body",
            )
            with Horizontal(id="trust-buttons"):
                yield Button("✓ Yes, I trust this folder", variant="primary", id="btn-trust")
                yield Button("✗ No, exit", variant="error", id="btn-exit")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-trust":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_reject(self):
        self.dismiss(False)

    DEFAULT_CSS = """
    TrustScreen {
        align: center middle;
        background: rgba(0,0,0,0.5);
    }

    #trust-box {
        width: 54;
        background: $surface;
        border: thick $warning;
        padding: 1 2;
    }

    #trust-title {
        background: $warning-darken-1;
        color: $text;
        text-align: center;
        text-style: bold;
        padding: 0 1;
    }

    #trust-body {
        padding: 1 0;
        color: $text;
    }

    #trust-buttons {
        height: 3;
        align-horizontal: center;
    }

    #trust-buttons Button {
        margin: 0 1;
    }
    """
