"""Tool base types and registry."""

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class ToolResult:
    """Result of a tool execution."""
    content: str
    success: bool = True


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file. Returns the file content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute or relative path to the file"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file. Creates the file if it doesn't exist.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to write"},
                    "content": {"type": "string", "description": "Content to write to the file"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List contents of a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the directory to list. Defaults to current directory."}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute a shell command and return the output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command to execute"}
                },
                "required": ["command"]
            }
        }
    },
]


def execute_tool(name: str, arguments: Dict[str, Any]) -> ToolResult:
    """Execute a named tool with given arguments."""
    from poplar.tools.builtin import BUILTIN_TOOLS
    tool = BUILTIN_TOOLS.get(name)
    if not tool:
        return ToolResult(content=f"Unknown tool: {name}", success=False)
    try:
        return tool(arguments)
    except Exception as e:
        return ToolResult(content=f"Tool error: {str(e)}", success=False)
