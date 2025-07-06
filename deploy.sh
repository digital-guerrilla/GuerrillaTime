#!/bin/bash

# Guerrilla T Timesheet - Docker Build & Deploy Script
# This script builds and runs the timesheet application using nixpacks

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="guerrilla-t-timesheet"
CONTAINER_NAME="guerrilla-t-app"
PORT=${PORT:-5000}

echo -e "${BLUE}🚀 Guerrilla T Timesheet - Docker Deployment${NC}"
echo "================================================="

# Function to generate secure secrets
generate_secrets() {
    echo -e "${YELLOW}🔐 Generating secure secrets...${NC}"
    
    # Generate SECRET_KEY
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || openssl rand -hex 32)
    
    # Generate API_KEY
    API_KEY="timesheet-api-$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || openssl rand -base64 32 | tr -d '=' | tr '+/' '-_')"
    
    echo -e "${GREEN}✓ Secrets generated successfully${NC}"
}

# Function to check if nixpacks is installed
check_nixpacks() {
    if ! command -v nixpacks &> /dev/null; then
        echo -e "${RED}❌ nixpacks is not installed${NC}"
        echo "Please install nixpacks first:"
        echo "  curl -sSL https://nixpacks.com/install.sh | bash"
        echo "  or"
        echo "  cargo install nixpacks"
        exit 1
    fi
    echo -e "${GREEN}✓ nixpacks found${NC}"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info &> /dev/null; then
        echo -e "${RED}❌ Docker is not running or not accessible${NC}"
        echo "Please start Docker and try again."
        exit 1
    fi
    echo -e "${GREEN}✓ Docker is running${NC}"
}

# Function to prompt for environment variables
prompt_env_vars() {
    echo -e "${YELLOW}📝 Please provide the following configuration:${NC}"
    echo ""
    
    # Admin email
    read -p "Admin Email: " ADMIN_EMAIL
    if [[ -z "$ADMIN_EMAIL" ]]; then
        echo -e "${RED}❌ Admin email is required${NC}"
        exit 1
    fi
    
    # Admin password
    echo -n "Admin Password: "
    read -s ADMIN_PASSWORD
    echo ""
    if [[ -z "$ADMIN_PASSWORD" ]]; then
        echo -e "${RED}❌ Admin password is required${NC}"
        exit 1
    fi
    
    # Optional: Custom port
    read -p "Port (default: 5000): " CUSTOM_PORT
    if [[ -n "$CUSTOM_PORT" ]]; then
        PORT=$CUSTOM_PORT
    fi
    
    echo -e "${GREEN}✓ Configuration collected${NC}"
}

# Function to build the Docker image
build_image() {
    echo -e "${YELLOW}🏗️  Building Docker image with nixpacks...${NC}"
    
    # Remove existing image if it exists
    if docker image inspect $IMAGE_NAME &> /dev/null; then
        echo -e "${YELLOW}🗑️  Removing existing image...${NC}"
        docker rmi $IMAGE_NAME
    fi
    
    # Build with nixpacks
    nixpacks build . --name $IMAGE_NAME
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Docker image built successfully${NC}"
    else
        echo -e "${RED}❌ Failed to build Docker image${NC}"
        exit 1
    fi
}

# Function to stop and remove existing container
cleanup_container() {
    if docker container inspect $CONTAINER_NAME &> /dev/null; then
        echo -e "${YELLOW}🧹 Stopping and removing existing container...${NC}"
        docker stop $CONTAINER_NAME
        docker rm $CONTAINER_NAME
    fi
}

# Function to run the container
run_container() {
    echo -e "${YELLOW}🚀 Starting container...${NC}"
    
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
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Container started successfully${NC}"
    else
        echo -e "${RED}❌ Failed to start container${NC}"
        exit 1
    fi
}

# Function to wait for application to be ready
wait_for_app() {
    echo -e "${YELLOW}⏳ Waiting for application to be ready...${NC}"
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Application is ready!${NC}"
            return 0
        fi
        
        echo -n "."
        sleep 2
        ((attempt++))
    done
    
    echo -e "${RED}❌ Application failed to start within expected time${NC}"
    echo "Check container logs: docker logs $CONTAINER_NAME"
    return 1
}

# Function to display success information
show_success() {
    echo ""
    echo -e "${GREEN}🎉 Deployment successful!${NC}"
    echo "================================="
    echo -e "📱 Application URL: ${BLUE}http://localhost:$PORT${NC}"
    echo -e "🔍 Health Check: ${BLUE}http://localhost:$PORT/health${NC}"
    echo -e "👤 Admin Email: ${YELLOW}$ADMIN_EMAIL${NC}"
    echo -e "🔑 API Key: ${YELLOW}$API_KEY${NC}"
    echo ""
    echo -e "${YELLOW}Useful Commands:${NC}"
    echo "  View logs:    docker logs $CONTAINER_NAME"
    echo "  Stop app:     docker stop $CONTAINER_NAME"
    echo "  Start app:    docker start $CONTAINER_NAME"
    echo "  Remove app:   docker rm $CONTAINER_NAME"
    echo "  Rebuild:      ./deploy.sh"
    echo ""
    echo -e "${BLUE}💾 Database is persisted in: ./data/${NC}"
    echo -e "${RED}⚠️  Keep your API key secure for Power BI integration!${NC}"
}

# Function to create data directory
create_data_dir() {
    mkdir -p data
    echo -e "${GREEN}✓ Data directory created${NC}"
}

# Main execution
main() {
    echo -e "${BLUE}Starting deployment process...${NC}"
    echo ""
    
    # Check prerequisites
    check_nixpacks
    check_docker
    
    # Generate secrets
    generate_secrets
    
    # Get user input
    prompt_env_vars
    
    # Create data directory for database persistence
    create_data_dir
    
    # Build and deploy
    build_image
    cleanup_container
    run_container
    
    # Wait for app to be ready
    if wait_for_app; then
        show_success
    else
        echo -e "${RED}❌ Deployment completed but application may not be running correctly${NC}"
        echo "Check the logs for more information:"
        echo "  docker logs $CONTAINER_NAME"
        exit 1
    fi
}

# Handle script interruption
trap 'echo -e "\n${RED}❌ Deployment interrupted${NC}"; exit 1' INT

# Run main function
main

echo -e "${GREEN}✅ Script completed successfully!${NC}"
