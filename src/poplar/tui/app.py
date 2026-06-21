from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, Static
from textual.worker import get_current_worker
from poplar.tui.chat_view import ChatView, MessageWidget
from poplar.tui.composer import Composer, ComposerSubmit
from poplar.tui.session_picker import SessionPicker
from poplar.tui.help_screen import HelpScreen
from poplar.tui.cmd_prompt import CommandSuggestion
from poplar.tui.commands import COMMANDS, UI_ONLY_COMMANDS, find_command, dispatch_command
from poplar.core.session import Session, Message, Role
from poplar.providers import create_provider, get_available_providers
from poplar.i18n import t
from poplar.config import get_cache_config, get_context_config, get_active_provider_name, get_provider_config, save_config, load_config
from poplar.persistence.store import SessionStore
from poplar.tools.base import ToolResult, TOOL_RESULT_PREVIEW_CHARS
from poplar.core.context import ContextManager, estimate_tokens
from poplar.core.stats import stats
from poplar.core.agent_loop import AgentLoop, AgentTurn
from poplar.core.trust import is_workspace_trusted, trust_workspace
from poplar.tui.trust_screen import TrustScreen
from poplar.utils import get_writable_dir, SPINNER_CHARS, is_thinking_message
import json
import logging
import os
import time
from datetime import datetime


class StatusFooter(Static):
    """Custom status bar that displays model, token count, and status."""

    def __init__(self, app_instance, **kwargs):
        super().__init__(**kwargs)
        self.app_instance = app_instance

    def on_mount(self):
        self.update(self.render())

    def render(self):
        provider = self.app_instance._provider_name
        model = self.app_instance.provider.model
        tokens = self.app_instance._total_tokens
        messages = self.app_instance._message_count

        return f"[bold]{provider}:{model}[/bold] | {t('status_tokens')}: {tokens} | {t('status_messages')}: {messages}"


