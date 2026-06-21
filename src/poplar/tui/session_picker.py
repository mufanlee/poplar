"""Session picker modal dialog."""

from textual.screen import ModalScreen
from textual.widgets import Static, Input
from textual.containers import Vertical, VerticalScroll
from textual.binding import Binding
from typing import List
from poplar.core.session import Session
from poplar.i18n import t


class SessionPicker(ModalScreen[str | None]):
    """Modal dialog for selecting/managing sessions."""

    BINDINGS = [
        Binding("escape", "close", "Close", priority=True),
        Binding("up", "nav_up", "", show=False, priority=True),
        Binding("down", "nav_down", "", show=False, priority=True),
        Binding("n", "new_session", "", show=False, priority=True),
        Binding("d", "delete_session", "", show=False, priority=True),
        Binding("r", "rename_session", "", show=False, priority=True),
    ]

    def on_key(self, event):
        if self._renaming:
            event.stop()
            return
        if event.key == "enter" and self._sessions:
            self.dismiss(self._sessions[self._nav_index].id)

    def __init__(self, sessions: List[Session], active_id: str):
        super().__init__()
        self._sessions = sessions
        self._active_id = active_id
        self._nav_index = next(
            (i for i, s in enumerate(sessions) if s.id == active_id), 0
        )
        self._renaming = False

    def compose(self):
        with Vertical(id="picker-box"):
            yield Static(" Sessions ", id="picker-title")
            with VerticalScroll(id="picker-list"):
                pass
            yield Static(
                t("picker_hint"),
                id="picker-hint",
            )

    def on_mount(self):
        self._render_list()
        self.query_one("#picker-list").focus()

    def _render_list(self):
        container = self.query_one("#picker-list")
        container.remove_children()
        for i, s in enumerate(self._sessions):
            count = getattr(s, "_message_count", 0)
            title = s.title[:26] or t("new_chat")
            time_str = s.created_at.strftime("%m-%d %H:%M") if s.created_at else ""
            info = f"{count:>3}msgs {time_str}"
            is_active = s.id == self._active_id
            is_nav = i == self._nav_index
            padded_title = f"{title:<28s}"
            if is_active:
                content = f"[bold cyan]▶ {padded_title}[/bold cyan][dim]{info}[/dim]"
            elif is_nav:
                content = f"[bold reverse]  {padded_title}[/bold reverse][dim]{info}[/dim]"
            else:
                content = f"  {padded_title}[dim]{info}[/dim]"
            container.mount(Static(content, classes="session-row"))

    def action_nav_up(self):
        if not self._renaming and self._nav_index > 0:
            self._nav_index -= 1; self._render_list()

    def action_nav_down(self):
        if not self._renaming and self._nav_index < len(self._sessions) - 1:
            self._nav_index += 1; self._render_list()

    def action_close(self):
        if self._renaming:
            self._renaming = False
            self.query_one("#rename-input", Input).remove()
            return
        self.dismiss(None)

    def action_new_session(self):
        self.dismiss("__new__")

    def action_delete_session(self):
        if self._renaming: return
        if self._sessions:
            sid = self._sessions[self._nav_index].id
            self.dismiss(f"__delete__:{sid}")

    def action_rename_session(self):
        if self._renaming or not self._sessions: return
        self._renaming = True
        s = self._sessions[self._nav_index]
        self.query_one("#rename-input", Input).remove() if self.query("#rename-input") else None
        box = self.query_one("#picker-box")
        box.mount(Input(value=s.title, id="rename-input"))
        self.query_one("#rename-input").focus()

    def on_input_submitted(self, event: Input.Submitted):
        new_title = event.value.strip()[:30] or "New Chat"
        s = self._sessions[self._nav_index]
        s.title = new_title
        sid = s.id
        self._renaming = False
        self.query_one("#rename-input", Input).remove()
        self._render_list()
        # Dismiss with rename result — caller handles persistence
        self.dismiss(f"__rename__:{sid}:{new_title}")

    CSS = """
    SessionPicker {
        align: center middle;
        background: rgba(0,0,0,0.4);
    }

    #picker-box {
        width: 50;
        max-height: 32;
        background: $surface;
        border: round $primary;
        padding: 0;
    }

    #picker-title {
        height: 1;
        background: $primary-darken-2;
        color: $text;
        content-align: center middle;
        text-style: bold;
    }

    #picker-list {
        height: 1fr;
        max-height: 24;
        padding: 1 0 0 0;
    }

    .session-row {
        height: 1;
        padding: 0 2;
    }

    .session-row:hover {
        background: $surface-lighten-1;
    }

    #picker-hint {
        height: 1;
        padding: 0 2;
        background: $surface-darken-1;
        color: $text-disabled;
        content-align: center middle;
        dock: bottom;
    }

    #rename-input {
        margin: 1 2;
    }
    """
