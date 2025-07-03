# src/server/Dockerfile

# Use a slim Python base image for a smaller final container
FROM python:3.11-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install system dependencies
# - supervisor: to manage all our processes
# - curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    supervisor \
    nginx \
    curl \
    dos2unix \
    unzip \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

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