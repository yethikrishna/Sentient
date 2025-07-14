# Use a slim Python base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
# - supervisor: process manager
# - nginx: web server
# - curl, wget, gnupg, unzip: needed for Chrome/Chromedriver install
# - fonts-liberation: avoid font rendering issues
# - xvfb: virtual display for headless Selenium
# - libnss3, libatk-bridge2.0-0: common Chrome runtime deps
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
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

ENV CHROME_VERSION=125.0.6422.112
ENV CHROMEDRIVER_VERSION=125.0.6422.112

# Add Google’s signing key and repository
RUN mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /etc/apt/keyrings/google.gpg \
    && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list

# Install pinned Chrome version
RUN apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable=125.0.6422.112-1 \
    && rm -rf /var/lib/apt/lists/*

# Install Chromedriver
RUN wget -q -O /tmp/chromedriver.zip "https://storage.googleapis.com/chrome-for-testing-public/${CHROMEDRIVER_VERSION}/linux64/chromedriver-linux64.zip" \
    && unzip /tmp/chromedriver.zip -d /usr/local/bin/ \
    && mv /usr/local/bin/chromedriver*/chromedriver /usr/local/bin/chromedriver \
    && rm -rf /usr/local/bin/chromedriver* /tmp/chromedriver.zip \
    && chmod +x /usr/local/bin/chromedriver

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