"""Provider registry for pluggable subtitle providers.

Provides a registration system for subtitle providers, enabling
dynamic provider discovery and configuration-driven initialization.
"""

from typing import Callable, TypeVar

from plexsubs.providers.base import BaseProvider
from plexsubs.utils.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseProvider)

# Registry of provider classes
_provider_registry: dict[str, type[BaseProvider]] = {}


def register_provider(name: str) -> Callable[[type[T]], type[T]]:
    """Register a subtitle provider class.

    This decorator registers a provider class in the global registry,
    making it available for automatic instantiation.

    Args:
        name: Unique name for the provider (e.g., "opensubtitles")

    Returns:
        Decorator function that registers the class

    Example:
        @register_provider("opensubtitles")
        class OpenSubtitlesProvider(BaseProvider):
            ...
    """

    def decorator(cls: type[T]) -> type[T]:
        if name in _provider_registry:
            logger.warning(f"Provider '{name}' is already registered, overwriting")

        _provider_registry[name] = cls
        logger.debug(f"Registered subtitle provider: {name}")
        return cls

    return decorator


def get_provider_class(name: str) -> type[BaseProvider] | None:
    """Get a registered provider class by name.

    Args:
        name: Provider name

    Returns:
        Provider class or None if not found
    """
    return _provider_registry.get(name)


def get_all_provider_classes() -> dict[str, type[BaseProvider]]:
    """Get all registered provider classes.

    Returns:
        Dictionary mapping provider names to classes
    """
    return _provider_registry.copy()


def unregister_provider(name: str) -> bool:
    """Unregister a provider.

    Args:
        name: Provider name to unregister

    Returns:
        True if provider was removed, False if not found
    """
    if name in _provider_registry:
        del _provider_registry[name]
        logger.debug(f"Unregistered subtitle provider: {name}")
        return True
    return False


def clear_registry() -> None:
    """Clear all registered providers."""
    _provider_registry.clear()
    logger.debug("Cleared provider registry")


def create_provider(name: str, **kwargs) -> BaseProvider:
    """Create a provider instance by name.

    Args:
        name: Provider name
        **kwargs: Arguments to pass to provider constructor

    Returns:
        Provider instance

    Raises:
        ValueError: If provider is not registered
    """
    provider_class = get_provider_class(name)
    if provider_class is None:
        raise ValueError(f"Provider '{name}' is not registered")

    return provider_class(**kwargs)


def list_providers() -> list[str]:
    """List all registered provider names.

    Returns:
        List of provider names
    """
    return list(_provider_registry.keys())
