"""Plex Subtitle Webhook package."""

__version__ = "0.1.0"
__author__ = "Plex Subtitle Webhook"
__description__ = (
    "A webhook service that automatically downloads and attaches subtitles "
    "for your Plex media library using the OpenSubtitles API"
)

from plexsubs.main import create_app, main

__all__ = ["create_app", "main"]
