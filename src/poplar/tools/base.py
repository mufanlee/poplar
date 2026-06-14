"""Tool base types and registry."""

import json
import logging
from dataclasses import dataclass
from typing import List, Dict, Any

from poplar.persistence.cache import CacheManager, make_key
from poplar.i18n import get_cache_config

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Result of a tool execution."""
    content: str
    success: bool = True


# Lazy-initialized cache manager
_cache: CacheManager = None


def _get_cache() -> CacheManager:
    global _cache
    if _cache is None:
        _cache = CacheManager()
    return _cache


def _cache_enabled() -> bool:
    return get_cache_config().get("enabled", True)


# Cache TTL config keys, keyed by tool name
_TOOL_CACHE_CONFIG = {
    "read_file": "tool_read_file_ttl",
    "list_directory": "tool_list_dir_ttl",
}


def _tool_cache_key(name: str, arguments: Dict[str, Any]) -> str:
    return make_key("tool", name, json.dumps(arguments, sort_keys=True))


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
    """Execute a named tool with given arguments, with caching support."""
    from poplar.tools.builtin import BUILTIN_TOOLS
    tool = BUILTIN_TOOLS.get(name)
    if not tool:
        return ToolResult(content=f"Unknown tool: {name}", success=False)

    # --- Cache check for cacheable tools ---
    cache = _get_cache() if _cache_enabled() else None
    ttl_key = _TOOL_CACHE_CONFIG.get(name)

    if cache and ttl_key:
        config = get_cache_config()
        ttl = config.get(ttl_key, 300)
        cache_key = _tool_cache_key(name, arguments)

        cached = cache.get(cache_key)
        if cached is not None:
            logger.info("Tool cache hit: %s", cache_key)
            result = ToolResult(content=cached, success=True)
            result._cached = True
            return result

    # --- Execute ---
    try:
        result = tool(arguments)
    except Exception as e:
        return ToolResult(content=f"Tool error: {str(e)}", success=False)

    # --- Post-execution cache ---
    if cache and ttl_key and result.success:
        cache.set(cache_key, result.content, ttl, cache_type=f"tool_{name}")

    # --- Invalidate related caches on write_file ---
    if cache and name == "write_file" and result.success:
        # Invalidate all read_file caches (the written file may have changed)
        cache.invalidate("tool:read_file:")

    return result
