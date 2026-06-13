from textual.widget import Widget
from textual.reactive import reactive
from poplar.core.session import Message, Role


class ChatView(Widget):
    """Displays conversation history."""

    messages: reactive[list] = reactive([])

    def render(self) -> str:
        if not self.messages:
            return "No messages yet. Start a conversation!"

        lines = []
        for msg in self.messages:
            if msg.role == Role.USER:
                lines.append(f"[bold blue]You:[/bold blue] {msg.content}")
            elif msg.role == Role.ASSISTANT:
                lines.append(f"[bold green]Assistant:[/bold green] {msg.content}")
            elif msg.role == Role.SYSTEM:
                lines.append(f"[dim]System: {msg.content}[/dim]")
            lines.append("")  # Empty line between messages

        return "\n".join(lines)

    def add_message(self, message: Message):
        self.messages = self.messages + [message]
