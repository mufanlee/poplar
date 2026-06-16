"""Composer widget with slash command suggestions."""

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
    """Multi-line input. Enter=send, Ctrl+Enter=newline. '/' shows command suggestions."""

    BINDINGS = [
        Binding("enter", "send", "Send", show=False, priority=True),
    ]

    def compose(self):
        yield CommandSuggestion(id="cmd-suggest")
        yield TextArea(id="input")

    def on_mount(self):
        textarea = self.query_one(TextArea)
        textarea.show_line_numbers = False
        textarea.tab_behavior = "focus"
        textarea.border_title = t("composer_placeholder")

    def on_text_area_changed(self, event: TextArea.Changed):
        """Show or hide command suggestions when '/' is typed."""
        text = event.text_area.text.strip()
        suggest = self.query_one(CommandSuggestion)

        if text.startswith("/"):
            suggest.show(text)
        else:
            suggest.hide()

    def on_key(self, event):
        suggest = self.query_one(CommandSuggestion)
        if suggest.is_visible:
            if event.key == "enter" or event.key == "tab":
                event.stop()
                cmd, _ = suggest._selected()
                suggest.hide()
                if cmd:
                    textarea = self.query_one(TextArea)
                    textarea.text = cmd + " "  # type: ignore[assignment]
                    self.action_send()
                return
            elif event.key == "up":
                event.stop()
                suggest.action_nav_up()
                return
            elif event.key == "down":
                event.stop()
                suggest.action_nav_down()
                return
            elif event.key == "escape":
                event.stop()
                suggest.action_dismiss()
                self.query_one(TextArea).clear()
                return
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
