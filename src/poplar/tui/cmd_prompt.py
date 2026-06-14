"""Command suggestion popup for slash commands."""

from textual.widgets import Static
from textual.binding import Binding
from textual.screen import Screen
from textual.containers import Vertical
from textual.message import Message
from typing import List


class CommandSelected(Message):
    """Posted when user selects a command from the suggestion list."""

    def __init__(self, command: str):
        self.command = command
        super().__init__()


_COMMANDS = [
    ("/help", "Show available commands"),
    ("/exit", "Exit application"),
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


class CommandSuggestion(Screen[str]):
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
            for cmd, desc in self._matching():
                prefix = "● " if (cmd, desc) == self._selected else "  "
                yield Static(f"{prefix}{cmd} [dim]— {desc}[/dim]", id=f"cmd-{cmd}")

    def _matching(self):
        return [(c, d) for c, d in _COMMANDS if self._filter in c.lower()]

    @property
    def _selected(self):
        items = self._matching()
        if not items:
            return ("", "")
        idx = self._index % len(items)
        return items[idx]

    def on_mount(self):
        self.query_one("#cmd-title").focus()

    def action_nav_up(self):
        items = self._matching()
        if items:
            self._index = (self._index - 1) % len(items)
            self._refresh()

    def action_nav_down(self):
        items = self._matching()
        if items:
            self._index = (self._index + 1) % len(items)
            self._refresh()

    def action_select(self):
        cmd, _ = self._selected
        if cmd:
            self.dismiss(cmd)

    def action_dismiss_none(self):
        self.dismiss(None)

    def _refresh(self):
        self.remove_children(compose=False)
        self.compose()
        self.mount_composed_widgets()

    DEFAULT_CSS = """
    CommandSuggestion {
        align: center bottom;
        margin-bottom: 4;
    }
    #cmd-box {
        width: 42;
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
    CommandSuggestion Static {
        height: 1;
    }
    """
