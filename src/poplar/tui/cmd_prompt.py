"""Command suggestion popup for slash commands — mounted as widget above composer."""

from textual.widgets import Static
from textual.containers import Vertical


class CommandSuggestion(Vertical):
    """Slash command suggestion popup, shown above the composer."""

    _COMMANDS = [
        ("/help", "Show available commands"),
        ("/quit", "Exit application"),
        ("/session", "Manage sessions"),
        ("/clear", "Clear current session"),
        ("/context", "Show session context"),
        ("/compress", "Compress conversation"),
        ("/stats", "Performance statistics"),
        ("/export ", "Export session to JSON"),
        ("/import ", "Import session from JSON"),
        ("/provider", "Show current provider"),
        ("/provider list", "List all providers"),
        ("/provider set", "Switch provider"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._filter = ""
        self._index = 0
        self._visible: bool = False

    @property
    def is_visible(self) -> bool:
        return self._visible

    def compose(self):
        yield Static(" Commands ", id="cmd-title")
        yield Static(id="cmd-list")

    def show(self, filter_text: str):
        """Show the command popup with the given filter."""
        new_filter = filter_text.lower()
        if new_filter != self._filter:
            self._index = 0
        self._filter = new_filter
        self._visible = True
        self.styles.display = "block"
        self._render_list()

    def hide(self):
        """Hide the popup."""
        self._visible = False
        self.styles.display = "none"
        self._filter = ""
        self._index = 0

    def _matching(self):
        return [(c, d) for c, d in self._COMMANDS if self._filter in c.lower()]

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
            lines.append(f"{prefix} {cmd}  {desc}")
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

    def action_dismiss(self):
        self.hide()

    DEFAULT_CSS = """
    CommandSuggestion {
        height: 15;
        width: 42;
        margin: 0 0 0 1;
        background: $surface;
        border: solid $secondary;
        padding: 0 1;
        display: none;
        overflow-y: auto;
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
