"""Configuration management for Poplar."""

import yaml
from pathlib import Path

DEFAULT_LANGUAGE = "en"
DEFAULT_MODEL = "deepseek-chat"

# Cache defaults
CACHE_DEFAULTS: dict = {
    "enabled": True,
    "max_memory_items": 100,
    "tool_read_file_ttl": 300,
    "tool_list_dir_ttl": 30,
    "api_response_ttl": 3600,
}

# Context window defaults
CONTEXT_DEFAULTS: dict = {
    "max_tokens": 32768,
    "auto_compress_at": 0.7,
    "keep_recent_exchanges": 3,
}

# Provider defaults
DEFAULT_PROVIDER = "deepseek"

PROVIDER_DEFAULTS: dict = {
    "deepseek": {"model": "deepseek-chat"},
    "openai": {"model": "gpt-4o"},
    "anthropic": {"model": "claude-3-5-sonnet-20241022"},
    "ollama": {"model": "llama3", "base_url": "http://localhost:11434"},
}


def get_config_path():
    """Get the configuration file path at the standard location."""
    home_dir = Path.home() / ".poplar"
    home_dir.mkdir(parents=True, exist_ok=True)
    return home_dir / "config.yaml"


def init_config():
    """Initialize default config file if it doesn't exist."""
    config_path = get_config_path()
    if not config_path.exists():
        default_config = {
            "language": DEFAULT_LANGUAGE,
            "model": DEFAULT_MODEL,
            "provider": DEFAULT_PROVIDER,
            "providers": {k: dict(v) for k, v in PROVIDER_DEFAULTS.items()},
            "cache": dict(CACHE_DEFAULTS),
            "context": dict(CONTEXT_DEFAULTS),
        }
        try:
            save_config(default_config)
        except OSError:
            pass  # Read-only filesystem, can't write defaults


def load_config():
    """Load configuration from file."""
    init_config()
    config_path = get_config_path()
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return {}


def save_config(config):
    """Save configuration to file."""
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)


def get_cache_config() -> dict:
    """Get cache configuration with defaults for missing keys."""
    config = load_config()
    user_cache = config.get("cache", {})
    merged = dict(CACHE_DEFAULTS)
    merged.update(user_cache)
    return merged


def get_context_config() -> dict:
    """Get context window configuration with defaults for missing keys."""
    config = load_config()
    user_ctx = config.get("context", {})
    merged = dict(CONTEXT_DEFAULTS)
    merged.update(user_ctx)
    return merged


def get_active_provider_name() -> str:
    """Get the active provider name from config."""
    config = load_config()
    return str(config.get("provider", DEFAULT_PROVIDER))


def get_provider_config() -> dict:
    """Get the full provider configuration."""
    config = load_config()
    name = config.get("provider", DEFAULT_PROVIDER)
    providers_section = config.get("providers", {})
    user_cfg = providers_section.get(name, {})
    defaults = PROVIDER_DEFAULTS.get(name, {})
    merged = dict(defaults)
    merged.update(user_cfg)
    return {"name": name, "config": merged}
