"""Provider exports."""

from plexsubs.providers.base import BaseProvider, SubtitleResult
from plexsubs.providers.opensubtitles import OpenSubtitlesProvider
from plexsubs.providers.registry import (
    create_provider,
    get_all_provider_classes,
    get_provider_class,
    list_providers,
    register_provider,
    unregister_provider,
)

__all__ = [
    "BaseProvider",
    "OpenSubtitlesProvider",
    "SubtitleResult",
    # Registry
    "register_provider",
    "get_provider_class",
    "get_all_provider_classes",
    "create_provider",
    "list_providers",
    "unregister_provider",
]
