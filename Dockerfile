# Scholar Inbox Slack Bot Dockerfile

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml uv.lock requirements.txt ./
COPY src/ ./src/
COPY config.yaml ./
COPY .env.example ./
# Note: .env file is not copied into the image for security reasons.
# It should be mounted at runtime using: -v "$(pwd)/.env:/app/.env"
# or use --env-file .env to pass environment variables directly

# Create virtual environment and install Python dependencies
RUN python -m venv .venv && \
    .venv/bin/pip install --upgrade pip && \
    .venv/bin/pip install -e . && \
    .venv/bin/python -m playwright install chromium && \
    .venv/bin/python -m playwright install-deps chromium

# Create data directory
RUN mkdir -p data/cache

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Set entrypoint (fixed command)
ENTRYPOINT [".venv/bin/python", "-m", "src.main"]

# Default arguments (can be overridden with docker run arguments)
CMD ["--mode", "once"]
