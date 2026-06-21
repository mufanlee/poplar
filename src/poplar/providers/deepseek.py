"""DeepSeek provider — uses the openai SDK with DeepSeek API endpoint."""

from typing import List
from poplar.providers.base import ModelInfo
from poplar.providers.openai_compat import OpenAICompatibleProvider


class DeepSeekProvider(OpenAICompatibleProvider):
    """Provider for DeepSeek API (OpenAI-compatible)."""

    _DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
    _DEFAULT_MODEL = "deepseek-chat"

    def get_models(self) -> List[ModelInfo]:
        return [
            ModelInfo(id="deepseek-v4-flash", name="DeepSeek V4 Flash"),
            ModelInfo(id="deepseek-v4-pro", name="DeepSeek V4 Pro"),
            ModelInfo(id="deepseek-chat", name="DeepSeek Chat (deprecating)"),
            ModelInfo(id="deepseek-reasoner", name="DeepSeek Reasoner (deprecating)"),
        ]
