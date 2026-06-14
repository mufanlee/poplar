"""Command suggestion popup for slash commands."""

from textual.widgets import Static
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.containers import Vertical


_COMMANDS = [
    ("/help", "Show available commands"),
    ("/quit", "Exit application"),
    ("/context", "Show session context"),
    ("/compress", "Compress conversation"),
    ("/stats", "Performance statistics"),
    ("/export ", "Export session to JSON"),
    ("/import ", "Import session from JSON"),
    ("/provider", "Show current provider"),
    ("/provider list", "List all providers"),
    ("/provider set ", "Switch provider"),
]


class CommandSuggestion(ModalScreen[str]):
    """Popup screen showing slash command suggestions."""

    BINDINGS = [
        Binding("escape", "dismiss_none", "Cancel", show=False, priority=True),
        Binding("tab", "select", "Complete", show=False, priority=True),
        Binding("enter", "select", "Complete", show=False, priority=True),
        Binding("up", "nav_up", "", show=False, priority=True),
        Binding("down", "nav_down", "", show=False, priority=True),
    ]

    def __init__(self, filter_text: str):
        super().__init__()
        self._filter = filter_text.lower()
        self._index = 0

    def compose(self):
        with Vertical(id="cmd-box"):
            yield Static(" Commands ", id="cmd-title")
            yield Static(id="cmd-list")

    def on_mount(self):
        self._render_list()

    def _matching(self):
        return [(c, d) for c, d in _COMMANDS if self._filter in c.lower()]

    @property
    def _selected(self):
        items = self._matching()
        if not items:
            return ("", "")
        return items[self._index % len(items)]

    def _render_list(self):
        items = self._matching()
        if not items:
            self.query_one("#cmd-list").update("[dim]No matching commands[/dim]")
            return

        lines = []
        for i, (cmd, desc) in enumerate(items):
            prefix = "●" if i == (self._index % len(items)) else " "
            lines.append(f"{prefix} {cmd}  [dim]— {desc}[/dim]")
        self.query_one("#cmd-list").update("\n".join(lines))

    def action_nav_up(self):
        items = self._matching()
        if items:
            self._index = (self._index - 1) % len(items)
            self._render_list()

    def action_nav_down(self):
        items = self._matching()
        if items:
            self._index = (self._index + 1) % len(items)
            self._render_list()

    def action_select(self):
        cmd, _ = self._selected
        if cmd:
            self.dismiss(cmd)

    def action_dismiss_none(self):
        self.dismiss(None)

    DEFAULT_CSS = """
    CommandSuggestion {
        align: left bottom;
        margin-left: 1;
        margin-bottom: 3;
        height: auto;
    }
    #cmd-box {
        width: 42;
        height: auto;
        max-height: 14;
        background: $surface;
        border: solid $secondary;
        padding: 0 1;
    }
    #cmd-title {
        background: $primary-darken-2;
        color: $text;
        text-align: center;
        width: 100%;
    }
    #cmd-list {
        width: 100%;
        height: auto;
    }
    """
