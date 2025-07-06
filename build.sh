#!/bin/bash

set -e

# Load .env variables if .env file exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Build the image with Nixpacks
echo "Building application with Nixpacks..."
nixpacks build . --start-cmd "gunicorn -c gunicorn_config.py run:app"

# Get the latest image ID created by Nixpacks
IMAGE_ID=$(docker images --format "{{.ID}}" | head -n 1)
echo "Built image with ID: $IMAGE_ID"

# Tag the image
docker tag $IMAGE_ID guerrillatime

# Tag for GitHub Container Registry
GITHUB_USER="digital-guerrilla"
REPO="guerrillatime"
docker tag $IMAGE_ID ghcr.io/$GITHUB_USER/$REPO:latest
echo "Tagged image as ghcr.io/$GITHUB_USER/$REPO:latest"

# Login to GitHub Container Registry
echo "Logging into GitHub Container Registry..."
echo $GITHUB_TOKEN | docker login ghcr.io -u $GITHUB_USER --password-stdin

# Push the image
echo "Pushing image to GitHub Container Registry..."
docker push ghcr.io/$GITHUB_USER/$REPO:latest

# Pull the latest image (ensure you have the latest before redeploy)
echo "Pulling latest image to verify deployment..."
docker pull ghcr.io/$GITHUB_USER/$REPO:latest

echo "Deployment to GitHub Container Registry completed successfully!"
