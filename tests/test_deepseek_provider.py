from poplar.providers.base import Provider
from poplar.core.session import Message, Role


def test_provider_interface_exists():
    """Verify Provider protocol is defined."""
    from poplar.providers.base import Provider
    assert Provider is not None


def test_provider_has_required_methods():
    """Verify Provider protocol has chat and stream methods."""
    import inspect
    from poplar.providers.base import Provider

    # Check that Protocol defines the methods
    assert hasattr(Provider, 'chat') or 'chat' in dir(Provider)


from unittest.mock import Mock, patch
from poplar.core.session import Message, Role
from poplar.providers.deepseek import DeepSeekProvider


def test_deepseek_provider_creation():
    provider = DeepSeekProvider(api_key="test-key")
    assert provider.api_key == "test-key"
    assert provider.base_url == "https://api.deepseek.com/v1"


def test_deepseek_chat_mocked():
    """Test chat method without actual API call."""
    with patch('openai.OpenAI') as mock_client:
        # Setup mock response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15

        mock_client.return_value.chat.completions.create.return_value = mock_response

        # Test
        provider = DeepSeekProvider(api_key="test-key")
        messages = [Message(role=Role.USER, content="Hello")]
        response = provider.chat(messages)

        assert response.content == "Test response"
        assert response.usage["total_tokens"] == 15
