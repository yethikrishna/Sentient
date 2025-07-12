# src/server/Dockerfile

# Use a slim Python base image for a smaller final container
FROM python:3.11-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install system dependencies
# - supervisor: to manage all our processes
# - curl, wget, gnupg, unzip: for installing chrome/chromedriver
RUN apt-get update && apt-get install -y --no-install-recommends \
    supervisor \
    nginx \
    curl \
    dos2unix \
    unzip \
    wget \
    gnupg \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Google Chrome for Selenium
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Install Chromedriver
# Find the latest stable chromedriver version
RUN CHROME_DRIVER_VERSION=$(curl -sS https://storage.googleapis.com/chrome-for-testing-public/LATEST_RELEASE_STABLE) \
    && wget -O /tmp/chromedriver.zip "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_DRIVER_VERSION}/linux64/chromedriver-linux64.zip" \
    && unzip /tmp/chromedriver.zip -d /usr/local/bin/ \
    && mv /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver \
    && rm -rf /usr/local/bin/chromedriver-linux64 /tmp/chromedriver.zip \
    && chmod +x /usr/local/bin/chromedriver

# Create necessary directories
RUN mkdir -p /etc/supervisor/conf.d /var/log/supervisor

# Remove the default Nginx site configuration.
RUN rm /etc/nginx/sites-enabled/default

# Set the working directory
WORKDIR /app

# Install Python dependencies from the master requirements file
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the supervisor configuration file from the build context (src/server)
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copy our custom Nginx configuration
COPY nginx.conf /etc/nginx/sites-available/sentient

# Copy all the server-side Python code from the build context (src/server) into the container
COPY . .
RUN if [ -f /app/.env ]; then dos2unix /app/.env; fi

# Copy the startup script, fix its line endings, and make it executable
COPY start.sh .
RUN dos2unix ./start.sh && chmod +x ./start.sh

# Link our Nginx config to make it active.
RUN ln -s /etc/nginx/sites-available/sentient /etc/nginx/sites-enabled/sentient

# Expose the public port for the main FastAPI server
EXPOSE 5000

# The command to run when the container starts
CMD ["/app/start.sh"]