#!/bin/bash
# Starts the main FastAPI server 

echo "Starting main Uvicorn server..."
# The --forwarded-allow-ips='*' is important for running behind a reverse proxy like Render's
uvicorn main.app:app --host 0.0.0.0 --port $PORT --forwarded-allow-ips='*'