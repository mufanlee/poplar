from textual.widget import Widget
from textual.widgets import TextArea
from textual.message import Message


class ComposerSubmit(Message):
    """Message sent when user submits input."""
    def __init__(self, text: str):
        self.text = text
        super().__init__()


class Composer(Widget):
    """Multi-line input field for user messages."""

    def compose(self):
        self.text_area = TextArea(id="input")
        yield self.text_area

    def on_key(self, event):
        if event.key == "enter" and not event.shift:
            event.prevent_default()
            text = self.text_area.text
            if text.strip():
                self.post_message(ComposerSubmit(text=text))
                self.text_area.text = ""
