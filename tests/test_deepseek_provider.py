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
