from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Footer, Header, Static
from textual.worker import Worker, get_current_worker
from poplar.tui.chat_view import ChatView
from poplar.tui.composer import Composer, ComposerSubmit
from poplar.tui.session_picker import SessionPicker
from poplar.core.session import Session, Message, Role
from poplar.providers.deepseek import DeepSeekProvider
from poplar.i18n import t, get_model
from poplar.persistence.store import SessionStore
from poplar.tools.base import TOOL_DEFINITIONS, execute_tool
from poplar.persistence.cache import CacheManager, hash_messages
from poplar.core.context import ContextManager
from poplar.i18n import get_cache_config, get_context_config
import os
import json
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
from pathlib import Path

def _get_writable_dir(subdir: str) -> Path:
    """Get a writable directory, preferring ~/.poplar/<subdir> with fallback."""
    for base in (Path.home() / ".poplar", Path.cwd() / ".poplar"):
        candidate = base / subdir
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            test = candidate / ".write_test"
            test.touch()
            test.unlink()
            return candidate
        except (OSError, PermissionError):
            continue
    # Last resort: temp directory
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="poplar-")) / subdir
    tmp.mkdir(parents=True, exist_ok=True)
    return tmp

_log_dir = _get_writable_dir("logs")
_log_path = _log_dir / "app.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=str(_log_path),
    filemode='a'
)
logger = logging.getLogger(__name__)

SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠉"

SYSTEM_PROMPT = """You are Poplar, a helpful AI assistant with access to tools for file operations and command execution.
Use tools when appropriate: read_file, write_file, list_directory, run_command.
Keep responses concise and clear. Use Markdown formatting for code blocks, lists, and emphasis."""


