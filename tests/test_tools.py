"""Tests for tool execution."""

from poplar.tools.base import execute_tool, ToolResult


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
