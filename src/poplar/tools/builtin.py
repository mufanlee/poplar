"""Built-in tool implementations."""

import os
import subprocess
from pathlib import Path
from typing import Dict, Any
from poplar.tools.base import ToolResult

# --- Tool-specific limits ---
MAX_FILE_READ_CHARS = 8000
MAX_COMMAND_OUTPUT_CHARS = 4000
COMMAND_TIMEOUT_SECONDS = 30


def _safe_path(path: str) -> Path:
    """Resolve a path, defaulting to current working directory."""
    p = Path(path)
    if not p.is_absolute():
        p = Path.cwd() / p
    return p.resolve()


def read_file(args: Dict[str, Any]) -> ToolResult:
    """Read a file and return its contents."""
    path = _safe_path(args["path"])
    try:
        content = path.read_text(encoding="utf-8")
        # Truncate if too long
        if len(content) > MAX_FILE_READ_CHARS:
            content = content[:MAX_FILE_READ_CHARS] + "\n... (truncated)"
        return ToolResult(content=content)
    except FileNotFoundError:
        return ToolResult(content=f"File not found: {path}", success=False)
    except PermissionError:
        return ToolResult(content=f"Permission denied: {path}", success=False)
    except Exception as e:
        return ToolResult(content=f"Error reading file: {str(e)}", success=False)


def write_file(args: Dict[str, Any]) -> ToolResult:
    """Write content to a file."""
    path = _safe_path(args["path"])
    content = args["content"]
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return ToolResult(content=f"File written: {path} ({len(content)} bytes)")
    except PermissionError:
        return ToolResult(content=f"Permission denied: {path}", success=False)
    except Exception as e:
        return ToolResult(content=f"Error writing file: {str(e)}", success=False)


def list_directory(args: Dict[str, Any]) -> ToolResult:
    """List directory contents."""
    path = _safe_path(args.get("path", "."))
    try:
        items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        lines = []
        for item in items:
            suffix = "/" if item.is_dir() else ""
            size = ""
            if item.is_file():
                try:
                    s = item.stat().st_size
                    size = f" ({s:,} bytes)"
                except OSError:
                    pass
            lines.append(f"  {item.name}{suffix}{size}")
        header = f"Contents of {path}:\n"
        return ToolResult(content=header + "\n".join(lines) if lines else header + "  (empty)")
    except FileNotFoundError:
        return ToolResult(content=f"Directory not found: {path}", success=False)
    except Exception as e:
        return ToolResult(content=f"Error listing directory: {str(e)}", success=False)


def run_command(args: Dict[str, Any]) -> ToolResult:
    """Execute a shell command.

    WARNING: Uses shell=True — the LLM can request arbitrary commands.
    This is intentional for a local developer TUI tool, but users should
    be aware that malicious prompt injection could lead to command execution.
    """
    cmd = args["command"]
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
            cwd=os.getcwd()
        )
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}"
        if not output.strip():
            output = f"(exit code: {result.returncode})"
        if len(output) > MAX_COMMAND_OUTPUT_CHARS:
            output = output[:MAX_COMMAND_OUTPUT_CHARS] + "\n... (truncated)"
        success = result.returncode == 0
        return ToolResult(content=output, success=success)
    except subprocess.TimeoutExpired:
        return ToolResult(content="Command timed out after 30s", success=False)
    except Exception as e:
        return ToolResult(content=f"Error running command: {str(e)}", success=False)


BUILTIN_TOOLS = {
    "read_file": read_file,
    "write_file": write_file,
    "list_directory": list_directory,
    "run_command": run_command,
}
