"""Chat message display widgets."""

from textual.widgets import Static
from textual.containers import ScrollableContainer, Horizontal, Center
from textual.reactive import reactive
from rich.text import Text
from rich.panel import Panel
from rich.markdown import Markdown
from rich.color import Color
from poplar.core.session import Message, Role
from poplar.i18n import t
from poplar.tools.base import TOOL_RESULT_PREVIEW_CHARS


def build_welcome():
    """Build a centered welcome screen using Rich."""
    title = Text()
    title.append("P", style="bold cyan")
    title.append(" O ", style="bold yellow")
    title.append("P", style="bold cyan")
    title.append(" L ", style="bold yellow")
    title.append("A", style="bold cyan")
    title.append("R", style="bold yellow")

    body = Text()
    body.append("\n")
    body.append(title)
    body.append("\n")
    body.append(f"{t('welcome_version')} — {t('welcome_subtitle')}\n", style="dim")
    body.append("\n")
    body.append(f"{t('welcome_description')}\n", style="dim")
    body.append("\n")
    body.append(f"{t('welcome_features')}:\n", style="bold")
    body.append(f"  {t('welcome_feature1')}\n", style="")
    body.append(f"  {t('welcome_feature2')}\n", style="")
    body.append(f"  {t('welcome_feature3')}\n", style="")
    body.append("\n")
    body.append(f"{t('welcome_start')}\n", style="bold green")

    panel = Panel(
        body,
        title=t("welcome_title"),
        border_style="cyan",
        padding=(1, 2),
    )
    return panel


class MessageContent(Static):
    """Renders message body — plain text, Markdown, or tool output."""

    def __init__(self, message: Message):
        super().__init__()
        self._msg = message
        self._build()

    def _build(self):
        msg = self._msg
        if msg.role == Role.USER:
            self.update(Text(f"👤 You\n\n{msg.content}"))
        elif msg.role == Role.ASSISTANT:
            self.update(Markdown(msg.content))
        elif msg.role == Role.SYSTEM:
            self.update(Text(f"  {msg.content}", style="dim yellow"))
        elif msg.role == Role.TOOL:
            name = msg.name or "tool"
            preview = msg.content[:TOOL_RESULT_PREVIEW_CHARS] + "..." if len(msg.content) > TOOL_RESULT_PREVIEW_CHARS else msg.content
            body = f"🔧 {name}\n"
            for line in preview.split("\n")[:10]:
                body += f"  {line}\n"
            self.update(Text(body.rstrip(), style="dim"))


class CopyButton(Static):
    """Small clickable 'copy' label at the top-right of each message."""

    def __init__(self, msg: Message):
        super().__init__("[copy]")
        self._msg = msg

    def on_click(self):
        if self._msg.content:
            self.app.copy_to_clipboard(self._msg.content)
            self.app.notify(f"📋 Copied: {self._msg.content[:60]}...")

    DEFAULT_CSS = """
    CopyButton {
        width: 5;
        height: 1;
        text-align: center;
        color: $text-muted;
    }
    CopyButton:hover {
        color: $text;
        background: $accent 30%;
    }
    """


class MessageBar(Static):
class MessageWidget(Horizontal):
    """A single chat message: [colored left bar] [content] [copy]."""

    _BAR_COLORS = {
        Role.USER: "#2ac3de",
        Role.ASSISTANT: "#9ece6a",
        Role.TOOL: "#565f89",
    }

    def __init__(self, message: Message):
        super().__init__()
        self._msg = message
        bar_hex = self._BAR_COLORS.get(message.role, "#e0af68")
        self.styles.border_left = ("thick", Color.parse(bar_hex))

    def compose(self):
        yield MessageContent(self._msg)
        yield CopyButton(self._msg)

    DEFAULT_CSS = """
    MessageWidget {
        height: auto;
        margin: 1 0 0 0;
        padding: 0 0 0 1;
    }
    MessageContent {
        width: 1fr;
        height: auto;
    }
    """


class WelcomeWidget(Static):
    """Full-screen welcome widget."""

    DEFAULT_CSS = """
    WelcomeWidget {
        height: auto;
        width: auto;
    }
    """

    def on_mount(self):
        self.update(build_welcome())


class ChatView(ScrollableContainer):
    """Scrollable container for chat messages."""

    messages: reactive[list[Message]] = reactive([], init=False)

    DEFAULT_CSS = """
    ChatView {
        overflow-y: auto;
        overflow-x: auto;
        border: round $secondary;
        height: 1fr;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._rendered_count = 0

    def _rebuild(self, messages: list[Message]):
        # Incremental: only render new messages, reuse existing widgets
        if self._rendered_count <= len(messages) and self._rendered_count > 0:
            new_msgs = messages[self._rendered_count:]
            for msg in new_msgs:
                self.mount(MessageWidget(msg))
            self._rendered_count = len(messages)
            self.scroll_end(animate=False)
            return

        # Full rebuild (session switch, compression, initial load)
        self.remove_children()
        if not messages:
            self.mount(Center(WelcomeWidget()))
            self.scroll_end(animate=False)
            self._rendered_count = 0
            return
        MAX_VISIBLE = 100
        display_msgs = messages[-MAX_VISIBLE:] if len(messages) > MAX_VISIBLE else messages
        if len(messages) > MAX_VISIBLE:
            self.mount(Static(
                Text(f"  ... {len(messages) - MAX_VISIBLE} earlier messages hidden", style="dim")
            ))
        for msg in display_msgs:
            self.mount(MessageWidget(msg))
        self._rendered_count = len(messages)
        self.scroll_end(animate=False)

    def watch_messages(self, messages: list[Message]):
        self._rebuild(messages)

    def add_message(self, message: Message):
        self.messages = self.messages + [message]

    def add_system_message(self, content: str):
        widget = MessageWidget(Message(role=Role.SYSTEM, content=content))
        self.mount(widget)
        self.scroll_end(animate=False)
        return widget

    def update_message_widget(self, predicate, make_message):
        for child in self.children:
            if isinstance(child, MessageWidget) and predicate(child):
                new_msg = make_message(child)
                child._msg = new_msg
                for sub in child.query(MessageContent):
                    sub._msg = new_msg
                    sub._build()
                return
        self.messages = list(self.messages)