# Configure logging
from pathlib import Path
_log_dir = get_writable_dir("logs")
_log_path = _log_dir / "app.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=str(_log_path),
    filemode='a'
)
logger = logging.getLogger(__name__)


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

        # Create provider from config
        self._provider_name = get_active_provider_name()
        prov_cfg = get_provider_config()
        self.provider = create_provider(prov_cfg["name"], prov_cfg["config"])
        
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

        # Recalculate token count from loaded session (after context_mgr init)
        if self._message_count > 0:
            self._total_tokens = self.context_mgr.get_cumulative_token_count(self.session)

        logger.info("Provider initialized: %s (model: %s)", self._provider_name, self.provider.model)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield ChatView(id="chat")
        yield CommandSuggestion(id="cmd-suggest")
        yield Composer(id="composer")
        yield StatusFooter(self)
        yield Footer()

    def on_mount(self):
        """Called when the app is mounted."""
        from pathlib import Path
        if not is_workspace_trusted(Path.cwd()):
            self.push_screen(TrustScreen(Path.cwd()), self._handle_trust_result)
        else:
            self._load_session_messages()

    def _handle_trust_result(self, trusted: bool):
        """Handle result of workspace trust prompt."""
        from pathlib import Path
        if trusted:
            trust_workspace(Path.cwd())
            self._load_session_messages()
        else:
            self.exit()

    def _load_session_messages(self):
        """Load current session messages into ChatView."""
        chat_view = self.query_one(ChatView)
        chat_view.messages = list(self.session.messages)

    def action_session_picker(self):
        """Open session picker modal (Ctrl+S)."""
        sessions = self.store.list_sessions()
        self.push_screen(SessionPicker(sessions, self.session.id), self._handle_picker_result)

    def _handle_picker_result(self, result: str | None):
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

    def _clear_session(self):
        """Clear all messages from the current session."""
        logger.info("Clearing session: %s", self.session.id)
        self.store.delete_session(self.session.id)
        self.session = self.store.create_session(session_id=self.session.id, title="New Chat")
        self._message_count = 0
        self._first_message = True
        self._total_tokens = 0
        chat_view = self.query_one(ChatView)
        chat_view.messages = []
        self._update_status_bar()
        self.notify("Session cleared")

    def _update_status_bar(self):
        """Update the status bar display."""
        try:
            footer = self.query_one(StatusFooter)
            footer.update(footer.render())
        except Exception:  # Widget not yet mounted during startup
            pass

    def on_composer_submit(self, event: ComposerSubmit):
        """Handle user message submission."""
        text = event.text.strip()

        # Handle /commands — echo as user message (skip pure UI commands)
        if text.startswith("/") and text not in UI_ONLY_COMMANDS:
            chat_view = self.query_one(ChatView)
            user_msg = Message(role=Role.USER, content=event.text)
            self.session.add_message(user_msg)
            self.store.save_message(self.session.id, user_msg)
            chat_view.add_message(user_msg)

        # Dispatch via command registry (single source of truth)
        if dispatch_command(self, text):
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
        stats.record_user_message()
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
        self._spinner_index = (self._spinner_index + 1) % len(SPINNER_CHARS)
        frame = SPINNER_CHARS[self._spinner_index]
        elapsed = int(time.time() - self._thinking_start_time)
        chat_view = self.query_one(ChatView)

        # Update thinking message display using widget update
        chat_view.update_message_widget(
            predicate=lambda w: hasattr(w, '_msg') and is_thinking_message(w._msg),
            make_message=lambda w: Message(
                role=Role.SYSTEM,
                content=f"{frame} {t('thinking')}... ({t('esc_to_cancel')}, {elapsed}{t('seconds')})"
            ),
        )
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
            self.session.messages = [m for m in self.session.messages if not is_thinking_message(m)]
            # Also remove streaming msg from session if present
            if self._streaming_msg and self._streaming_msg in self.session.messages:
                self.session.messages.remove(self._streaming_msg)

            # Rebuild from session (removes stale widgets)
            chat_view._rebuild(self.session.messages)
            
            cancel_msg = Message(role=Role.SYSTEM, content=t("request_cancelled"))
            self.session.add_message(cancel_msg)
            w = MessageWidget(cancel_msg)
            chat_view.mount(w)
            
            self._streaming = False
            self._pending_count = 0
            self._update_status_bar()
            self.notify(t("notify_cancelled"))
            self._check_pending()

    def _fetch_response(self):
        """Worker function — delegates to AgentLoop for LLM+tool orchestration."""
        worker = get_current_worker()

        loop = AgentLoop(self.provider)

        for turn_result in loop.run_iter(
            self.session,
            on_stream=lambda content: self.call_from_thread(self._update_streaming, content),
        ):
            if worker.is_cancelled:
                loop.cancel()
                return

            # --- Cached response ---
            if turn_result.cached:
                self.call_from_thread(self._stop_spinner)
                if not worker.is_cancelled:
                    self.call_from_thread(self._finalize_streaming, turn_result.content)
                    self.call_from_thread(self.notify, "📦 [dim]Cached response[/dim]")
                return

            # --- Error ---
            if turn_result.error:
                if not worker.is_cancelled:
                    self.call_from_thread(self._show_error, turn_result.error)
                return

            # --- Tool calls ---
            if turn_result.tool_calls:
                formatted = turn_result.tool_calls
                tool_names = [tc["function"]["name"] for tc in formatted]
                text = turn_result.content
                if not text.strip() and formatted:
                    text = "Called tool: `" + ", ".join(tool_names) + "`"

                # Persist assistant message with tool_calls
                assistant_msg = Message(
                    role=Role.ASSISTANT,
                    content=text or "",
                    tool_calls=formatted if formatted else None,
                )
                self.session.add_message(assistant_msg)
                self.store.save_message(self.session.id, assistant_msg)
                self._streaming_msg = None

                # Persist tool results
                for i, tc_result in enumerate(turn_result.tool_results):
                    if i < len(formatted):
                        tc_name = formatted[i]["function"]["name"]
                        tc_id = formatted[i]["id"]
                    else:
                        tc_name = "unknown"
                        tc_id = f"tc_{i}"

                    tool_msg = Message(
                        role=Role.TOOL,
                        content=tc_result.content,
                        tool_call_id=tc_id,
                        name=tc_name,
                    )
                    self.session.add_message(tool_msg)
                    self.store.save_message(self.session.id, tool_msg)
                    # Show cached marker if applicable
                    display = tc_result.content
                    if getattr(tc_result, "_cached", False):
                        display = f"[dim][cached][/dim] {display}"
                    self.call_from_thread(self._show_tool_result, tc_name, display)
                    stats.record_tool_call()

                continue  # Next turn

            # --- Final text response ---
            if turn_result.content:
                if not worker.is_cancelled:
                    self.call_from_thread(self._finalize_streaming, turn_result.content)
                return

            # Fallback
            if not worker.is_cancelled:
                self.call_from_thread(
                    self._finalize_streaming,
                    "Tool execution completed. You can continue the conversation.",
                )
    def _show_tool_result(self, name: str, content: str):
        """Show tool execution result as a system message (mount directly, no reactive)."""
        chat_view = self.query_one(ChatView)
        preview = content[:TOOL_RESULT_PREVIEW_CHARS] + "..." if len(content) > TOOL_RESULT_PREVIEW_CHARS else content
        tool_msg = Message(role=Role.SYSTEM, content=f"{t('tool_result_prefix', name=name)}\n{preview}")
        w = MessageWidget(tool_msg)
        chat_view.mount(w)
        chat_view.scroll_end(animate=False)

    def _update_streaming(self, content: str):
        """Called when a streaming chunk arrives."""
        chat_view = self.query_one(ChatView)

        if self._thinking:
            self._stop_spinner()
            self.session.messages = [m for m in self.session.messages if not is_thinking_message(m)]

            # Remove thinking message widget
            for child in list(chat_view.children):
                if isinstance(child, MessageWidget) and is_thinking_message(child._msg):
                    child.remove()

            self._streaming_msg = Message(role=Role.ASSISTANT, content=content)
            # Mount streaming widget
            w = MessageWidget(self._streaming_msg)
            chat_view.mount(w)
        else:
            # Update existing widget or mount new one
            if self._streaming_msg is not None:
                self._streaming_msg.content = content
                chat_view.update_message_widget(
                    predicate=lambda w: hasattr(w, '_msg') and w._msg is self._streaming_msg,
                    make_message=lambda w: self._streaming_msg,
                )
            else:
                self._streaming_msg = Message(role=Role.ASSISTANT, content=content)
                w = MessageWidget(self._streaming_msg)
                chat_view.mount(w)

        chat_view.scroll_end(animate=False)

    def _finalize_streaming(self, content: str):
        """Called when streaming completes."""
        assistant_msg = Message(role=Role.ASSISTANT, content=content)
        self.session.add_message(assistant_msg)
        self.store.save_message(self.session.id, assistant_msg)
        self._message_count += 1
        self._total_tokens += max(1, estimate_tokens(content))
        stats.record_assistant_message()
        stats.record_api_success(completion_tokens=estimate_tokens(content))
        self._streaming_msg = None

        # Sync chat view with session (rebuilds all widgets from session.messages)
        chat_view = self.query_one(ChatView)
        chat_view.messages = list(self.session.messages)

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
        ctx = self.context_mgr
        old_msgs, _ = ctx.get_summarizable_messages(self.session.messages)
        if not old_msgs or len(old_msgs) < 2:
            lines = [
                "**Compression skipped**",
                "",
                f"You only have {len(self.session.messages)} message(s) in total.",
                f"Need at least {ctx.keep_recent_exchanges + 1} user exchanges to compress.",
                "",
                "Keep chatting and try again later.",
            ]
            msg = Message(role=Role.ASSISTANT, content="\n".join(lines))
            self.session.add_message(msg)
            self.store.save_message(self.session.id, msg)
            chat_view = self.query_one(ChatView)
            chat_view.add_message(msg)
            chat_view.scroll_end(animate=False)
            return

        self.notify(t("compress_start"))
        chat_view = self.query_one(ChatView)
        compress_msg = Message(role=Role.SYSTEM, content=f"🔄 {t('compress_start')}")
        chat_view.add_message(compress_msg)
        chat_view.scroll_end(animate=False)

        self.run_worker(self._do_compress, thread=True)

    def _do_compress(self):
        """Worker thread: perform the actual summarization."""
        worker = get_current_worker()
        ctx = self.context_mgr

        old_msgs, _ = ctx.get_summarizable_messages(
            self.session.messages
        )

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
            self.call_from_thread(self._apply_compression, summary)

        except Exception as e:
            logger.error("Compression failed: %s", str(e), exc_info=True)
            self.call_from_thread(self.notify, f"[red]{t('error')}: {e}[/red]")

    def _apply_compression(self, summary: str):
        """Main thread: append summary to session without removing old messages."""
        ctx = self.context_mgr
        summary_msg = Message(
            role=Role.ASSISTANT,
            content=f"*Summary of earlier conversation*\n\n{summary}\n\n---\n📦 **{t('compress_done')}**"
        )
        # Add summary as new message, keep all old messages intact
        self.session.add_message(summary_msg)
        self.store.save_message(self.session.id, summary_msg)
        self._total_tokens = ctx.get_cumulative_token_count(self.session)

        # Append to chat view
        chat_view = self.query_one(ChatView)
        chat_view.add_message(summary_msg)
        chat_view.scroll_end(animate=False)

        self._update_status_bar()
        self.notify(t("compress_done"))
        logger.info("Compression complete")

    def _show_context_info(self):
        """Show current context status as a system message."""
        from poplar.core.context import messages_token_count

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
            "**📊 Context Info**",
            "",
            f"| Item | Value |",
            f"|------|-------|",
            f"| Model | {self.provider.model} |",
            f"| Messages | {total_msgs} total ({user_msgs} user, {assistant_msgs} assistant, {system_msgs} system, {tool_msgs} tool) |",
            f"| Token estimate | {token_est} / {self.context_mgr.max_tokens} ({pct}%) |",
            f"| Auto-compress at | {threshold} tokens ({int(self.context_mgr.auto_compress_at * 100)}%) |",
            f"| Keep recent | {self.context_mgr.keep_recent_exchanges} exchanges |",
            f"| Has summary | {'✅' if has_summary else '❌'} |",
            f"| Tracked tokens | {self._total_tokens} |",
            "",
            "*/compress — manually compress*",
        ]

        msg = Message(role=Role.ASSISTANT, content="\n".join(lines))
        self.session.add_message(msg)
        self.store.save_message(self.session.id, msg)
        chat_view = self.query_one(ChatView)
        chat_view.add_message(msg)
        chat_view.scroll_end(animate=False)

    def _show_stats(self):
        """Show performance statistics."""
        msg = Message(role=Role.ASSISTANT, content=stats.report())
        self.session.add_message(msg)
        self.store.save_message(self.session.id, msg)
        chat_view = self.query_one(ChatView)
        chat_view.add_message(msg)
        chat_view.scroll_end(animate=False)

    def _show_cmd_result(self, content: str):
        """Display a command result — first echo the command as user message, then the result."""
        msg = Message(role=Role.ASSISTANT, content=content)
        self.session.add_message(msg)
        self.store.save_message(self.session.id, msg)
        chat_view = self.query_one(ChatView)
        chat_view.add_message(msg)
        chat_view.scroll_end(animate=False)

    def _show_help(self):
        """Show help as a modal popup."""
        self.push_screen(HelpScreen())

    def _show_unknown_command(self, text: str):
        """Show help when an unknown command is typed. Silently ignore bare '/'."""
        if text.strip() == "/":
            return
        lines = [
            f"**Unknown command: {text.split()[0]}**",
            "",
            "Try **/help** to see available commands.",
        ]
        msg = Message(role=Role.ASSISTANT, content="\n".join(lines))
        self.session.add_message(msg)
        self.store.save_message(self.session.id, msg)
        chat_view = self.query_one(ChatView)
        chat_view.add_message(msg)
        chat_view.scroll_end(animate=False)

    def _handle_provider_command(self, text: str):
        """Handle /provider commands."""
        parts = text.split()
        cmd = parts[1] if len(parts) > 1 else "show"

        if cmd == "list":
            available = get_available_providers()
            current = self._provider_name
            lines = ["| Provider | Status |", "|----------|--------|"]
            for name in available:
                marker = "● active" if name == current else "○"
                lines.append(f"| {name} | {marker} |")
            msg = Message(role=Role.ASSISTANT, content="\n".join(lines))
            chat_view = self.query_one(ChatView)
            chat_view.add_message(msg)
            chat_view.scroll_end(animate=False)

        elif cmd == "set" and len(parts) >= 3:
            name = parts[2]
            if name not in get_available_providers():
                self.notify(f"[red]Unknown provider: {name}[/red]")
                return
            self._switch_provider(name)

        else:
            # Show current provider info (no API call — avoids UI freeze)
            lines = [
                f"**{self._provider_name}** · `{self.provider.model}`",
            ]
            msg = Message(role=Role.ASSISTANT, content="\n".join(lines))
            chat_view = self.query_one(ChatView)
            chat_view.add_message(msg)
            chat_view.scroll_end(animate=False)

    def _switch_provider(self, name: str):
        """Switch to a different provider at runtime."""
        try:
            config = load_config()
            prov_cfg = config.get("providers", {}).get(name, {})
            self.provider = create_provider(name, prov_cfg)
            self._provider_name = name

            # Persist to config
            config["provider"] = name
            save_config(config)

            self._update_status_bar()
            self.notify(f"Switched to [bold]{name}[/bold] ({self.provider.model})")
            logger.info("Switched provider to %s (model: %s)", name, self.provider.model)

            # Warn if API key is missing (except Ollama)
            if name != "ollama":
                api_key = prov_cfg.get("api_key") or os.getenv(f"{name.upper()}_API_KEY")
                if not api_key:
                    self.notify(
                        f"[yellow]No API key for {name}.[/yellow] "
                        f"Set in config or export {name.upper()}_API_KEY",
                        timeout=8,
                    )
        except Exception as e:
            logger.error("Failed to switch provider: %s", str(e), exc_info=True)
            self.notify(f"[red]Failed: {e}[/red]")

    def _export_session(self, text: str):
        """Export current session to a JSON file."""
        parts = text.split(maxsplit=1)
        path_str = parts[1] if len(parts) > 1 else f"poplar-session-{self.session.id}.json"
        path = Path(path_str).expanduser().resolve()

        try:
            data = {
                "poplar_session": True,
                "version": 1,
                "exported_at": datetime.now().isoformat(),
                "session": {
                    "title": self.session.title,
                    "created_at": self.session.created_at.isoformat() if self.session.created_at else None,
                    "messages": [m.to_dict() for m in self.session.messages],
                }
            }
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            self.notify(f"📤 Exported to {path.name}")
            logger.info("Session exported to %s", path)
        except Exception as e:
            logger.error("Export failed: %s", str(e), exc_info=True)
            self.notify(f"[red]Export failed: {e}[/red]")

    def _import_session(self, text: str):
        """Import a session from a JSON file."""
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            self.notify("[red]Usage: /import <path>[/red]")
            return
        path = Path(parts[1]).expanduser().resolve()

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not data.get("poplar_session"):
                self.notify("[red]Not a valid Poplar session file[/red]")
                return

            session_data = data["session"]
            title = session_data.get("title", "Imported Chat")

            new_session = self.store.create_session(title=title)
            for msg_dict in session_data.get("messages", []):
                msg = Message.from_dict(msg_dict)
                self.store.save_message(new_session.id, msg)

            self.session = self.store.get_session(new_session.id)
            self._message_count = sum(1 for m in self.session.messages if m.role != Role.SYSTEM)
            self._first_message = self._message_count == 0
            self._total_tokens = self.context_mgr.get_cumulative_token_count(self.session)
            chat_view = self.query_one(ChatView)
            chat_view.messages = list(self.session.messages)
            self._update_status_bar()
            self.notify(f"📥 Imported: {title} ({self._message_count} messages)")
            logger.info("Session imported from %s: %s", path, new_session.id)
        except Exception as e:
            logger.error("Import failed: %s", str(e), exc_info=True)
            self.notify(f"[red]Import failed: {e}[/red]")

    def _show_error(self, error: str):
        """Called on main thread when API call fails."""
        logger.error("Displaying error: %s", error[:100] if len(error) > 100 else error)
        stats.record_api_error()
        self._stop_spinner()
        chat_view = self.query_one(ChatView)

        # Remove thinking message widgets
        for child in list(chat_view.children):
            if isinstance(child, MessageWidget) and is_thinking_message(child._msg):
                child.remove()

        # Clean session messages
        self.session.messages = [m for m in self.session.messages if not is_thinking_message(m)]
        # Rebuild chat view to match session
        chat_view._rebuild(self.session.messages)

        # Show error as assistant message (mount directly, session already has it)
        error_msg = Message(role=Role.ASSISTANT, content=f"**{t('error')}: {error}**")
        self.session.add_message(error_msg)
        self.store.save_message(self.session.id, error_msg)
        # Rebuild to display error
        chat_view._rebuild(self.session.messages)
        chat_view.scroll_end(animate=False)
        self._update_status_bar()
        self._streaming = False
        self._check_pending()
