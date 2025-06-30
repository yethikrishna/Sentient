# src/server/Dockerfile

# Use a slim Python base image for a smaller final container
FROM python:3.11-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies
# - supervisor: to manage all our processes
# - curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    supervisor \
    curl \
    unzip \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create necessary directories
RUN mkdir -p /etc/supervisor/conf.d /var/log/supervisor

# Set the working directory
WORKDIR /app

# Copy the supervisor configuration file from the build context (src/server)
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Install Python dependencies. Note the path is now local to the build context.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy all the server-side Python code from the build context (src/server) into the container
COPY . .

# Copy the startup script and make it executable
COPY start.sh .
RUN chmod +x ./start.sh

# Expose the public port for the main FastAPI server
EXPOSE 5000

# The command to run when the container starts
CMD ["/app/start.sh"]