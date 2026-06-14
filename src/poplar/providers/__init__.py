"""Provider registry and factory."""

import importlib
import os
from poplar.providers.base import Provider

# Registry: maps provider name → (module_path, class_name, env_var_for_api_key)
PROVIDER_REGISTRY = {
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
    return list(PROVIDER_REGISTRY.keys())


def create_provider(name: str, user_config: dict = None) -> Provider:
    """Create a provider instance by name.

    Args:
        name: Provider name (e.g. 'deepseek', 'openai')
        user_config: Per-provider config dict from ~/.poplar/config.yaml.
                     May contain 'model', 'base_url', and optionally 'api_key'.

    Returns:
        A Provider instance matching the Provider Protocol.
    """
    info = PROVIDER_REGISTRY.get(name)
    if not info:
        raise ValueError(f"Unknown provider: {name}. Available: {list(PROVIDER_REGISTRY.keys())}")

    config = user_config or {}

    # API key: user_config > env var
    api_key = config.get("api_key") or (os.getenv(info["env_key"]) if info["env_key"] else None)
    model = config.get("model", info["default_model"])
    base_url = config.get("base_url")

    module = importlib.import_module(info["module"])
    cls = getattr(module, info["class"])

    kwargs = {"api_key": api_key, "model": model}
    if base_url:
        kwargs["base_url"] = base_url

    return cls(**kwargs)
