#!/bin/bash
# Start TAU API Server

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Start server
echo "Starting TAU API Server..."
echo "API docs will be available at http://localhost:8000/docs"
python3 tau/server.py
