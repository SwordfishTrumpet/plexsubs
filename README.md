# plexsubs - Plex Subtitle Webhook

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![Docker](https://img.shields.io/badge/docker-supported-blue.svg)

A webhook service that automatically downloads and attaches subtitles for your Plex media library. When you start playing a movie or show, it searches the OpenSubtitles API for subtitles in your preferred languages, downloads them to your media directories, and can even switch them on mid-playback so you don't have to pause and hunt for files.

## Who Is This For?

This tool solves the subtitle problem for Plex users who are tired of:

- **The "Search Loop"**: Plex search timing out or returning "No results found" for your preferred language
- **The "Manual Chore"**: Downloading .srt files on your PC just to move them to your NAS
- **The "Silent Failure"**: Starting a movie only to realize 5 minutes in that you forgot to find subtitles

If you've ever wished subtitles would just appear automatically when you start watching, plexsubs is for you.

## How It Works

When you start playing media in Plex, the webhook triggers plexsubs to search for and download subtitles automatically. Once downloaded, the subtitle is automatically selected and enabled in your Plex player.

## Features

- **OpenSubtitles Provider**: Primary subtitle source
- **Smart Matching**: Release group matching for best subtitle quality (SPARKS, AMIABLE, CACHET, etc.)
- **Auto-Select**: Automatically enables downloaded subtitles in Plex
- **Language Detection**: Verifies downloaded subtitle language
- **Upgrade Support**: Replaces existing subtitles on perfect release match
- **Color-Coded Logging**: Easy-to-read logs with package prefixes
- **Docker Support**: Easy deployment with Docker Compose

## Limitations

- **No subtitle synchronization**: This tool downloads subtitles but does not adjust timing if they are out of sync with the audio. You may need to manually adjust subtitle delay in your player if needed.

## Quick Start

### Prerequisites

Before you begin, you'll need:
- **Plex Media Server** with a valid token
- **Plex Pass subscription** (required for webhook support)
- **OpenSubtitles.com account** (free registration)
- **Docker** (recommended) or **Python 3.9+**

### Getting Your Credentials

#### Plex URL and Token

**Plex URL:**
- If Plex is on the same machine: `http://localhost:32400`
- If Plex is on another machine: `http://<ip-address>:32400`
- You can also use your Plex Direct URL from Settings > Remote Access

**Plex Token:**
1. Open Plex Web App in your browser
2. Go to any item and click **"Get Info"** or **"Edit"**
3. Click **"View XML"** in the popup
4. Look at the URL - your token is the string after `X-Plex-Token=`

#### OpenSubtitles Credentials

**You need ALL THREE credentials:** username, password, AND API key.

1. Go to [opensubtitles.com](https://www.opensubtitles.com) and create a free account
2. **Username and Password:** These are your OpenSubtitles login credentials
3. **API Key:** Log in and go to **API Consumers** in your profile
   - Click **"Add New Consumer"**
   - Copy the **API Key** (all three credentials are required to use the API)

### Using Docker (Recommended)

Add to your existing `docker-compose.yml`:

```yaml
services:
  plexsubs:
    image: swordfishtrumpet/plexsubs:latest
    container_name: plexsubs
    ports:
      - "9000:9000"
    environment:
      - PLEX_URL=http://plex:32400
      - PLEX_TOKEN=your_token
      - OPENSUBTITLES_USERNAME=your_username
      - OPENSUBTITLES_PASSWORD=your_password
      - OPENSUBTITLES_API_KEY=your_api_key
      - PLEX_PATH_MAPPINGS=/media:/mnt/library
    restart: unless-stopped
```

Or clone and run standalone:

```bash
git clone https://github.com/SwordfishTrumpet/plexsubs.git
cd plexsubs
cp .env.example .env
# Edit .env with your credentials
docker-compose up -d
```

### Manual Installation

1. **Install uv (if not already installed):**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. **Install dependencies:**
```bash
uv sync
```

3. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your credentials
```

4. **Run the server:**
```bash
uv run python -m plexsubs.main
```

## Configuration

All configuration is done via environment variables or `.env` file:

### Required Settings

```bash
# Plex
PLEX_URL=https://your-plex-server:32400
PLEX_TOKEN=your_plex_token

# OpenSubtitles (all three required)
OPENSUBTITLES_USERNAME=your_username
OPENSUBTITLES_PASSWORD=your_password
OPENSUBTITLES_API_KEY=your_api_key
```

### Optional Settings

```bash
# Languages (ISO 639-1 codes, comma-separated)
# First language is preferred, others are tried in order if not found
SUBTITLES_LANGUAGES=nl,en,de

# Features
SUBTITLES_AUTO_SELECT=true         # Auto-enable subtitles in Plex
SUBTITLES_USE_RELEASE_MATCHING=true # Match by release group
SUBTITLES_UPGRADE_ON_PERFECT_MATCH=true # Replace existing on perfect match

# Path Mappings (Plex path -> local path)
PLEX_PATH_MAPPINGS=/media:/mnt/library

# Discovery Settings
DISCOVERY_ENABLED=true               # Enable discovery endpoints
DISCOVERY_VALIDATE_ON_STARTUP=false  # Validate paths on startup
# DISCOVERY_TEST_FILE=/path/to/test.mkv  # Optional: specific test file
```

### Advanced Settings

```bash
# Logging
LOG_LEVEL=INFO                       # DEBUG, INFO, WARNING, ERROR
LOG_USE_COLORS=true                  # Colored console output
LOG_JSON_FORMAT=false                # JSON format for structured logging
# LOG_FILE=/app/logs/webhook.log     # Optional: log to file

# Server
SERVER_HOST=0.0.0.0                  # Bind address (0.0.0.0 = all interfaces)
SERVER_PORT=9000                     # Port to listen on
SERVER_WEBHOOK_PATH=/plexsubs        # Webhook endpoint path

# Retry Behavior
SUBTITLES_MAX_RETRIES=3              # Download retry attempts
SUBTITLES_RETRY_DELAY_SECONDS=5      # Seconds between retries
```

## Path Mapping Guide

When Plex runs outside Docker and plexsubs runs inside Docker, paths often differ:

**Example Setup:**
- Plex sees: `/media/movies/Inception.mkv`
- Docker container sees: `/mnt/library/movies/Inception.mkv`
- **Mapping needed:** `PLEX_PATH_MAPPINGS=/media:/mnt/library`

**To find the correct mapping:**

1. Check what paths Plex uses:
   ```bash
   curl http://localhost:9000/discover/libraries
   ```

2. Validate your current mapping:
   ```bash
   curl http://localhost:9000/discover/validate-paths
   ```

3. Get suggestions if validation fails:
   ```bash
   curl http://localhost:9000/discover/suggest-mappings
   ```

> 💡 **Pro-Tip:** If you aren't sure about your mappings, run `curl http://localhost:9000/discover/suggest-mappings`. It will compare what Plex reports vs. what the container sees and try to do the math for you.

## Plex Webhook Setup

1. Open Plex Web App
2. Go to **Settings** → **Webhooks**
3. Click **Add Webhook**
4. Enter: `http://your-server:9000/plexsubs`
5. Click **Save**

## Logging

Logs use color-coded prefixes for easy identification:

- `[WEBHOOK]` - Webhook events (cyan)
- `[PLEX]` - Plex API calls (blue)
- `[OPENSUBTITLES]` - OpenSubtitles provider (green)
- `[CORE]` - Core logic (white)
- `[ERROR]` - Errors (red)

## API Endpoints

### Core Endpoints

- `POST /plexsubs` - Plex webhook endpoint
- `GET /health` - Health check
- `GET /config` - Current configuration (no secrets)

### Discovery Endpoints

- `GET /discover/libraries` - List all Plex libraries with their configured paths
- `GET /discover/validate-paths` - Test if path mappings work correctly
- `POST /discover/validate-paths` - Test specific paths with `{"test_paths": ["/media/movie.mkv"]}`
- `GET /discover/suggest-mappings` - Get auto-suggested path mappings
- `GET /discover/status` - Discovery service configuration

### Example Usage

```bash
# Check what paths Plex is using
curl http://localhost:9000/discover/libraries

# Validate your path mappings
curl http://localhost:9000/discover/validate-paths

# Test a specific file
curl -X POST http://localhost:9000/discover/validate-paths \
  -H "Content-Type: application/json" \
  -d '{"test_paths": ["/media/movies/Inception.mkv"]}'

# Get path mapping suggestions
curl http://localhost:9000/discover/suggest-mappings
```

## Project Structure

```
plexsubs/
├── __init__.py
├── main.py                 # FastAPI application
├── api/
│   ├── __init__.py
│   └── discovery.py        # Discovery endpoints
├── config/
│   ├── __init__.py
│   └── settings.py         # Pydantic settings
├── providers/
│   ├── __init__.py
│   ├── base.py             # Provider interface
│   └── opensubtitles.py    # OpenSubtitles API
├── plex/
│   ├── __init__.py
│   ├── client.py           # Plex API client
│   └── webhook.py          # Webhook handler
├── core/
│   ├── __init__.py
│   ├── subtitle_manager.py # Download orchestration
│   ├── release_matcher.py  # Release group matching
│   ├── language_detector.py # Language verification
│   └── discovery.py        # Path discovery and validation
└── utils/
    ├── __init__.py
    ├── exceptions.py       # Custom exceptions
    └── logging_config.py   # Colored logging
```

## Contributing

We welcome your feedback! Here's how to engage with the project:

### Reporting Issues

- **Bug Reports**: Use the [Bug Report template](https://github.com/SwordfishTrumpet/plexsubs/issues/new?template=bug_report.yml) - please include logs!
- **Feature Requests**: Use the [Feature Request template](https://github.com/SwordfishTrumpet/plexsubs/issues/new?template=feature_request.yml)
- **Questions**: Use [GitHub Discussions](https://github.com/SwordfishTrumpet/plexsubs/discussions) instead of Issues

### Pull Requests

**Pull requests are not accepted.** This is a personal project with limited maintenance time. If you'd like to contribute code, please:

1. Fork the repository
2. Make your changes in your fork
3. Use your fork for your own needs

We appreciate your understanding!

## Acknowledgment

Vibed with [Kimi K2.5](https://www.moonshot.ai/)

## License

MIT License
