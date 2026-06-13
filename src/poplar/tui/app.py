from textual.app import App, ComposeResult
from poplar.tui.chat_view import ChatView
from poplar.tui.composer import Composer, ComposerSubmit
from poplar.core.session import Session, Message, Role
from poplar.providers.deepseek import DeepSeekProvider
import os


class PoplarApp(App):
    """Main Poplar TUI application."""

    CSS = """
    ChatView {
        height: 80%;
        border: solid green;
    }

    Composer {
        height: 20%;
        border: solid blue;
    }
    """

    def __init__(self):
        super().__init__()
        self.session = Session(id="default", title="New Chat")
        api_key = os.getenv("DEEPSEEK_API_KEY", "your-api-key-here")
        self.provider = DeepSeekProvider(api_key=api_key)

    def compose(self) -> ComposeResult:
        yield ChatView(id="chat")
        yield Composer(id="composer")

    def on_composer_submit(self, event: ComposerSubmit):
        """Handle user message submission."""
        # Add user message to session
        user_msg = Message(role=Role.USER, content=event.text)
        self.session.add_message(user_msg)

        # Update chat view
        chat_view = self.query_one(ChatView)
        chat_view.add_message(user_msg)

        # Get response from provider
        try:
            response = self.provider.chat(self.session.messages)
            assistant_msg = Message(role=Role.ASSISTANT, content=response.content)
            self.session.add_message(assistant_msg)
            chat_view.add_message(assistant_msg)
        except Exception as e:
            error_msg = Message(role=Role.ASSISTANT, content=f"Error: {str(e)}")
            self.session.add_message(error_msg)
            chat_view.add_message(error_msg)
