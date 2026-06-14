from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Footer, Header, Static
from textual.worker import Worker, get_current_worker
from poplar.tui.chat_view import ChatView
from poplar.tui.composer import Composer, ComposerSubmit
from poplar.core.session import Session, Message, Role
from poplar.providers.deepseek import DeepSeekProvider
from poplar.i18n import t, get_model
import os
import logging
import time


class StatusFooter(Static):
    """Custom status bar that displays model, token count, and status."""

    def __init__(self, app_instance, **kwargs):
        super().__init__(**kwargs)
        self.app_instance = app_instance

    def on_mount(self):
        self.update(self.render())

    def render(self):
        model = self.app_instance.provider.model
        tokens = self.app_instance._total_tokens
        messages = self.app_instance._message_count

        return f"[bold]{model}[/bold] | {t('status_tokens')}: {tokens} | {t('status_messages')}: {messages}"


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='poplar.log',
    filemode='a'
)
logger = logging.getLogger(__name__)

SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠉"


class PoplarApp(App):
    """Main Poplar TUI application."""

    TITLE = "🌳 Poplar"
    SUB_TITLE = "AI Agent TUI v0.1.0"

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("ctrl+c", "quit", "Force quit", show=False),
        Binding("escape", "cancel_request", "Cancel", show=False),
    ]

    CSS = """
    Screen {
        background: $surface;
    }

    #main-container {
        layout: vertical;
        height: 1fr;
    }

    ChatView {
        height: 1fr;
        border: round $primary-darken-2;
        padding: 1;
        background: $surface;
        
        scrollbar-size: 1 1;
        scrollbar-background: $surface-darken-1;
        scrollbar-background-hover: $surface-darken-2;
        scrollbar-color: $primary-darken-1;
        scrollbar-color-active: $primary-lighten-1;
        scrollbar-color-hover: $primary;
        scrollbar-corner-color: $surface-darken-2;
        scrollbar-gutter: auto;
    }

    Composer {
        height: auto;
        border: round $accent-darken-2;
        padding: 1;
        background: $surface-darken-1;
    }

    StatusFooter {
        height: 1;
        background: $primary-darken-2;
        color: $text;
        padding: 0 1;
        content-align: center middle;
    }
    """

    def __init__(self):
        super().__init__()
        logger.info("Application starting")
        self.session = Session(id="default", title="New Chat")
        api_key = os.getenv("DEEPSEEK_API_KEY", "your-api-key-here")
        model = get_model()
        self.provider = DeepSeekProvider(api_key=api_key, model=model)
        self._thinking = False
        self._spinner_index = 0
        self._current_worker = None
        self._total_tokens = 0
        self._message_count = 0
        self._thinking_start_time = 0
        logger.info("Provider initialized with API key: %s...%s", api_key[:6], api_key[-4:])

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="main-container"):
            yield ChatView(id="chat")
            yield Composer(id="composer")
        yield StatusFooter(self)
        yield Footer()

    def _get_status_text(self):
        """Generate status bar text."""
        status = t("status_online") if self._thinking else t("status_ready")
        return f"[bold]{self.provider.model}[/bold] | {t('status_tokens')}: {self._total_tokens} | {t('status_messages')}: {self._message_count} | {status}"

    def _update_status_bar(self):
        """Update the status bar display."""
        try:
            footer = self.query_one(StatusFooter)
            footer.update(footer.render())
        except Exception:
            pass

    def on_composer_submit(self, event: ComposerSubmit):
        """Handle user message submission."""
        # 1. Immediately display user message
        user_msg = Message(role=Role.USER, content=event.text)
        self.session.add_message(user_msg)
        chat_view = self.query_one(ChatView)
        chat_view.add_message(user_msg)
        self._message_count += 1

        # 2. Show thinking indicator and start animation
        elapsed = 0
        thinking_msg = Message(role=Role.SYSTEM, content=f"⠋ {t('thinking')}... ({t('esc_to_cancel')}, {elapsed}{t('seconds')})")
        chat_view.add_message(thinking_msg)
        self._thinking = True
        self._spinner_index = 0
        self._thinking_start_time = time.time()
        self._animate_spinner()
        self._update_status_bar()

        # 3. Start API call in background thread
        logger.info("Sending message to API: %s...", event.text[:50])
        self._current_worker = self.run_worker(self._fetch_response, thread=True)

    def _animate_spinner(self):
        """Update spinner animation with braille character before 'Thinking...'."""
        if not self._thinking:
            return
        self._spinner_index = (self._spinner_index + 1) % len(SPINNER_FRAMES)
        frame = SPINNER_FRAMES[self._spinner_index]
        elapsed = int(time.time() - self._thinking_start_time)
        chat_view = self.query_one(ChatView)

        # Update thinking message display
        chat_view.messages = [
            Message(role=Role.SYSTEM, content=f"{frame} {t('thinking')}... ({t('esc_to_cancel')}, {elapsed}{t('seconds')})")
            if self._is_thinking_msg(m)
            else m
            for m in chat_view.messages
        ]
        chat_view.chat_display.update_messages(chat_view.messages)
        self.set_timer(0.1, self._animate_spinner)

    def _stop_spinner(self):
        """Stop the thinking animation."""
        self._thinking = False

    def action_cancel_request(self):
        """Cancel ongoing API request when ESC is pressed."""
        if self._thinking and self._current_worker:
            logger.info("User cancelled API request")
            self._stop_spinner()
            
            # Cancel the worker
            if self._current_worker.is_running:
                self._current_worker.cancel()
            
            # Remove thinking message
            chat_view = self.query_one(ChatView)
            self.session.messages = [m for m in self.session.messages if not self._is_thinking_msg(m)]
            chat_view.messages = [m for m in chat_view.messages if not self._is_thinking_msg(m)]
            chat_view.chat_display.update_messages(chat_view.messages)
            
            # Show cancellation message
            cancel_msg = Message(role=Role.SYSTEM, content=t("request_cancelled"))
            self.session.add_message(cancel_msg)
            chat_view.add_message(cancel_msg)
            
            self._update_status_bar()
            self.notify(t("notify_cancelled"))

    def _fetch_response(self):
        """Worker function - runs in background thread."""
        worker = get_current_worker()
        try:
            logger.info("API call started")
            response = self.provider.chat(self.session.messages)
            logger.info("API call successful, received %d tokens", response.usage.get('total_tokens', 0))
            if not worker.is_cancelled:
                self.call_from_thread(self._show_response, response.content, response.usage)
        except Exception as e:
            logger.error("API call failed: %s", str(e), exc_info=True)
            import traceback
            error_details = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            if not worker.is_cancelled:
                self.call_from_thread(self._show_error, error_details)

    def _is_thinking_msg(self, m: Message) -> bool:
        """Check if a message is a thinking/spinner indicator."""
        if m.role != Role.SYSTEM:
            return False
        content_lower = m.content.lower()
        return "thinking" in content_lower or t("thinking").lower() in content_lower

    def _show_response(self, content: str, usage: dict):
        """Called on main thread when response arrives."""
        logger.info("Displaying response: %s...", content[:50] if len(content) > 50 else content)
        self._stop_spinner()
        chat_view = self.query_one(ChatView)

        # Remove thinking messages
        self.session.messages = [m for m in self.session.messages if not self._is_thinking_msg(m)]
        chat_view.messages = [m for m in chat_view.messages if not self._is_thinking_msg(m)]
        chat_view.chat_display.update_messages(chat_view.messages)

        # Show assistant response
        assistant_msg = Message(role=Role.ASSISTANT, content=content)
        self.session.add_message(assistant_msg)
        chat_view.add_message(assistant_msg)
        
        # Update token count and status bar
        self._total_tokens += usage.get('total_tokens', 0)
        self._message_count += 1
        self._update_status_bar()
        
        logger.info("Response displayed successfully")

    def _show_error(self, error: str):
        """Called on main thread when API call fails."""
        logger.error("Displaying error: %s", error[:100] if len(error) > 100 else error)
        self._stop_spinner()
        chat_view = self.query_one(ChatView)

        # Remove thinking messages
        self.session.messages = [m for m in self.session.messages if not self._is_thinking_msg(m)]
        chat_view.messages = [m for m in chat_view.messages if not self._is_thinking_msg(m)]
        chat_view.chat_display.update_messages(chat_view.messages)

        # Show error as assistant message
        error_msg = Message(role=Role.ASSISTANT, content=f"[red]{t('error')}: {error}[/red]")
        self.session.add_message(error_msg)
        chat_view.add_message(error_msg)
        self._update_status_bar()
