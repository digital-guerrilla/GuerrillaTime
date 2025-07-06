set -e

# Load .env variables
export $(grep -v '^#' .env | xargs)

# Build the image with Nixpacks
nixpacks build . --start-cmd "gunicorn -c gunicorn_config.py main:app"

# Get the latest image ID created by Nixpacks
IMAGE_ID=$(docker images --format "{{.ID}}" | head -n 1)

# Tag the image
docker tag $IMAGE_ID guerrillatime

# Tag for Docker Hub (replace DOCKERHUB_USER and REPO)
DOCKERHUB_USER="andrewwaring"
REPO="guerrillatime"
docker tag $IMAGE_ID $DOCKERHUB_USER/$REPO:latest

# Login to Docker Hub
echo $DOCKERHUB_TOKEN | docker login -u $DOCKERHUB_USER --password-stdin

# Push the image
docker push $DOCKERHUB_USER/$REPO:latest

# Pull the latest image (ensure you have the latest before redeploy)
docker pull $DOCKERHUB_USER/$REPO:latest