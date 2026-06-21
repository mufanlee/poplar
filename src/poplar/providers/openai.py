"""OpenAI provider — uses the openai SDK."""

from typing import List
from poplar.providers.base import ModelInfo
from poplar.providers.openai_compat import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    """Provider for OpenAI API."""

    _DEFAULT_BASE_URL = "https://api.openai.com/v1"
    _DEFAULT_MODEL = "gpt-4o"

    def get_models(self) -> List[ModelInfo]:
        return [
            ModelInfo(id="gpt-4o", name="GPT-4o"),
            ModelInfo(id="gpt-4o-mini", name="GPT-4o Mini"),
            ModelInfo(id="gpt-4-turbo", name="GPT-4 Turbo"),
        ]
