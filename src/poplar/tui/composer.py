from textual.widget import Widget
from textual.widgets import TextArea
from textual.binding import Binding
from textual.message import Message
from poplar.i18n import t
from poplar.tui.cmd_prompt import CommandSuggestion


class ComposerSubmit(Message):
    def __init__(self, text: str):
        self.text = text
        super().__init__()


class Composer(Widget):
    """Multi-line input field. Enter=send, Alt+Enter=newline. Typing '/' shows command suggestions."""

    BINDINGS = [
        Binding("enter", "send", "Send", show=False, priority=True),
    ]

    def compose(self):
        yield TextArea(id="input")

    def on_mount(self):
        textarea = self.query_one(TextArea)
        textarea.show_line_numbers = False
        textarea.tab_behavior = "focus"
        textarea.border_title = t("composer_placeholder")
        self._suggesting = False

    def on_text_area_changed(self, event: TextArea.Changed):
        """Show command suggestions when '/' is typed at start of line."""
        if self._suggesting:
            return
        text = event.text_area.text.strip()
        if text.startswith("/") and len(text) <= 2:
            self._suggesting = True
            app = self.app
            if app and hasattr(app, 'push_screen'):
                app.push_screen(CommandSuggestion(text), self._on_command_selected)

    def _on_command_selected(self, cmd: str | None):
        """Handle command selection from suggestion popup."""
        self._suggesting = False
        if cmd:
            textarea = self.query_one(TextArea)
            textarea.text = cmd + " "
            textarea.focus()

    def on_key(self, event):
        if event.key == "enter":
            event.stop()
            if event.ctrl:
                self.query_one(TextArea).insert("\n")
            else:
                self.action_send()
        elif event.key == "ctrl+j":
            event.stop()
            self.query_one(TextArea).insert("\n")

    def action_send(self):
        textarea = self.query_one(TextArea)
        text = textarea.text.strip()
        if text:
            self.post_message(ComposerSubmit(text=text))
            textarea.clear()

    DEFAULT_CSS = """
    Composer TextArea {
        height: auto;
        min-height: 1;
    }
    """
