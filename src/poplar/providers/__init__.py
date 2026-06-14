"""Provider registry and factory."""

import importlib
import os
from typing import Optional
from poplar.providers.base import Provider

# Registry: maps provider name → config dict
_PROVIDER_REGISTRY: dict[str, dict[str, Optional[str]]] = {
    "deepseek": {
        "module": "poplar.providers.deepseek",
        "class": "DeepSeekProvider",
        "env_key": "DEEPSEEK_API_KEY",
        "default_model": "deepseek-chat",
    },
    "openai": {
        "module": "poplar.providers.openai",
        "class": "OpenAIProvider",
        "env_key": "OPENAI_API_KEY",
        "default_model": "gpt-4o",
    },
    "anthropic": {
        "module": "poplar.providers.anthropic",
        "class": "AnthropicProvider",
        "env_key": "ANTHROPIC_API_KEY",
        "default_model": "claude-3-5-sonnet-20241022",
    },
    "ollama": {
        "module": "poplar.providers.ollama",
        "class": "OllamaProvider",
        "env_key": None,
        "default_model": "llama3",
    },
}


def get_available_providers() -> list[str]:
    """Return list of registered provider names."""
    return list(_PROVIDER_REGISTRY.keys())


def create_provider(name: str, user_config: Optional[dict] = None) -> Provider:
    """Create a provider instance by name.

    Args:
        name: Provider name (e.g. 'deepseek', 'openai')
        user_config: Per-provider config dict from ~/.poplar/config.yaml.
                     May contain 'model', 'base_url', and optionally 'api_key'.

    Returns:
        A Provider instance matching the Provider Protocol.
    """
    info = _PROVIDER_REGISTRY.get(name)
    if not info:
        raise ValueError(f"Unknown provider: {name}. Available: {list(_PROVIDER_REGISTRY.keys())}")

    config: dict = user_config or {}

    # API key: user_config > env var
    env_key: Optional[str] = info.get("env_key")  # type: ignore[assignment]
    api_key: Optional[str] = config.get("api_key") or (os.getenv(env_key) if env_key else None)
    model: str = str(config.get("model") or info.get("default_model", ""))
    base_url: Optional[str] = config.get("base_url")

    module = importlib.import_module(str(info["module"]))
    cls = getattr(module, str(info["class"]))

    kwargs: dict = {"api_key": api_key, "model": model}
    if base_url:
        kwargs["base_url"] = base_url

    return cls(**kwargs)  # type: ignore[no-any-return,return-value]
