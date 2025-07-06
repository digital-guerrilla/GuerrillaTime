# GuerrillaTime - GitHub Container Registry Build

This repository contains build scripts for deploying GuerrillaTime to GitHub Container Registry.

## Quick Start

### Prerequisites
- Docker installed and running
- Nixpacks installed (`curl -sSL https://nixpacks.com/install.sh | bash`)
- GitHub token with `packages:write` permission

### Local Build

1. **Set up environment**:
   ```bash
   export GITHUB_TOKEN=your_github_token_here
   ```

2. **Run build script**:
   ```bash
   # For Linux/macOS
   chmod +x build.sh
   ./build.sh
   
   # For Windows PowerShell
   .\build.ps1
   ```

### Automated Deployment

Push to main/master branch and GitHub Actions will automatically:
- Build with Nixpacks
- Push to `ghcr.io/digital-guerrilla/guerrillatime:latest`
- Notify on completion

### Using the Built Image

```bash
# Pull the image
docker pull ghcr.io/digital-guerrilla/guerrillatime:latest

# Run the container
docker run -p 8000:8000 \
  -e SECRET_KEY=your_secret_key \
  ghcr.io/digital-guerrilla/guerrillatime:latest
```

## Files Created

- `build.sh` - Unix/Linux build script
- `build.ps1` - Windows PowerShell build script  
- `gunicorn_config.py` - Production Gunicorn configuration
- `.github/workflows/deploy.yml` - GitHub Actions workflow
- Updated `nixpacks.toml` - Nixpacks configuration
- Updated `DEPLOYMENT.md` - Comprehensive deployment guide

## Configuration

The build uses:
- **Base Image**: Nixpacks-generated container
- **Runtime**: Python 3.10
- **Server**: Gunicorn with optimized settings
- **Registry**: GitHub Container Registry (ghcr.io)
- **Repository**: `digital-guerrilla/guerrillatime`

## Support

See `DEPLOYMENT.md` for detailed deployment instructions and troubleshooting.
