"""Internationalization support for Poplar."""

import os
from poplar.config import DEFAULT_LANGUAGE, load_config, save_config

TRANSLATIONS = {
    "en": {
        "welcome_title": "Poplar",
        "welcome_subtitle": "AI Agent TUI",
        "welcome_version": "v0.1.0",
        "welcome_description": "Your intelligent terminal assistant",
        "welcome_features": "Features",
        "welcome_feature1": "• Chat with AI models",
        "welcome_feature2": "• Markdown rendering",
        "welcome_feature3": "• Cancel requests with ESC",
        "welcome_start": "Press Enter to start chatting",
        "status_model": "Model",
        "status_tokens": "Tokens",
        "status_messages": "Messages",
        "status_online": "● Online",
        "status_ready": "○ Ready",
        "thinking": "Thinking",
        "esc_to_cancel": "esc to cancel",
        "request_cancelled": "Request cancelled",
        "error": "Error",
        "seconds": "s",
        "notify_calling_api": "Calling API...",
        "notify_cancelled": "Request cancelled",
        "key_quit": "Quit",
        "key_cancel": "Cancel",
        "composer_placeholder": "Type your message...",
        "input_placeholder": "Type your message...",
        "title_you": "You",
        "title_assistant": "Assistant",
        "picker_hint": "↑↓:nav Enter:switch N:new D:del R:rename Esc:close",
        "new_chat": "New Chat",
        "copied": "Copied to clipboard",
        "no_response": "No response to copy",
        "session_cleared": "Last session cleared",
        "session_deleted": "Session deleted",
        "tool_result_prefix": "🔧 {name}",
        "compress_start": "Compressing conversation...",
        "compress_done": "Compression complete",
    },
    "zh": {
        "welcome_title": "Poplar",
        "welcome_subtitle": "AI Agent TUI",
        "welcome_version": "v0.1.0",
        "welcome_description": "你的智能终端助手",
        "welcome_features": "功能特性",
        "welcome_feature1": "• 与 AI 模型对话",
        "welcome_feature2": "• Markdown 渲染",
        "welcome_feature3": "• ESC 取消请求",
        "welcome_start": "按 Enter 开始对话",
        "status_model": "模型",
        "status_tokens": "Token",
        "status_messages": "消息",
        "status_online": "● 在线",
        "status_ready": "○ 就绪",
        "thinking": "思考中",
        "esc_to_cancel": "esc 取消",
        "request_cancelled": "请求已取消",
        "error": "错误",
        "seconds": "秒",
        "notify_calling_api": "正在调用 API...",
        "notify_cancelled": "请求已取消",
        "key_quit": "退出",
        "key_cancel": "取消",
        "composer_placeholder": "输入你的消息...",
        "input_placeholder": "输入你的消息...（Enter 发送，Shift+Enter 换行）",
        "title_you": "你",
        "title_assistant": "助手",
        "picker_hint": "↑↓:导航 Enter:切换 N:新建 D:删除 R:重命名 Esc:关闭",
        "new_chat": "新会话",
        "copied": "已复制到剪贴板",
        "no_response": "没有可复制的内容",
        "session_cleared": "会话已清空",
        "session_deleted": "会话已删除",
        "tool_result_prefix": "🔧 {name}",
        "compress_start": "正在压缩对话...",
        "compress_done": "压缩完成",
    }
}

_current_language: str = DEFAULT_LANGUAGE
_language_inited: bool = False


def get_language() -> str:
    """Get the current language, checking env var first, then config."""
    global _current_language, _language_inited
    env_lang = os.getenv("POPLAR_LANGUAGE")
    if env_lang in TRANSLATIONS:
        return env_lang
    if not _language_inited:
        config = load_config()
        if "language" in config and config["language"] in TRANSLATIONS:
            _current_language = config["language"]
        _language_inited = True
    return _current_language


def set_language(language: str) -> bool:
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
    if kwargs:
        return translation.format(**kwargs)
    return translation
