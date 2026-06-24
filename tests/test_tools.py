"""Tests for tool execution."""

import pytest
from unittest.mock import patch
from poplar.tools.base import execute_tool, ToolResult


@pytest.fixture(autouse=True)
def _trust_workspace():
    """Mock trust check so tests can run without actual trust setup."""
    with patch("poplar.core.trust.is_workspace_trusted", return_value=True):
        yield


def test_read_file(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("hello world")
    result = execute_tool("read_file", {"path": str(f)})
    assert result.success
    assert "hello world" in result.content


def test_read_file_not_found():
    result = execute_tool("read_file", {"path": "/nonexistent/file.txt"})
    assert not result.success
    assert "not found" in result.content.lower()


def test_write_file(tmp_path):
    f = tmp_path / "output.txt"
    result = execute_tool("write_file", {"path": str(f), "content": "test content"})
    assert result.success
    assert f.read_text() == "test content"


def test_list_directory(tmp_path):
    (tmp_path / "file1.txt").write_text("a")
    (tmp_path / "dir1").mkdir()
    result = execute_tool("list_directory", {"path": str(tmp_path)})
    assert result.success
    assert "file1.txt" in result.content
    assert "dir1" in result.content


def test_run_command():
    result = execute_tool("run_command", {"command": "echo hello"})
    assert result.success
    assert "hello" in result.content


def test_unknown_tool():
    result = execute_tool("nonexistent_tool", {})
    assert not result.success


def test_tool_error():
    result = execute_tool("run_command", {"command": "exit 1"})
    assert not result.success


def test_read_file_truncation(tmp_path):
    """Long file content gets truncated."""
    f = tmp_path / "big.txt"
    f.write_text("x" * 10000)  # > MAX_FILE_READ_CHARS (8000)
    result = execute_tool("read_file", {"path": str(f)})
    assert result.success
    assert "... (truncated)" in result.content


def test_read_file_permission_denied(tmp_path):
    """PermissionError returns failure."""
    import stat
    f = tmp_path / "secret.txt"
    f.write_text("secret")
    f.chmod(0o000)
    try:
        result = execute_tool("read_file", {"path": str(f)})
        assert not result.success
    finally:
        f.chmod(0o644)


def test_write_file_permission_denied(tmp_path):
    """PermissionError when writing."""
    from unittest.mock import patch as upatch
    from poplar.tools import builtin
    with upatch.object(builtin.Path, 'write_text', side_effect=PermissionError("denied")):
        result = execute_tool("write_file", {"path": str(tmp_path / "x.txt"), "content": "x"})
        assert not result.success


def test_list_dir_not_found():
    """Directory not found error."""
    result = execute_tool("list_directory", {"path": "/nonexistent_dir_xyz"})
    assert not result.success
    assert "not found" in result.content.lower()


def test_list_dir_empty(tmp_path):
    """Empty directory returns '(empty)'."""
    empty = tmp_path / "empty_dir"
    empty.mkdir()
    result = execute_tool("list_directory", {"path": str(empty)})
    assert result.success
    assert "(empty)" in result.content


def test_run_command_with_stderr():
    """Command with stderr output."""
    result = execute_tool("run_command", {"command": "echo err >&2"})
    assert "[stderr]" in result.content or "err" in result.content


def test_run_command_empty_output():
    """Command with no stdout/stderr."""
    result = execute_tool("run_command", {"command": "true"})
    assert "exit code: 0" in result.content


def test_run_command_truncation(tmp_path):
    """Long command output gets truncated."""
    result = execute_tool("run_command", {"command": f"python3 -c \"print('x'*10000)\""})
    assert result.success
    assert "... (truncated)" in result.content


def test_run_command_timeout():
    """Command timeout."""
    result = execute_tool("run_command", {"command": "sleep 60"})
    assert not result.success
    assert "timed out" in result.content.lower()

def test_run_command_invalid():
    """Invalid command."""
    result = execute_tool("run_command", {"command": "nonexistentcmd 2>/dev/null"})
    # May succeed or fail depending on shell, just ensure no crash
    assert isinstance(result.content, str)
