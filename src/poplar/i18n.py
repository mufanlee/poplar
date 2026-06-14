"""Internationalization support for Poplar."""
import os
import yaml
from pathlib import Path

# Default language
DEFAULT_LANGUAGE = "en"
DEFAULT_MODEL = "deepseek-chat"

# Cache defaults (applied when not present in config)
CACHE_DEFAULTS = {
    "enabled": True,
    "max_memory_items": 100,
    "tool_read_file_ttl": 300,     # 5 min
    "tool_list_dir_ttl": 30,       # 30 sec
    "api_response_ttl": 3600,      # 1 hour
}

# Context window defaults
CONTEXT_DEFAULTS = {
    "max_tokens": 32768,
    "auto_compress_at": 0.7,
    "keep_recent_exchanges": 3,
}

# Provider defaults
DEFAULT_PROVIDER = "deepseek"

PROVIDER_DEFAULTS = {
    "deepseek": {"model": "deepseek-chat"},
    "openai": {"model": "gpt-4o"},
    "anthropic": {"model": "claude-3-5-sonnet-20241022"},
    "ollama": {"model": "llama3", "base_url": "http://localhost:11434"},
}

# Translation dictionaries
TRANSLATIONS = {
    "en": {
        # Welcome screen
        "welcome_title": "Poplar",
        "welcome_subtitle": "AI Agent TUI",
        "welcome_version": "v0.1.0",
        "welcome_description": "Your intelligent terminal assistant",
        "welcome_features": "Features",
        "welcome_feature1": "• Chat with AI models",
        "welcome_feature2": "• Markdown rendering",
        "welcome_feature3": "• Cancel requests with ESC",
        "welcome_start": "Press Enter to start chatting",
        
        # Status bar
        "status_model": "Model",
        "status_tokens": "Tokens",
        "status_messages": "Messages",
        "status_online": "● Online",
        "status_ready": "○ Ready",
        
        # Messages
        "thinking": "Thinking",
        "esc_to_cancel": "esc to cancel",
        "request_cancelled": "Request cancelled",
        "error": "Error",
        "seconds": "s",
        
        # Notifications
        "notify_calling_api": "Calling API...",
        "notify_cancelled": "Request cancelled",
        
        # Keybindings
        "key_quit": "Quit",
        "key_cancel": "Cancel",
        
        # Composer
        "composer_placeholder": "Type your message...",
        "input_placeholder": "Type your message... (Enter to send, Shift+Enter for new line)",
        
        # Titles
        "title_you": "You",
        "title_assistant": "Assistant",

        # Session picker
        "picker_hint": "↑↓:nav Enter:switch N:new D:del R:rename Esc:close",
        "new_chat": "New Chat",

        # Actions
        "copied": "Copied to clipboard",
        "no_response": "No response to copy",
        "session_cleared": "Last session cleared",
        "session_deleted": "Session deleted",

        # Tool results
        "tool_result_prefix": "🔧 {name}",

        # Context
        "compress_start": "Compressing conversation...",
        "compress_done": "Compression complete",
    },
    "zh": {
        # Welcome screen
        "welcome_title": "Poplar",
        "welcome_subtitle": "AI Agent TUI",
        "welcome_version": "v0.1.0",
        "welcome_description": "你的智能终端助手",
        "welcome_features": "功能特性",
        "welcome_feature1": "• 与 AI 模型对话",
        "welcome_feature2": "• Markdown 渲染",
        "welcome_feature3": "• ESC 取消请求",
        "welcome_start": "按 Enter 开始对话",
        
        # Status bar
        "status_model": "模型",
        "status_tokens": "Token",
        "status_messages": "消息",
        "status_online": "● 在线",
        "status_ready": "○ 就绪",
        
        # Messages
        "thinking": "思考中",
        "esc_to_cancel": "esc 取消",
        "request_cancelled": "请求已取消",
        "error": "错误",
        "seconds": "秒",
        
        # Notifications
        "notify_calling_api": "正在调用 API...",
        "notify_cancelled": "请求已取消",
        
        # Keybindings
        "key_quit": "退出",
        "key_cancel": "取消",
        
        # Composer
        "composer_placeholder": "输入你的消息...",
        "input_placeholder": "输入你的消息...（Enter 发送，Shift+Enter 换行）",
        
        # Titles
        "title_you": "你",
        "title_assistant": "助手",

        # Session picker
        "picker_hint": "↑↓:导航 Enter:切换 N:新建 D:删除 R:重命名 Esc:关闭",
        "new_chat": "新会话",

        # Actions
        "copied": "已复制到剪贴板",
        "no_response": "没有可复制的内容",
        "session_cleared": "会话已清空",
        "session_deleted": "会话已删除",

        # Tool results
        "tool_result_prefix": "🔧 {name}",

        # Context
        "compress_start": "正在压缩对话...",
        "compress_done": "压缩完成",
    }
}

# Current language
_current_language = DEFAULT_LANGUAGE


def get_config_path():
    """Get the configuration file path."""
    config_dir = Path.home() / ".poplar"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "config.yaml"


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
        save_config(default_config)


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
    return config.get("provider", DEFAULT_PROVIDER)


def get_provider_config() -> dict:
    """Get the full provider configuration.

    Returns:
        {"name": "deepseek", "config": {"model": "deepseek-chat", ...}}
    """
    config = load_config()
    name = config.get("provider", DEFAULT_PROVIDER)
    providers_section = config.get("providers", {})
    user_cfg = providers_section.get(name, {})
    defaults = PROVIDER_DEFAULTS.get(name, {})
    merged = dict(defaults)
    merged.update(user_cfg)
    return {"name": name, "config": merged}


def get_language():
    """Get the current language."""
    global _current_language
    
    # Check environment variable first
    env_lang = os.getenv("POPLAR_LANGUAGE")
    if env_lang in TRANSLATIONS:
        _current_language = env_lang
        return _current_language
    
    # Check config file
    config = load_config()
    if "language" in config and config["language"] in TRANSLATIONS:
        _current_language = config["language"]
        return _current_language
    
    return DEFAULT_LANGUAGE


def set_language(language):
    """Set the current language and save to config."""
    global _current_language
    if language in TRANSLATIONS:
        _current_language = language
        config = load_config()
        config["language"] = language
        save_config(config)
        return True
    return False


def t(key, **kwargs):
    """Get translation for a key."""
    lang = get_language()
    translation = TRANSLATIONS.get(lang, {}).get(key, TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key))

    # Format with kwargs if provided
    if kwargs:
        return translation.format(**kwargs)
    return translation


def get_model():
    """Get the configured model name."""
    config = load_config()
    return config.get("model", DEFAULT_MODEL)
