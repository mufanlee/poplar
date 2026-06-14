from textual.widget import Widget
from textual.widgets import Input
from textual.message import Message
from poplar.i18n import t


class ComposerSubmit(Message):
    """Message sent when user submits input."""
    def __init__(self, text: str):
        self.text = text
        super().__init__()


class Composer(Widget):
    """Input field for user messages."""

    def compose(self):
        yield Input(placeholder=t("composer_placeholder"), id="input")

    def on_input_submitted(self, event: Input.Submitted):
        """Handle Enter key - send message."""
        text = event.value
        if text.strip():
            self.post_message(ComposerSubmit(text=text))
            # Clear the input
            self.query_one(Input).value = ""
