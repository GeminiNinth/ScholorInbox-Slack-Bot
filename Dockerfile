# Scholar Inbox Slack Bot Dockerfile

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Copy project files
COPY pyproject.toml uv.lock requirements.txt ./
COPY src/ ./src/
COPY config.yaml ./
COPY .env.example ./

# Install Python dependencies
RUN uv venv && \
    . .venv/bin/activate && \
    uv pip install -r requirements.txt && \
    playwright install chromium && \
    playwright install-deps chromium

# Create data directory
RUN mkdir -p data/cache

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the bot
CMD [".venv/bin/python", "-m", "src.main", "--mode", "scheduled"]
