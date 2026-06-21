"""Workspace trust management.

Tracks which directories the user has explicitly trusted for tool execution.
Trust records persist to ~/.poplar/trusted.json.
"""

import json
import logging
from pathlib import Path
from typing import List, Set

from poplar.utils import get_writable_dir

logger = logging.getLogger(__name__)

_TRUST_FILE_NAME = "trusted.json"


def _trust_file_path() -> Path:
    """Get the path to the trust records file."""
    return get_writable_dir() / _TRUST_FILE_NAME


def _load_trusted() -> Set[str]:
    """Load the set of trusted directory paths."""
    path = _trust_file_path()
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {p for p in data.get("trusted", []) if isinstance(p, str)}
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load trust records: %s", e)
        return set()


def _save_trusted(trusted: Set[str]) -> None:
    """Save the set of trusted directory paths."""
    path = _trust_file_path()
    try:
        path.write_text(
            json.dumps({"trusted": sorted(trusted)}, indent=2),
            encoding="utf-8",
        )
    except OSError as e:
        logger.warning("Failed to save trust records: %s", e)


def is_workspace_trusted(directory: Path) -> bool:
    """Check if a directory is in the trusted list.

    Also trusts subdirectories of any trusted parent directory.
    """
    resolved = directory.resolve()
    trusted = _load_trusted()

    for trusted_path in trusted:
        try:
            tp = Path(trusted_path).resolve()
            # Trust if the directory is the same as or inside a trusted directory
            if resolved == tp or str(resolved).startswith(str(tp) + "/"):
                return True
        except OSError:
            continue
    return False


def trust_workspace(directory: Path) -> None:
    """Mark a directory as trusted and persist."""
    resolved = str(directory.resolve())
    trusted = _load_trusted()
    if resolved not in trusted:
        trusted.add(resolved)
        _save_trusted(trusted)
        logger.info("Workspace trusted: %s", resolved)


def untrust_workspace(directory: Path) -> None:
    """Remove trust for a directory and persist."""
    resolved = str(directory.resolve())
    trusted = _load_trusted()
    if resolved in trusted:
        trusted.discard(resolved)
        _save_trusted(trusted)
        logger.info("Workspace untrusted: %s", resolved)


def get_trusted_workspaces() -> List[str]:
    """Return all trusted directory paths."""
    return sorted(_load_trusted())
