# Use a slim Python base image
FROM python:3.11-slim

# --- Build Arguments ---
# These arguments are passed from docker-compose.yaml or the `docker build` command.
ARG OPENAI_API_KEY
ARG OPENAI_MODEL_NAME

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DEBIAN_FRONTEND=noninteractive \
    CHROME_VERSION=138.0.7204.157 \
    CHROMEDRIVER_VERSION=138.0.7204.157 \
    CHROME_BIN=/opt/chrome/chrome
# Set Ollama to listen on all interfaces within the container
ENV OLLAMA_HOST=0.0.0.0

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    supervisor \
    nginx \
    curl \
    wget \
    unzip \
    dos2unix \
    ca-certificates \
    gnupg \
    xvfb \
    libnss3 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libasound2 \
    libgbm1 \
    libxshmfence1 \
    fonts-liberation \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Download and install Chrome-for-Testing
RUN mkdir -p /opt/chrome \
    && wget -q -O /tmp/chrome-linux64.zip "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chrome-linux64.zip" \
    && unzip -q /tmp/chrome-linux64.zip -d /opt/ \
    && mv /opt/chrome-linux64/* /opt/chrome/ \
    && chmod +x /opt/chrome/chrome \
    && rm -rf /tmp/chrome-linux64.zip

# Install matching Chromedriver
RUN wget -q -O /tmp/chromedriver.zip "https://storage.googleapis.com/chrome-for-testing-public/${CHROMEDRIVER_VERSION}/linux64/chromedriver-linux64.zip" \
    && unzip -j /tmp/chromedriver.zip '*/chromedriver' -d /usr/local/bin/ \
    && chmod +x /usr/local/bin/chromedriver \
    && rm -f /tmp/chromedriver.zip

# --- Conditional Ollama Installation ---
# This checks if the API key is set to 'ollama'. If so, install Ollama and pull the specified model.
# This is checked during the 'docker build' process.
RUN if [ "$OPENAI_API_KEY" = "ollama" ]; then \
    echo "Ollama API key detected. Installing Ollama..."; \
    curl -fsSL https://ollama.com/install.sh | sh; \
    echo "Pulling model: ${OPENAI_MODEL_NAME}"; \
    /usr/local/bin/ollama pull ${OPENAI_MODEL_NAME}; \
    else \
    echo "Ollama configuration not detected. Skipping installation."; \
    fi

# Create required directories
RUN mkdir -p /etc/supervisor/conf.d /var/log/supervisor

# Remove default Nginx site configuration
RUN rm -f /etc/nginx/sites-enabled/default

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy configuration files and server code
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY nginx.conf /etc/nginx/sites-available/sentient
COPY . .

# Fix line endings for .env and start.sh (if present)
RUN if [ -f /app/.env ]; then dos2unix /app/.env; fi \
    && dos2unix /app/start.sh \
    && chmod +x /app/start.sh

# Enable custom Nginx site
RUN ln -s /etc/nginx/sites-available/sentient /etc/nginx/sites-enabled/sentient

# Expose port
EXPOSE 5000

# Start Xvfb and our processes using supervisord
CMD ["/app/start.sh"]