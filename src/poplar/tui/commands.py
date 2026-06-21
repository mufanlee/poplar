"""Shared command registry — single source of truth for all slash commands.

Used by app.py (dispatch), cmd_prompt.py (suggestions),
and help_screen.py (help list).
"""

from dataclasses import dataclass
from typing import Optional, List


@dataclass(frozen=True)
class Command:
    """A slash command definition."""
    pattern: str        # e.g. "/help", "/provider"
    description: str    # e.g. "Show available commands"
    handler: str        # method name on PoplarApp, e.g. "_show_help"
    match: str = "exact"  # "exact" or "prefix"


COMMANDS: List[Command] = [
    # --- UI commands (not echoed as user message) ---
    Command("/help",     "Show available commands",      handler="_show_help",              match="exact"),
    Command("/quit",     "Exit application",             handler="exit",                    match="exact"),
    Command("/session",  "Manage sessions",              handler="action_session_picker",   match="exact"),
    Command("/clear",    "Clear current session",        handler="_clear_session",          match="exact"),
    # --- Data commands (echoed in chat) ---
    Command("/context",  "Session context info",         handler="_show_context_info",      match="exact"),
    Command("/compress", "Compress conversation",        handler="_compress_conversation",  match="exact"),
    Command("/stats",    "Performance statistics",       handler="_show_stats",             match="exact"),
    Command("/provider", "Show / switch provider",       handler="_handle_provider_command",match="prefix"),
    Command("/model",    "Show / switch model",           handler="_handle_model_command",   match="prefix"),
    Command("/export ",  "Export session to JSON",       handler="_export_session",         match="prefix"),
    Command("/import ",  "Import session from JSON",     handler="_import_session",         match="prefix"),
]

# Commands that should NOT be echoed as a user message in the chat
UI_ONLY_COMMANDS = frozenset({"/help", "/quit", "/session", "/clear", "/compress"})


def find_command(text: str) -> Optional[Command]:
    """Find the first command matching the given text."""
    for cmd in COMMANDS:
        if cmd.match == "exact" and text == cmd.pattern:
            return cmd
        if cmd.match == "prefix" and text.startswith(cmd.pattern):
            return cmd
    return None


def dispatch_command(app, text: str) -> bool:
    """Dispatch a slash command to the app. Returns True if handled.

    If the command is unknown, calls _show_unknown_command.
    """
    cmd = find_command(text)
    if cmd:
        handler = getattr(app, cmd.handler)
        if cmd.match == "prefix":
            handler(text)
        else:
            handler()
        return True

    if text.startswith("/"):
        app._show_unknown_command(text)
        return True

    return False
