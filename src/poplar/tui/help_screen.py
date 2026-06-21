"""Help popup — shows available commands."""

from textual.screen import ModalScreen
from textual.widgets import Static
from textual.containers import Vertical
from textual.binding import Binding
from poplar.tui.commands import COMMANDS


class HelpScreen(ModalScreen[None]):
    """Modal popup showing all available commands."""

    BINDINGS = [
        Binding("escape", "dismiss_help", "Close", show=False, priority=True),
        Binding("q", "dismiss_help", "", show=False, priority=True),
    ]

    def compose(self):
        with Vertical(id="help-box"):
            yield Static(" Commands ", id="help-title")
            yield Static(
                "\n".join(
                    f"{c.pattern:<22s}{c.description}"
                    for c in COMMANDS
                ),
                id="help-body",
            )
            yield Static("[dim]Press Esc to close[/dim]", id="help-footer")

    def action_dismiss_help(self):
        self.dismiss(None)

    CSS = """
    HelpScreen {
        align: center middle;
        background: rgba(0,0,0,0.4);
    }
    #help-box {
        width: 50;
        height: auto;
        background: $surface;
        border: solid $secondary;
        padding: 1 2;
    }
    #help-title {
        background: $primary-darken-2;
        color: $text;
        text-align: center;
        width: 100%;
    }
    #help-body {
        width: 100%;
        padding: 1 0;
    }
    #help-footer {
        width: 100%;
        text-align: center;
        padding-top: 1;
    }
    """
