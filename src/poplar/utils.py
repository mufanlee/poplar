"""Shared utilities — filesystem helpers and shared constants."""

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from poplar.core.session import Message

# --- Shared constants ---
SPINNER_CHARS = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠉"


def is_thinking_message(m: "Message") -> bool:
    """Check if a message is a thinking/spinner indicator.
    
    Used by both AgentLoop (API message filtering) and PoplarApp (UI cleanup).
    Only checks for braille spinner characters — no real message contains these.
    """
    # Late import to avoid circular dependency
    from poplar.core.session import Role
    if m.role != Role.SYSTEM:
        return False
    return bool(m.content and any(c in m.content for c in SPINNER_CHARS))


def get_writable_dir(subdir: str = "") -> Path:
    """Get a writable directory under the poplar config tree.

    Tries in order:
      1. ~/.poplar/<subdir>
      2. ./.poplar/<subdir>  (current working directory)
      3. <temp>/.poplar/<subdir>

    Returns a guaranteed-writable directory, creating it if needed.
    """
    for base in (Path.home() / ".poplar", Path.cwd() / ".poplar"):
        try:
            candidate = base / subdir if subdir else base
            candidate.mkdir(parents=True, exist_ok=True)
            test = candidate / ".write_test"
            test.touch()
            test.unlink()
            return candidate
        except (OSError, PermissionError):
            continue

    # Last resort: system temp directory
    tmp = Path(tempfile.mkdtemp(prefix="poplar-"))
    if subdir:
        tmp = tmp / subdir
        tmp.mkdir(parents=True, exist_ok=True)
    return tmp


def get_db_path() -> str:
    """Get the shared SQLite database path in the poplar data directory.
    
    Used by both CacheManager and SessionStore.
    """
    return str(get_writable_dir() / "poplar.db")
