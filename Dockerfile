# Multi-stage build for smaller image
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Create virtual environment and install dependencies
RUN uv venv /opt/venv && \
    VIRTUAL_ENV=/opt/venv uv pip install --no-cache -e .

# Production stage
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r plexsubs && useradd -r -g plexsubs plexsubs

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY plexsubs/ ./plexsubs/

# Change ownership
RUN chown -R plexsubs:plexsubs /app

# Switch to non-root user
USER plexsubs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request, sys; response = urllib.request.urlopen('http://localhost:9000/health', timeout=5); sys.exit(0 if response.status == 200 else 1)"

# Expose port
EXPOSE 9000

# Run the application
CMD ["python", "-m", "plexsubs.main"]
