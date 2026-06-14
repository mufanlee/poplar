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
    """Multi-line input field. Enter=send, Ctrl+Enter=newline. Typing '/' shows command suggestions."""

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

    def on_text_area_changed(self, event: TextArea.Changed):
        """Show or hide command suggestions when '/' is typed."""
        text = event.text_area.text.strip()
        app = self.app
        if not app:
            return
        try:
            suggest = app.query_one("#cmd-suggest", CommandSuggestion)
        except Exception:
            return

        if text.startswith("/") and len(text) <= 2:
            suggest.show(text)
        else:
            suggest.hide()

    def on_key(self, event):
        if event.key == "enter":
            event.stop()
            # During Enter, if popup is visible, let popup handle it
            app = self.app
            if app:
                try:
                    suggest = app.query_one("#cmd-suggest", CommandSuggestion)
                    if suggest._visible:
                        suggest.action_select()
                        return
                except Exception:
                    pass
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
