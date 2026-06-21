"""Chat message display widgets."""

from textual.widgets import Static
from textual.containers import ScrollableContainer, Horizontal
from textual.reactive import reactive
from rich.text import Text
from rich.panel import Panel
from rich.markdown import Markdown
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
        Text(body),
        title=t("welcome_title"),
        border_style="cyan",
        padding=(1, 2),
    )
    return panel


class MessageContent(Static):
    """Renders the message body (Panel / Text)."""

    def __init__(self, message: Message):
        super().__init__()
        self._msg = message
        self._build()

    def _build(self):
        msg = self._msg
        if msg.role == Role.USER:
            title = f"👤 {t('title_you')}"
            self.update(Panel(
                Text(msg.content),
                title=title,
                border_style="blue",
                padding=(0, 1),
            ))
        elif msg.role == Role.ASSISTANT:
            title = f"🤖 {t('title_assistant')}"
            self.update(Panel(
                Markdown(msg.content),
                title=title,
                border_style="green",
                padding=(0, 1),
                expand=False,
            ))
        elif msg.role == Role.SYSTEM:
            self.update(Text(f"  {msg.content}", style="dim yellow"))
        elif msg.role == Role.TOOL:
            name = msg.name or "tool"
            preview = msg.content[:TOOL_RESULT_PREVIEW_CHARS] + "..." if len(msg.content) > TOOL_RESULT_PREVIEW_CHARS else msg.content
            lines = [f"{t('tool_result_prefix', name=name)}:"]
            for line in preview.split("\n")[:10]:
                lines.append(f"  {line}")
            self.update(Text("\n".join(lines), style="dim"))


class CopyButton(Static):
    """Small clickable 'copy' label at the top-right of each message."""

    def __init__(self, msg: Message):
        super().__init__("copy")
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


class MessageWidget(Horizontal):
    """A single chat message with a copy button at top-right."""

    def __init__(self, message: Message):
        super().__init__()
        self._msg = message

    def compose(self):
        yield MessageContent(self._msg)
        yield CopyButton(self._msg)

    DEFAULT_CSS = """
    MessageWidget {
        height: auto;
        margin: 0 0 0 0;
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
        height: 100%;
        content-align: center middle;
    }
    """

    def __init__(self):
        super().__init__()
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

    def _rebuild(self, messages: list[Message]):
        self.remove_children()
        if not messages:
            self.mount(WelcomeWidget())
            self.scroll_end(animate=False)
            return
        MAX_VISIBLE = 100
        display_msgs = messages[-MAX_VISIBLE:] if len(messages) > MAX_VISIBLE else messages
        if len(messages) > MAX_VISIBLE:
            self.mount(Static(
                Text(f"  ... {len(messages) - MAX_VISIBLE} earlier messages hidden", style="dim")
            ))
        for msg in display_msgs:
            w = MessageWidget(msg)
            self.mount(w)
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
