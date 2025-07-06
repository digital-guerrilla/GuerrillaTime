@echo off
setlocal enabledelayedexpansion

REM Guerrilla T Timesheet - Windows Docker Deploy Script
echo 🚀 Guerrilla T Timesheet - Docker Deployment
echo =================================================

REM Configuration
set IMAGE_NAME=guerrilla-t-timesheet
set CONTAINER_NAME=guerrilla-t-app
set PORT=5000

REM Check if nixpacks is installed
nixpacks --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ nixpacks is not installed
    echo Please install nixpacks first:
    echo   Visit: https://nixpacks.com/docs/install
    pause
    exit /b 1
)
echo ✓ nixpacks found

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not running or not accessible
    echo Please start Docker and try again.
    pause
    exit /b 1
)
echo ✓ Docker is running

REM Generate secrets
echo 🔐 Generating secure secrets...
for /f %%i in ('python -c "import secrets; print(secrets.token_hex(32))"') do set SECRET_KEY=%%i
for /f %%i in ('python -c "import secrets; print('timesheet-api-' + secrets.token_urlsafe(32))"') do set API_KEY=%%i

REM Get user input
echo.
echo 📝 Please provide the following configuration:
set /p ADMIN_EMAIL=Admin Email: 
if "%ADMIN_EMAIL%"=="" (
    echo ❌ Admin email is required
    pause
    exit /b 1
)

set /p ADMIN_PASSWORD=Admin Password: 
if "%ADMIN_PASSWORD%"=="" (
    echo ❌ Admin password is required
    pause
    exit /b 1
)

set /p CUSTOM_PORT=Port (default: 5000): 
if not "%CUSTOM_PORT%"=="" set PORT=%CUSTOM_PORT%

echo ✓ Configuration collected

REM Create data directory
if not exist data mkdir data
echo ✓ Data directory created

REM Stop and remove existing container
echo 🧹 Cleaning up existing container...
docker stop %CONTAINER_NAME% >nul 2>&1
docker rm %CONTAINER_NAME% >nul 2>&1

REM Remove existing image
docker rmi %IMAGE_NAME% >nul 2>&1

REM Build with nixpacks
echo 🏗️ Building Docker image with nixpacks...
nixpacks build . --name %IMAGE_NAME%
if %errorlevel% neq 0 (
    echo ❌ Failed to build Docker image
    pause
    exit /b 1
)
echo ✓ Docker image built successfully

REM Run container
echo 🚀 Starting container...
docker run -d ^
    --name %CONTAINER_NAME% ^
    -p %PORT%:%PORT% ^
    -e SECRET_KEY=%SECRET_KEY% ^
    -e ADMIN_EMAIL=%ADMIN_EMAIL% ^
    -e ADMIN_PASSWORD=%ADMIN_PASSWORD% ^
    -e API_KEY=%API_KEY% ^
    -e PORT=%PORT% ^
    -e FLASK_ENV=production ^
    -e FLASK_DEBUG=false ^
    -v %cd%/data:/app/data ^
    --restart unless-stopped ^
    %IMAGE_NAME%

if %errorlevel% neq 0 (
    echo ❌ Failed to start container
    pause
    exit /b 1
)
echo ✓ Container started successfully

REM Wait for application to be ready
echo ⏳ Waiting for application to be ready...
timeout /t 10 /nobreak >nul

REM Test health endpoint
curl -s http://localhost:%PORT%/health >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ Application is ready!
    echo.
    echo 🎉 Deployment successful!
    echo =================================
    echo 📱 Application URL: http://localhost:%PORT%
    echo 🔍 Health Check: http://localhost:%PORT%/health
    echo 👤 Admin Email: %ADMIN_EMAIL%
    echo 🔑 API Key: %API_KEY%
    echo.
    echo Useful Commands:
    echo   View logs:    docker logs %CONTAINER_NAME%
    echo   Stop app:     docker stop %CONTAINER_NAME%
    echo   Start app:    docker start %CONTAINER_NAME%
    echo   Remove app:   docker rm %CONTAINER_NAME%
    echo.
    echo 💾 Database is persisted in: ./data/
    echo ⚠️ Keep your API key secure for Power BI integration!
) else (
    echo ❌ Application failed to start within expected time
    echo Check container logs: docker logs %CONTAINER_NAME%
)

echo.
echo ✅ Script completed!
pause
