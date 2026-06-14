"""Internationalization support for Poplar."""
import os
import yaml
from pathlib import Path

# Default language
DEFAULT_LANGUAGE = "en"
DEFAULT_MODEL = "deepseek-chat"

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
        
        # Titles
        "title_you": "You",
        "title_assistant": "Assistant",
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
        
        # Titles
        "title_you": "你",
        "title_assistant": "助手",
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
