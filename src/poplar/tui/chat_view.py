from textual.widgets import Static
from textual.containers import ScrollableContainer
from textual.reactive import reactive
from rich.align import Align
from rich.text import Text
from rich.panel import Panel
from rich.markdown import Markdown
from rich.console import Group
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


class ChatMessages(Static):
    """Static widget to display chat messages."""

    DEFAULT_CSS = """
    ChatMessages {
        height: auto;
    }
    ChatMessages.welcome {
        height: 100%;
        content-align: center middle;
    }
    """

    def update_messages(self, messages: list[Message]):
        if not messages:
            self.add_class("welcome")
            self.update(build_welcome())
            return

        self.remove_class("welcome")
        
        # Build a list of renderables
        renderables = []
        
        for msg in messages:
            if msg.role == Role.USER:
                # User message with blue background - full width
                user_content = Text(msg.content)
                renderables.append(Panel(
                    user_content,
                    title=f"👤 {t('title_you')}",
                    border_style="blue",
                    padding=(0, 1),
                ))
            elif msg.role == Role.ASSISTANT:
                # Assistant message with gray background and Markdown
                renderables.append(Panel(
                    Markdown(msg.content),
                    title=f"🤖 {t('title_assistant')}",
                    border_style="green",
                    padding=(0, 1),
                    expand=False,
                ))
            elif msg.role == Role.SYSTEM:
                # System message - no circle prefix
                renderables.append(Text(f"  {msg.content}", style="dim yellow"))
            
            # Add spacing between messages
            renderables.append(Text(""))
        
        # Update with grouped renderables
        self.update(Group(*renderables))


class ChatView(ScrollableContainer):
    """Scrollable container for chat messages."""

    messages: reactive[list] = reactive([])

    def compose(self):
        self.chat_display = ChatMessages()
        yield self.chat_display

    def on_mount(self):
        """Show welcome screen on startup."""
        self.chat_display.add_class("welcome")
        self.chat_display.update(build_welcome())

    def watch_messages(self, messages: list[Message]):
        """Called when messages reactive changes."""
        self.chat_display.update_messages(messages)
        self.scroll_end(animate=False)

    def add_message(self, message: Message):
        self.messages = self.messages + [message]
