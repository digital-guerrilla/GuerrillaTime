# PowerShell build script for deploying GuerrillaTime to GitHub Container Registry

$ErrorActionPreference = "Stop"

# Load .env variables if .env file exists
if (Test-Path ".env") {
    Write-Host "Loading environment variables from .env file..."
    Get-Content ".env" | Where-Object { $_ -notmatch '^#' -and $_ -match '=' } | ForEach-Object {
        $name, $value = $_ -split '=', 2
        Set-Item -Path "env:$name" -Value $value
    }
}

# Build the image with Nixpacks
Write-Host "Building application with Nixpacks..." -ForegroundColor Green
nixpacks build . --start-cmd "gunicorn -c gunicorn_config.py run:app"

# Get the latest image ID created by Nixpacks
$IMAGE_ID = (docker images --format "{{.ID}}" | Select-Object -First 1)
Write-Host "Built image with ID: $IMAGE_ID" -ForegroundColor Yellow

# Tag the image
docker tag $IMAGE_ID guerrillatime

# Tag for GitHub Container Registry
$GITHUB_USER = "digital-guerrilla"
$REPO = "guerrillatime"
docker tag $IMAGE_ID "ghcr.io/$GITHUB_USER/$REPO`:latest"
Write-Host "Tagged image as ghcr.io/$GITHUB_USER/$REPO`:latest" -ForegroundColor Yellow

# Login to GitHub Container Registry
Write-Host "Logging into GitHub Container Registry..." -ForegroundColor Green
echo $env:GITHUB_TOKEN | docker login ghcr.io -u $GITHUB_USER --password-stdin

# Push the image
Write-Host "Pushing image to GitHub Container Registry..." -ForegroundColor Green
docker push "ghcr.io/$GITHUB_USER/$REPO`:latest"

# Pull the latest image (ensure you have the latest before redeploy)
Write-Host "Pulling latest image to verify deployment..." -ForegroundColor Green
docker pull "ghcr.io/$GITHUB_USER/$REPO`:latest"

Write-Host "Deployment to GitHub Container Registry completed successfully!" -ForegroundColor Green
