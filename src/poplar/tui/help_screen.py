"""Help screen showing available commands."""

from textual.screen import ModalScreen
from textual.widgets import Static
from textual.containers import Vertical
from textual.binding import Binding


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
                "\n".join([
                    "/help               Show this",
                    "/quit               Exit application",
                    "/context            Session context info",
                    "/compress           Summarize conversation",
                    "/stats              Performance statistics",
                    "/export <path>      Export session to JSON",
                    "/import <path>      Import session from JSON",
                    "/provider           Show current provider",
                    "/provider list      List all providers",
                    "/provider set <n>   Switch provider",
                ]),
                id="help-body",
            )
            yield Static("[dim]Press Esc or Q to close[/dim]", id="help-footer")

    def action_dismiss_help(self):
        self.dismiss(None)

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
        background: transparent;
    }
    #help-box {
        width: 48;
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
