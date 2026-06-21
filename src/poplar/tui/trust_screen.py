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
        Binding("left", "focus_previous", "", show=False),
        Binding("right", "focus_next", "", show=False),
        Binding("up", "focus_previous", "", show=False),
        Binding("down", "focus_next", "", show=False),
    ]

    def __init__(self, workspace_path: Path):
        super().__init__()
        self._workspace_path = workspace_path

    def compose(self):
        display_path = str(self._workspace_path)
        if len(display_path) > 55:
            display_path = "…" + display_path[-54:]

        with Vertical(id="trust-box"):
            yield Static(" 🔐  Workspace Trust", id="trust-title")
            yield Static(
                f"Poplar needs permission to access:\n"
                f"\n"
                f"[bold $accent]{display_path}[/bold $accent]\n"
                f"\n"
                f"Poplar can [italic]read[/italic] files, [italic]write[/italic] files,\n"
                f"and [italic]execute[/italic] shell commands in this workspace.\n"
                f"\n"
                f"[dim]Trust is remembered for this folder and its subdirectories.[/dim]",
                id="trust-body",
            )
            with Horizontal(id="trust-buttons"):
                yield Button("  ✓  Trust  ", variant="primary", id="btn-trust")
                yield Button("  ✗  Exit   ", variant="default", id="btn-exit")

    def on_mount(self):
        """Focus the 'Yes' button by default."""
        self.query_one("#btn-trust", Button).focus()

    def action_focus_next(self):
        """Move focus to the next button."""
        self.query_one("#btn-exit", Button).focus()

    def action_focus_previous(self):
        """Move focus to the previous button."""
        self.query_one("#btn-trust", Button).focus()

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
        background: rgba(0,0,0,0.55);
    }

    #trust-box {
        width: 56;
        background: $surface;
        border: thick $primary;
        border-title-color: $primary;
        padding: 0 2 1 2;
    }

    #trust-title {
        height: 3;
        background: $primary-darken-1;
        color: $text;
        text-align: center;
        text-style: bold;
        padding: 1 2;
        margin: 0 -2;
    }

    #trust-body {
        padding: 2 0;
        color: $text;
    }

    #trust-buttons {
        height: 3;
        align-horizontal: center;
        margin-bottom: 1;
    }

    #trust-buttons Button {
        margin: 0 2;
        min-width: 16;
    }
    """
