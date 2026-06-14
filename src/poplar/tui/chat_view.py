"""Chat message display widgets — each message with a copy button."""

from textual.widgets import Static
from textual.containers import ScrollableContainer, Horizontal
from textual.reactive import reactive
from rich.align import Align
from rich.text import Text
from rich.panel import Panel
from rich.markdown import Markdown
from poplar.core.session import Message, Role
from poplar.i18n import t


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
        Align.center(body),
        title=t("welcome_title"),
        border_style="cyan",
        padding=(1, 2),
    )
    return Align.center(panel)


class MessageContent(Static):
    """Renders the message body (Panel / Text)."""

    def __init__(self, message: Message):
        super().__init__()
        self._msg = message
        self._build()

    def _build(self):
        msg = self._msg
        if msg.role == Role.USER:
            self.update(Panel(
                Text(msg.content),
                title=f"👤 {t('title_you')}",
                border_style="blue",
                padding=(0, 1),
            ))
        elif msg.role == Role.ASSISTANT:
            self.update(Panel(
                Markdown(msg.content),
                title=f"🤖 {t('title_assistant')}",
                border_style="green",
                padding=(0, 1),
                expand=False,
            ))
        elif msg.role == Role.SYSTEM:
            self.update(Text(f"  {msg.content}", style="dim yellow"))
        elif msg.role == Role.TOOL:
            name = msg.name or "tool"
            preview = msg.content[:500] + "..." if len(msg.content) > 500 else msg.content
            lines = [f"{t('tool_result_prefix', name=name)}:"]
            for line in preview.split("\n")[:10]:
                lines.append(f"  {line}")
            self.update(Text("\n".join(lines), style="dim"))


class CopyButton(Static):
    """A small clickable copy button shown at top-right of each message."""

    def __init__(self, parent_widget):
        super().__init__("📋")
        self._parent = parent_widget

    def on_click(self):
        """Copy the parent message content to clipboard."""
        content = self._parent._msg.content
        if content:
            self.app.copy_to_clipboard(content)
            self.app.notify(f"📋 Copied: {content[:60]}...")

    DEFAULT_CSS = """
    CopyButton {
        width: 3;
        height: 1;
        padding: 0 0 0 0;
        text-align: center;
        background: $surface-darken-2;
    }
    CopyButton:hover {
        background: $accent;
        color: $text;
    }
    """


class MessageWidget(Static):
    """A single chat message: Panel + copy button at top-right."""

    def __init__(self, message: Message):
        super().__init__()
        self._msg = message

    def compose(self):
        with Horizontal():
            yield MessageContent(self._msg)
            yield CopyButton(self)

    DEFAULT_CSS = """
    MessageWidget {
        height: auto;
        margin: 0 0 0 0;
    }
    MessageContent {
        height: auto;
        width: 1fr;
    }
    """


class WelcomeWidget(Static):
    """Full-screen welcome widget, shown when there are no messages."""

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
    """Scrollable container for chat messages. Each message has a copy button."""

    messages: reactive[list] = reactive([], init=False)

    DEFAULT_CSS = """
    ChatView {
        overflow-y: auto;
        overflow-x: auto;
        border: round $secondary;
        height: 1fr;
    }
    """

    def compose(self):
        from textual.containers import Vertical
        self.chat_display = Vertical()
        yield self.chat_display

    def _rebuild(self, messages: list[Message]):
        """Rebuild all message widgets in the display container."""
        self.chat_display.remove_children()

        if not messages:
            self.chat_display.mount(WelcomeWidget())
            self.scroll_end(animate=False)
            return

        MAX_VISIBLE = 100
        display_msgs = messages[-MAX_VISIBLE:] if len(messages) > MAX_VISIBLE else messages

        if len(messages) > MAX_VISIBLE:
            self.chat_display.mount(Static(
                Text(f"  ... {len(messages) - MAX_VISIBLE} earlier messages hidden", style="dim")
            ))

        for msg in display_msgs:
            self.chat_display.mount(MessageWidget(msg))

        self.scroll_end(animate=False)

    def watch_messages(self, messages: list[Message]):
        """Called when messages reactive changes."""
        self._rebuild(messages)

    def add_message(self, message: Message):
        """Append a message and trigger reactivity."""
        self.messages = self.messages + [message]

    def add_system_message(self, content: str):
        """Add a system message directly without triggering full rebuild."""
        widget = MessageWidget(Message(role=Role.SYSTEM, content=content))
        self.chat_display.mount(widget)
        self.scroll_end(animate=False)
        return widget

    def update_message_widget(self, predicate, make_message):
        """Find the first MessageWidget matching predicate and update its content.

        Args:
            predicate: callable(MessageWidget) -> bool
            make_message: callable(MessageWidget) -> Message, returns updated message
        """
        for child in self.chat_display.children:
            if isinstance(child, MessageWidget) and predicate(child):
                new_msg = make_message(child)
                child._msg = new_msg
                # Update the MessageContent child
                for sub in child.query(MessageContent):
                    sub._msg = new_msg
                    sub._build()
                return
        # Fallback: trigger full rebuild
        self.messages = list(self.messages)