class PoplarApp(App):
    """Main Poplar TUI application."""

    TITLE = "🌳 Poplar"
    SUB_TITLE = "AI Agent TUI v0.1.0"

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("ctrl+s", "session_picker", "Sessions", show=True),
        Binding("ctrl+n", "new_session", "New", show=True),
        Binding("ctrl+c", "copy_last", "Copy", show=True),
        Binding("ctrl+d", "delete_session", "Delete", show=False),
        Binding("escape", "cancel_request", "Cancel", show=True),
    ]

    CSS = """
    Screen {
        background: $surface;
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
        self.store = SessionStore()
        api_key = os.getenv("DEEPSEEK_API_KEY", "your-api-key-here")
        model = get_model()
        self.provider = DeepSeekProvider(api_key=api_key, model=model)
        
        # Load existing session or create default
        sessions = self.store.list_sessions()
        if sessions:
            self.session = self.store.get_session(sessions[0].id)
            # Count non-system messages on load
            self._message_count = sum(1 for m in self.session.messages if m.role != Role.SYSTEM)
            self._first_message = self._message_count == 0
            logger.info("Loaded existing session: %s (%d messages)", self.session.id, self._message_count)
        else:
            self.session = self.store.create_session(title="New Chat")
            self._message_count = 0
            self._first_message = True
            logger.info("Created new session: %s", self.session.id)
        
        self._thinking = False
        self._spinner_index = 0
        self._current_worker = None
        self._total_tokens = 0
        self._thinking_start_time = 0
        self._streaming = False
        self._streaming_msg = None
        self._pending_count = 0
        self._compress_timer = None

        # Context manager for smart summarization
        ctx_cfg = get_context_config()
        self.context_mgr = ContextManager(
            max_tokens=ctx_cfg["max_tokens"],
            auto_compress_at=ctx_cfg["auto_compress_at"],
            keep_recent_exchanges=ctx_cfg["keep_recent_exchanges"],
        )
        logger.info("Provider initialized with API key: %s...%s", api_key[:6], api_key[-4:])

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield ChatView(id="chat")
        yield Composer(id="composer")
        yield StatusFooter(self)
        yield Footer()

    def on_mount(self):
        """Called when the app is mounted."""
        self._load_session_messages()

    def _load_session_messages(self):
        """Load current session messages into ChatView."""
        chat_view = self.query_one(ChatView)
        chat_view.messages = list(self.session.messages)

    def action_session_picker(self):
        """Open session picker modal (Ctrl+S)."""
        sessions = self.store.list_sessions()
        self.push_screen(SessionPicker(sessions, self.session.id), self._handle_picker_result)

    def _handle_picker_result(self, result):
        """Handle result from session picker dialog."""
        if result is None:
            return

        if result == "__new__":
            self._create_session()
            return

        if isinstance(result, str) and result.startswith("__delete__:"):
            self._do_delete_session(result.split(":", 1)[1])
            return

        if isinstance(result, str) and result.startswith("__rename__:"):
            parts = result.split(":", 2)
            self.store.update_title(parts[1], parts[2])
            if self.session.id == parts[1]:
                self.session.title = parts[2]
            return

        # result is a session_id - switch to it
        if result != self.session.id:
            logger.info("Switching to session: %s", result)
            self.session = self.store.get_session(result)
            self._message_count = sum(1 for m in self.session.messages if m.role != Role.SYSTEM)
            self._first_message = self._message_count == 0
            self._load_session_messages()
            self._update_status_bar()

    def action_new_session(self):
        """Create a new session (Ctrl+N)."""
        self._create_session()

    def _create_session(self):
        logger.info("Creating new session")
        self.session = self.store.create_session(title="New Chat")
        self._message_count = 0
        self._first_message = True
        self._load_session_messages()
        self._update_status_bar()

    def action_copy_last(self):
        """Copy the last assistant response to clipboard (Ctrl+C)."""
        for m in reversed(self.session.messages):
            if m.role == Role.ASSISTANT and m.content and not m.tool_calls:
                self.copy_to_clipboard(m.content)
                self.notify(t("copied"))
                return
        self.notify(t("no_response"))

    def _do_delete_session(self, session_id: str):
        """Delete a session. If deleting current, switch to another."""
        sessions = self.store.list_sessions()
        is_current = session_id == self.session.id

        if len(sessions) <= 1:
            self.store.delete_session(session_id)
            self.session = self.store.create_session(session_id=session_id, title="New Chat")
            self._message_count = 0
            self._first_message = True
            self._load_session_messages()
            self._update_status_bar()
            self.notify(t("session_cleared"))
            return

        logger.info("Deleting session: %s", session_id)
        self.store.delete_session(session_id)

        if is_current:
            # Switch to another session only if we deleted the current one
            sessions = self.store.list_sessions()
            new_session = self.store.get_session(sessions[0].id)
            if new_session:
                self.session = new_session
                self._message_count = sum(1 for m in self.session.messages if m.role != Role.SYSTEM)
                self._first_message = self._message_count == 0
                self._load_session_messages()
                self._update_status_bar()
        self.notify(t("session_deleted"))

    def _update_status_bar(self):
        """Update the status bar display."""
        try:
            footer = self.query_one(StatusFooter)
            footer.update(footer.render())
        except Exception:
            pass

    def on_composer_submit(self, event: ComposerSubmit):
        """Handle user message submission."""
        text = event.text.strip()

        # Handle /commands
        if text == "/compress":
            self._compress_conversation()
            return
        if text == "/context":
            self._show_context_info()
            return
        # If a response is streaming, queue this message for later
        if self._streaming:
            user_msg = Message(role=Role.USER, content=event.text)
            self.session.add_message(user_msg)
            self.store.save_message(self.session.id, user_msg)
            chat_view = self.query_one(ChatView)
            chat_view.add_message(user_msg)
            self._message_count += 1
            self._pending_count += 1
            return

        # Auto-title session on first user message
        if self._first_message and self.session.title == "New Chat":
            title = event.text[:30].strip()
            if title:
                self.session.title = title
                self.store.update_title(self.session.id, title)
            self._first_message = False

        # 1. Immediately display user message
        user_msg = Message(role=Role.USER, content=event.text)
        self.session.add_message(user_msg)
        self.store.save_message(self.session.id, user_msg)
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

        # 3. Start API call after brief delay to let spinner render
        self._start_timer = self.set_timer(0.3, self._start_api_call)

    def _start_api_call(self):
        """Start the threaded API worker."""
        self._start_timer = None
        self._streaming = True
        logger.info("Sending message to API")
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
        if self._thinking or self._streaming:
            logger.info("User cancelled API request")
            self._stop_spinner()
            
            if hasattr(self, '_start_timer') and self._start_timer:
                self._start_timer.stop()
                self._start_timer = None
            
            if self._current_worker and self._current_worker.is_running:
                self._current_worker.cancel()
            
            chat_view = self.query_one(ChatView)
            self.session.messages = [m for m in self.session.messages if not self._is_thinking_msg(m)]
            chat_view.messages = [m for m in chat_view.messages 
                                 if not self._is_thinking_msg(m) 
                                 and m is not self._streaming_msg]
            chat_view.chat_display.update_messages(chat_view.messages)
            
            cancel_msg = Message(role=Role.SYSTEM, content=t("request_cancelled"))
            self.session.add_message(cancel_msg)
            chat_view.add_message(cancel_msg)
            
            self._streaming = False
            self._pending_count = 0
            self._update_status_bar()
            self.notify(t("notify_cancelled"))
            self._check_pending()

    def _get_api_messages(self):
        """Get messages for API call, excluding thinking messages."""
        meaningful = [m for m in self.session.messages if not self._is_thinking_msg(m)]
        system_msg = Message(role=Role.SYSTEM, content=SYSTEM_PROMPT)
        return [system_msg] + meaningful

    def _fetch_response(self):
        """Worker function - supports tool calling with multi-turn and API caching."""
        worker = get_current_worker()
        max_turns = 3

        # Cache setup (only on first turn)
        api_cache = CacheManager() if get_cache_config().get("enabled", True) else None
        api_cache_key = None
        api_cache_ttl = get_cache_config().get("api_response_ttl", 3600)

        for turn in range(max_turns):
            if worker.is_cancelled:
                return

            accumulated = []
            tool_calls = []
            last_error = None

            # Check API cache on first turn
            if turn == 0 and api_cache:
                api_messages = self._get_api_messages()
                api_cache_key = "api:" + hash_messages(api_messages)
                cached = api_cache.get(api_cache_key)
                if cached is not None:
                    logger.info("API cache hit for %s", api_cache_key)
                    self.call_from_thread(self._stop_spinner)
                    if not worker.is_cancelled:
                        self.call_from_thread(self._finalize_streaming, cached)
                        self.call_from_thread(self.notify, "📦 [dim]Cached response[/dim]")
                    return

            for attempt in range(3):
                if worker.is_cancelled:
                    return
                try:
                    api_messages = self._get_api_messages()
                    for chunk in self.provider.stream_sync(api_messages, tools=TOOL_DEFINITIONS):
                        if worker.is_cancelled:
                            return
                        if chunk["type"] == "content":
                            accumulated.append(chunk["text"])
                            self.call_from_thread(self._update_streaming, "".join(accumulated))
                        elif chunk["type"] == "tool_call":
                            tool_calls.append(chunk)
                    break  # Success
                except Exception as e:
                    last_error = e
                    if not self._is_retryable(str(e)):
                        break
                    if attempt < 2:
                        wait = (2 ** attempt) * 0.5
                        logger.warning("Retry %d/3 after %.1fs", attempt + 1, wait)
                        time.sleep(wait)
                        accumulated = []
                        tool_calls = []

            if last_error and not tool_calls and not accumulated:
                logger.error("API call failed: %s", str(last_error), exc_info=True)
                if not worker.is_cancelled:
                    self.call_from_thread(self._show_error, str(last_error))
                return

            content = "".join(accumulated)

            if tool_calls:
                # Build proper tool_calls format for assistant message
                formatted_calls = []
                for tc in tool_calls:
                    try:
                        parsed_args = json.loads(tc["arguments"])
                    except json.JSONDecodeError:
                        parsed_args = {}
                    formatted_calls.append({
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": tc["arguments"]
                        }
                    })

                # Add assistant message with tool_calls (content may be None from API)
                assistant_msg = Message(
                    role=Role.ASSISTANT,
                    content=content or "",
                    tool_calls=formatted_calls if formatted_calls else None
                )
                self.session.add_message(assistant_msg)
                self.store.save_message(self.session.id, assistant_msg)

                # Execute tools and add TOOL messages
                for tc in tool_calls:
                    name = tc["name"]
                    try:
                        args = json.loads(tc["arguments"])
                    except json.JSONDecodeError:
                        args = {}
                    result = execute_tool(name, args)
                    # Visual marker for cached tool results
                    display_content = f"[dim][cached][/dim] {result.content}" if getattr(result, '_cached', False) else result.content
                    tool_msg = Message(
                        role=Role.TOOL,
                        content=result.content,
                        tool_call_id=tc["id"],
                        name=name
                    )
                    self.session.add_message(tool_msg)
                    self.store.save_message(self.session.id, tool_msg)
                    self.call_from_thread(self._show_tool_result, name, display_content)

                continue  # Next turn

            if content:
                # Cache the response (only for pure Q&A, no tool calls)
                if api_cache and api_cache_key and not tool_calls:
                    api_cache.set(api_cache_key, content, api_cache_ttl, cache_type="api_response")
                self.call_from_thread(self._finalize_streaming, content)
                return
            else:
                if turn == 0:
                    self.call_from_thread(self._show_error, "Empty response from API")
                return

    def _is_retryable(self, error_msg: str) -> bool:
        """Check if an API error is retryable (network, rate limit, server error)."""
        retryable = ["timeout", "connection", "rate_limit", "server_error", "503", "502", "429", "overloaded"]
        msg_lower = error_msg.lower()
        return any(kw in msg_lower for kw in retryable)

    def _show_tool_result(self, name: str, content: str):
        """Show tool execution result as a system message."""
        chat_view = self.query_one(ChatView)
        preview = content[:500] + "..." if len(content) > 500 else content
        tool_msg = Message(role=Role.SYSTEM, content=f"{t('tool_result_prefix', name=name)}\n{preview}")
        chat_view.add_message(tool_msg)
        chat_view.scroll_end(animate=False)

    def _update_streaming(self, content: str):
        """Called when a streaming chunk arrives."""
        chat_view = self.query_one(ChatView)

        if self._thinking:
            self._stop_spinner()
            self.session.messages = [m for m in self.session.messages if not self._is_thinking_msg(m)]
            chat_view.messages = [m for m in chat_view.messages if not self._is_thinking_msg(m)]
            self._streaming_msg = Message(role=Role.ASSISTANT, content=content)
            chat_view.messages = chat_view.messages + [self._streaming_msg]
        else:
            # Update or append - don't overwrite if content is shorter (new turn)
            if self._streaming_msg is not None:
                self._streaming_msg.content = content
            else:
                self._streaming_msg = Message(role=Role.ASSISTANT, content=content)
                chat_view.messages = chat_view.messages + [self._streaming_msg]
            chat_view.messages = chat_view.messages.copy()
        chat_view.chat_display.update_messages(chat_view.messages)
        chat_view.scroll_end(animate=False)

    def _finalize_streaming(self, content: str):
        """Called when streaming completes."""
        assistant_msg = Message(role=Role.ASSISTANT, content=content)
        self.session.add_message(assistant_msg)
        self.store.save_message(self.session.id, assistant_msg)
        self._message_count += 1
        self._total_tokens += max(1, len(content) // 3)
        self._update_status_bar()
        self._streaming = False
        logger.info("Streaming response finalized")
        self._check_pending()

        # Auto-compress if token count exceeds threshold
        if self.context_mgr.should_compress(self._total_tokens):
            logger.info("Token count %d exceeds threshold, auto-compressing", self._total_tokens)
            # Delay to avoid blocking UI after stream finalization
            if self._compress_timer:
                self._compress_timer.reset()
            self._compress_timer = self.set_timer(0.5, self._compress_conversation)

    def _check_pending(self):
        """If user queued input during streaming, process it now."""
        count = self._pending_count
        if count > 0:
            self._pending_count = 0
            chat_view = self.query_one(ChatView)
            thinking_msg = Message(role=Role.SYSTEM, content=f"⠋ {t('thinking')}...")
            chat_view.add_message(thinking_msg)
            self._thinking = True
            self._spinner_index = 0
            self._thinking_start_time = time.time()
            self._animate_spinner()
            self._update_status_bar()
            self._start_timer = self.set_timer(0.3, self._start_api_call)

    def _compress_conversation(self):
        """Compress earlier messages using LLM summarization (runs in worker thread)."""
        self.notify(t("compress_start"))

        # Show a system message indicating compression
        chat_view = self.query_one(ChatView)
        compress_msg = Message(
            role=Role.SYSTEM,
            content=f"🔄 {t('compress_start')}"
        )
        chat_view.add_message(compress_msg)
        chat_view.scroll_end(animate=False)

        # Run compression in a background thread to avoid blocking the UI
        self.run_worker(self._do_compress, thread=True)

    def _do_compress(self):
        """Worker thread: perform the actual summarization."""
        worker = get_current_worker()
        ctx = self.context_mgr

        old_msgs, recent_msgs = ctx.get_summarizable_messages(
            self.session.messages
        )
        if not old_msgs or len(old_msgs) < 2:
            self.call_from_thread(self.notify, t("compress_done") + " — nothing to compress")
            return

        try:
            # Build summarization prompt
            prompt = ctx.build_summary_prompt(old_msgs)
            logger.info("Compressing %d messages...", len(old_msgs))

            # Call API (blocks this thread, not the UI)
            response = self.provider.chat(
                [Message(role=Role.USER, content=prompt)]
            )
            if worker.is_cancelled:
                return

            summary = response.content.strip()

            # Apply compression on main thread
            self.call_from_thread(self._apply_compression, summary, recent_msgs)

        except Exception as e:
            logger.error("Compression failed: %s", str(e), exc_info=True)
            self.call_from_thread(self.notify, f"[red]{t('error')}: {e}[/red]")

    def _apply_compression(self, summary: str, recent_msgs: list):
        """Main thread: apply compression result to session and UI."""
        ctx = self.context_mgr
        ctx.apply_compression(self.session, summary, recent_msgs)
        self._total_tokens = ctx.get_cumulative_token_count(self.session)

        # Reload chat view
        chat_view = self.query_one(ChatView)
        chat_view.messages = list(self.session.messages)
        chat_view.chat_display.update_messages(chat_view.messages)
        chat_view.scroll_end(animate=False)

        self._update_status_bar()
        self.notify(t("compress_done"))
        logger.info("Compression complete")

    def _show_context_info(self):
        """Show current context status as a system message."""
        from poplar.core.context import estimate_tokens, messages_token_count

        total_msgs = len(self.session.messages)
        user_msgs = sum(1 for m in self.session.messages if m.role == Role.USER)
        assistant_msgs = sum(1 for m in self.session.messages if m.role == Role.ASSISTANT)
        system_msgs = sum(1 for m in self.session.messages if m.role == Role.SYSTEM)
        tool_msgs = sum(1 for m in self.session.messages if m.role == Role.TOOL)

        token_est = messages_token_count(self.session.messages)
        threshold = int(self.context_mgr.max_tokens * self.context_mgr.auto_compress_at)
        pct = round(token_est / self.context_mgr.max_tokens * 100, 1)

        has_summary = any(
            m.role == Role.SYSTEM and m.content.startswith("[Summary")
            for m in self.session.messages
        )

        lines = [
            f"[bold]📊 Context Info[/bold]",
            f"Model: {self.provider.model}",
            f"Messages: {total_msgs} total ({user_msgs} user, {assistant_msgs} assistant, {system_msgs} system, {tool_msgs} tool)",
            f"Token estimate: {token_est} / {self.context_mgr.max_tokens} ({pct}%)",
            f"Auto-compress threshold: {threshold} tokens ({int(self.context_mgr.auto_compress_at * 100)}%)",
            f"Keep recent: {self.context_mgr.keep_recent_exchanges} exchanges",
            f"Has summary: {'✅' if has_summary else '❌'}",
            f"Total tokens (tracked): {self._total_tokens}",
            "",
            f"[dim]/compress — manually compress[/dim]",
        ]

        msg = Message(role=Role.SYSTEM, content="\n".join(lines))
        chat_view = self.query_one(ChatView)
        chat_view.add_message(msg)
        chat_view.scroll_end(animate=False)

    def _is_thinking_msg(self, m: Message) -> bool:
        """Check if a message is a thinking/spinner indicator."""
        if m.role != Role.SYSTEM:
            return False
        content_lower = m.content.lower()
        return "thinking" in content_lower or t("thinking").lower() in content_lower

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
        self.store.save_message(self.session.id, error_msg)
        chat_view.add_message(error_msg)
        self._update_status_bar()
        self._streaming = False
        self._check_pending()
