#!/bin/bash

# Quick Deploy Script for Guerrilla T Timesheet
# Minimal configuration deployment

set -e

echo "🚀 Guerrilla T - Quick Deploy"
echo "============================="

# Default configuration
IMAGE_NAME="guerrilla-t-timesheet"
CONTAINER_NAME="guerrilla-t-app"
PORT=5000

# Generate secrets automatically
echo "🔐 Generating secure configuration..."
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || openssl rand -hex 32)
API_KEY="timesheet-api-$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || openssl rand -base64 32 | tr -d '=' | tr '+/' '-_')"

# Default admin credentials (user should change these)
ADMIN_EMAIL="admin@localhost"
ADMIN_PASSWORD="admin123-CHANGE-ME"

echo "⚠️  Using default admin credentials - CHANGE THEM AFTER DEPLOYMENT!"
echo "   Email: $ADMIN_EMAIL"
echo "   Password: $ADMIN_PASSWORD"
echo ""

# Check if nixpacks exists
if ! command -v nixpacks &> /dev/null; then
    echo "❌ nixpacks not found. Installing..."
    curl -sSL https://nixpacks.com/install.sh | bash
fi

# Create data directory
mkdir -p data

# Stop existing container
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true

# Remove existing image
docker rmi $IMAGE_NAME 2>/dev/null || true

echo "🏗️  Building application..."
nixpacks build . --name $IMAGE_NAME

echo "🚀 Starting application..."
docker run -d \
    --name $CONTAINER_NAME \
    -p $PORT:$PORT \
    -e SECRET_KEY="$SECRET_KEY" \
    -e ADMIN_EMAIL="$ADMIN_EMAIL" \
    -e ADMIN_PASSWORD="$ADMIN_PASSWORD" \
    -e API_KEY="$API_KEY" \
    -e PORT="$PORT" \
    -e FLASK_ENV="production" \
    -e FLASK_DEBUG="false" \
    -v $(pwd)/data:/app/data \
    --restart unless-stopped \
    $IMAGE_NAME

# Wait for app to start
echo "⏳ Waiting for application..."
sleep 10

# Check if app is running
if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
    echo ""
    echo "✅ SUCCESS! Application is running"
    echo "📱 URL: http://localhost:$PORT"
    echo "👤 Login: $ADMIN_EMAIL / $ADMIN_PASSWORD"
    echo "🔑 API Key: $API_KEY"
    echo ""
    echo "⚠️  IMPORTANT: Change the admin password after first login!"
else
    echo "❌ Application may not be running correctly"
    echo "Check logs: docker logs $CONTAINER_NAME"
fi
