"""Chat message display widgets."""

from textual.widgets import Static
from textual.containers import ScrollableContainer
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


class MessageWidget(Static):
    """A single chat message."""

    def __init__(self, message: Message):
        super().__init__()
        self._msg = message
        self._build()

    def _build(self):
        """Render the message."""
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

    DEFAULT_CSS = """
    MessageWidget {
        height: auto;
        margin: 0 0 0 0;
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
        """Rebuild all message widgets (mounted directly to this ScrollableContainer)."""
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
            self.mount(MessageWidget(msg))

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
        self.mount(widget)
        self.scroll_end(animate=False)
        return widget

    def update_message_widget(self, predicate, make_message):
        """Find the first MessageWidget matching predicate and update its content.

        Args:
            predicate: callable(MessageWidget) -> bool
            make_message: callable(MessageWidget) -> Message, returns updated message
        """
        for child in self.children:
            if isinstance(child, MessageWidget) and predicate(child):
                new_msg = make_message(child)
                child._msg = new_msg
                child._build()
                return
        # Fallback: trigger full rebuild
        self.messages = list(self.messages)
