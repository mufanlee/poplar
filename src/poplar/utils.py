"""Shared utilities — filesystem helpers used across modules."""

import tempfile
from pathlib import Path


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
