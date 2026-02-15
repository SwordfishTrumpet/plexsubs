# AGENTS.md

## Project Overview

This is `plexsubs` - a Plex webhook service for automatically downloading subtitles.

## Git Configuration

This repository uses a specific Git identity. Configure locally:

```bash
git config user.name "SwordfishTrumpet"
git config user.email "swordfishtrumpet@users.noreply.github.com"
```

Or set globally (for all repositories on this machine):

```bash
git config --global user.name "SwordfishTrumpet"
git config --global user.email "swordfishtrumpet@users.noreply.github.com"
```

## Development Commands

```bash
# Run the application
uv run python -m plexsubs.main

# Run linting
uv run ruff check .

# Run formatting
uv run ruff format .

# Sync dependencies after changes to pyproject.toml
uv sync
```

## Project Structure

- `plexsubs/` - Main application package
  - `main.py` - FastAPI application entry point
  - `config/` - Configuration and settings
  - `providers/` - Subtitle provider implementations
  - `plex/` - Plex API client and webhook handler
  - `core/` - Core business logic
  - `utils/` - Utilities and logging

## Technology Stack

- Python 3.9+
- FastAPI for web server
- Pydantic for configuration
- uv for dependency management
- ruff for linting/formatting

## Configuration

Configuration is done via environment variables or `.env` file. See `.env.example` for available options.

## Important Notes

### Webhook Endpoint

The webhook endpoint is `/plexsubs`. Configure Plex webhook as:
```
http://<your-server-ip>:9000/plexsubs
```

### Subtitle Behavior

- Languages are configured via SUBTITLES_LANGUAGES as comma-separated ISO 639-1 codes (default: en)
- First language is preferred, subsequent languages are tried in order if not found
- Subtitles are downloaded automatically when media starts playing
- The service attempts to switch subtitles mid-playback (takes ~15-20 seconds)
- If mid-playback switching fails, first language subtitle will be default on next play
- The service will NOT download secondary language subtitles if first language already exists

### Docker Deployment

The container runs with user permissions matching the media directory owner (uid 1000:100). This is configured in `docker-compose.yml`:
```yaml
user: "1000:100"
```

### Known Limitations

- Active session subtitle switching during playback can be unreliable

## Contributing Policy

**This project accepts Issues only - Pull Requests are not accepted.**

See [GITHUB_SETUP.md](GITHUB_SETUP.md) for:
- Issue templates configuration
- How to disable pull requests in repository settings
- Community engagement guidelines

### Related Documentation

- `.github/ISSUE_TEMPLATE/` - Issue templates for bugs and feature requests
- `.github/pull_request_template.md` - PR policy notice
- `README.md` - User-facing documentation with support disclaimer
