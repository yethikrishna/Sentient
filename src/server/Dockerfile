# Use a slim Python base image
FROM python:3.11-slim

# Set early environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DEBIAN_FRONTEND=noninteractive \
    OLLAMA_HOST=0.0.0.0

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    supervisor \
    nginx \
    curl \
    dos2unix \
    ca-certificates \
    gnupg \
    python3-pip \
    antiword \
    poppler-utils \
    tesseract-ocr \
    unrtf \
    && rm -rf /var/lib/apt/lists/*

# Set working directory early
WORKDIR /app

# Only copy and install Python requirements first to enable caching
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers and dependencies
RUN playwright install --with-deps

# --- Build Arguments for Ollama ---
ARG OPENAI_API_KEY
ARG OPENAI_MODEL_NAME

# Install Ollama conditionally (this layer is built later)
RUN if [ "$OPENAI_API_KEY" = "ollama" ]; then \
    echo "Ollama API key detected. Installing Ollama..."; \
    curl -fsSL https://ollama.com/install.sh | sh; \
    echo "Pulling model: ${OPENAI_MODEL_NAME}"; \
    /usr/local/bin/ollama pull ${OPENAI_MODEL_NAME}; \
    else \
    echo "Ollama configuration not detected. Skipping installation."; \
    fi

# Copy project files after installing deps
COPY . .

# Fix line endings for .env and start.sh (if they exist)
RUN if [ -f /app/.env ]; then dos2unix /app/.env; fi \
    && dos2unix /app/start.sh \
    && chmod +x /app/start.sh

# Remove default Nginx site and add custom config
RUN rm -f /etc/nginx/sites-enabled/default \
    && cp /etc/nginx/sites-available/sentient /etc/nginx/sites-enabled/sentient

# Create necessary directories
RUN mkdir -p /etc/supervisor/conf.d /var/log/supervisor

# Copy supervisord config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose application port
EXPOSE 5000

# Run app
CMD ["/app/start.sh"]