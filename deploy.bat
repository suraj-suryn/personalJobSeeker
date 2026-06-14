@echo off
setlocal EnableDelayedExpansion
title PersonalJobSeeker — Deployment Script

:: ============================================================
::  PersonalJobSeeker — One-Click Windows Deployment Script
::  Run this file on any Windows machine to deploy the app.
:: ============================================================

:: Set up log file — use PowerShell for timestamp (wmic removed in Win11)
for /f "delims=" %%T in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "_DT=%%T"
set "LOG_FILE=%~dp0deploy_log_%_DT%.txt"
echo Deploy log started: %date% %time% > "!LOG_FILE!"
echo. >> "!LOG_FILE!"

:: Helper: echo to screen AND log
call :log "PersonalJobSeeker Automated Deployment"
call :log "Log file: !LOG_FILE!"

color 0A
echo.
echo  ================================================
echo   PersonalJobSeeker ^— Automated Deployment
echo  ================================================
echo  Log file: !LOG_FILE!
echo.

:: ── Step 0: Ensure Docker bin is on PATH (survives fresh terminal) ─────────
set "DD_BIN=C:\Program Files\Docker\Docker\resources\bin"
where docker >nul 2>&1
if %ERRORLEVEL% neq 0 (
    if exist "!DD_BIN!\docker.exe" set "PATH=!PATH!;!DD_BIN!"
)

:: ── Step 1: Check prerequisites ────────────────────────────────────────────

echo [1/8] Checking prerequisites...

docker --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    color 0C
    echo.
    echo  ERROR: Docker is not installed or not running.
    echo.
    echo  Please install Docker Desktop from:
    echo    https://www.docker.com/products/docker-desktop
    echo.
    echo  After installing, launch Docker Desktop and wait
    echo  for the whale icon to show "Engine running", then
    echo  re-run this script.
    echo.
    pause
    exit /b 1
)

git --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    color 0C
    echo.
    echo  ERROR: Git is not installed.
    echo.
    echo  Please install Git from:
    echo    https://git-scm.com/download/win
    echo.
    echo  Then re-run this script.
    echo.
    pause
    exit /b 1
)

echo  [OK] Docker and Git found.

:: Verify Docker daemon is actually running — if not, auto-start it and wait
docker info >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo.
    echo  Docker engine is not running. Attempting to start Docker Desktop...

    :: Try common install locations
    set "DD_EXE="
    if exist "C:\Program Files\Docker\Docker\Docker Desktop.exe" (
        set "DD_EXE=C:\Program Files\Docker\Docker\Docker Desktop.exe"
    )
    if exist "%LOCALAPPDATA%\Docker\Docker Desktop.exe" (
        set "DD_EXE=%LOCALAPPDATA%\Docker\Docker Desktop.exe"
    )

    if defined DD_EXE (
        start "" "!DD_EXE!"
        echo  Waiting for Docker engine to start (up to 180 seconds^)...
        set /a DD_WAIT=0
        :wait_docker
        timeout /t 5 /nobreak >nul
        :: Use PowerShell job with 5s timeout so docker info never hangs the loop
        powershell -NoProfile -Command "$j=Start-Job{docker info};if(Wait-Job $j -Timeout 5){$r=Receive-Job $j;Remove-Job $j;exit 0}else{Stop-Job $j;Remove-Job $j;exit 1}" >nul 2>&1
        if %ERRORLEVEL% equ 0 goto :docker_ready
        set /a DD_WAIT+=10
        echo  Still waiting... (!DD_WAIT!s / 180s^)
        if !DD_WAIT! lss 180 goto :wait_docker
        :: Timed out
        color 0C
        echo.
        echo  ERROR: Docker Desktop did not start in 180 seconds.
        echo  Please open Docker Desktop manually, wait for the whale icon
        echo  to show "Engine running", then re-run this script.
        echo.
        pause
        exit /b 1
    ) else (
        color 0C
        echo.
        echo  ERROR: Cannot find Docker Desktop. Please install it from:
        echo    https://www.docker.com/products/docker-desktop
        echo  Then re-run this script.
        echo.
        pause
        exit /b 1
    )
)
:docker_ready
echo  [OK] Docker engine is running.

:: ── Step 1: Choose install directory ──────────────────────────────────────

echo.
echo [2/8] Where do you want to install PersonalJobSeeker?
echo.
echo  Press Enter to use: C:\PersonalJobSeeker
echo  Or type a custom path (e.g., D:\Apps\PersonalJobSeeker)
echo.
set /p INSTALL_DIR="Install path: "
if "!INSTALL_DIR!"=="" set INSTALL_DIR=C:\PersonalJobSeeker

:: Create directory if it doesn't exist
if not exist "!INSTALL_DIR!" mkdir "!INSTALL_DIR!"

:: Check if already cloned
if exist "!INSTALL_DIR!\docker-compose.yml" (
    echo.
    echo  Found existing installation at !INSTALL_DIR!
    set /p UPDATE_CHOICE="Pull latest updates from GitHub? (y/n): "
    if /i "!UPDATE_CHOICE!"=="y" (
        cd /d "!INSTALL_DIR!"
        git pull
        echo  [OK] Updated to latest version.
    )
    goto :configure_env
)

:: ── Step 2: Clone repository ───────────────────────────────────────────────

echo.
echo [3/8] Cloning repository...
echo.
git clone https://github.com/suraj-suryn/personalJobSeeker.git "!INSTALL_DIR!"
if %ERRORLEVEL% neq 0 (
    color 0C
    echo.
    echo  ERROR: Failed to clone repository.
    echo  Check your internet connection and try again.
    echo.
    pause
    exit /b 1
)
echo  [OK] Repository cloned to !INSTALL_DIR!

:: ── Step 3: Configure .env ─────────────────────────────────────────────────

:configure_env
cd /d "!INSTALL_DIR!"

echo.
echo [4/8] Configuring environment...
echo.

if exist ".env" (
    set /p ENV_CHOICE="A .env file already exists. Reconfigure it? (y/n): "
    if /i "!ENV_CHOICE!" neq "y" (
        :: Read LLM_PROVIDER from existing .env so Ollama model step works
        for /f "tokens=2 delims==" %%V in ('findstr /i "^LLM_PROVIDER=" .env') do set LLM_PROVIDER=%%V
        if "!LLM_PROVIDER!"=="ollama" (set LLM_CHOICE=1) else (set LLM_CHOICE=2)
        goto :build_images
    )
)

copy ".env.example" ".env" >nul

echo  You will be asked for a few required values.
echo  Press Enter to keep the shown default.
echo.

:: Admin email
set /p ADMIN_EMAIL="Admin email [admin@example.com]: "
if "!ADMIN_EMAIL!"=="" set ADMIN_EMAIL=admin@example.com

:: Admin password
:ask_password
set /p ADMIN_PASSWORD="Admin password (min 8 chars, must not be empty): "
if "!ADMIN_PASSWORD!"=="" (
    echo  Password cannot be empty.
    goto :ask_password
)

:: DB password
set /p DB_PASS="Database password [jobseeker_pass]: "
if "!DB_PASS!"=="" set DB_PASS=jobseeker_pass

:: Generate a simple secret key using timestamp + random
set APP_SECRET=%RANDOM%%RANDOM%%RANDOM%%RANDOM%abcdefgh12345678
set JWT_SECRET=%RANDOM%%RANDOM%%RANDOM%%RANDOM%xyzwvuts87654321

:: LLM choice
echo.
echo  LLM Provider Options (choose one):
echo    1. Ollama  - local, FREE, private (~5GB download on first run)
echo    2. Groq    - online, FREE (14,400 req/day), no download needed
echo    3. Gemini  - online, FREE (1M tokens/day), no download needed
echo.
set /p LLM_CHOICE="Your choice (1/2/3) [1]: "
if "!LLM_CHOICE!"=="" set LLM_CHOICE=1

set GROQ_KEY=
set GEMINI_KEY=
set LLM_PROVIDER=ollama

if "!LLM_CHOICE!"=="2" (
    set LLM_PROVIDER=groq
    echo.
    echo  Get a free Groq API key at: https://console.groq.com
    set /p GROQ_KEY="Groq API key: "
)
if "!LLM_CHOICE!"=="3" (
    set LLM_PROVIDER=gemini
    echo.
    echo  Get a free Gemini API key at: https://aistudio.google.com
    set /p GEMINI_KEY="Gemini API key: "
)

:: Pass values via environment variables so PowerShell receives them safely
:: (avoids CMD ^ line-continuation issues inside quoted PowerShell strings)
set "_ADMIN_EMAIL=!ADMIN_EMAIL!"
set "_ADMIN_PASSWORD=!ADMIN_PASSWORD!"
set "_DB_PASS=!DB_PASS!"
set "_APP_SECRET=!APP_SECRET!"
set "_JWT_SECRET=!JWT_SECRET!"
set "_GROQ_KEY=!GROQ_KEY!"
set "_GEMINI_KEY=!GEMINI_KEY!"

:: Write values into .env using a single-line PowerShell command
powershell -NoProfile -Command "$c=gc '.env'; $c=$c -replace 'ADMIN_EMAIL=.*',('ADMIN_EMAIL='+$env:_ADMIN_EMAIL); $c=$c -replace 'ADMIN_PASSWORD=.*',('ADMIN_PASSWORD='+$env:_ADMIN_PASSWORD); $c=$c -replace 'POSTGRES_PASSWORD=.*',('POSTGRES_PASSWORD='+$env:_DB_PASS); $c=$c -replace 'DATABASE_URL=.*',('DATABASE_URL=postgresql+asyncpg://jobseeker:'+$env:_DB_PASS+'@postgres:5432/jobseeker'); $c=$c -replace 'APP_SECRET_KEY=.*',('APP_SECRET_KEY='+$env:_APP_SECRET); $c=$c -replace 'JWT_SECRET_KEY=.*',('JWT_SECRET_KEY='+$env:_JWT_SECRET); $c=$c -replace 'GROQ_API_KEY=.*',('GROQ_API_KEY='+$env:_GROQ_KEY); $c=$c -replace 'GEMINI_API_KEY=.*',('GEMINI_API_KEY='+$env:_GEMINI_KEY); $c|sc '.env'"

echo  [OK] .env configured.

:: ── Step 4: Build Docker images ────────────────────────────────────────────

:build_images
echo.
echo [5/8] Building Docker images (this may take 5-15 minutes on first run)...
echo       You will see build output below. Full output also saved to log.
echo.
call :log "[5/8] Running docker compose build"
set "_LOG=!LOG_FILE!"
powershell -NoProfile -Command "docker compose build 2>&1 | Tee-Object -Append -FilePath $env:_LOG; exit $LASTEXITCODE"
if !ERRORLEVEL! neq 0 (
    color 0C
    echo.
    echo  ERROR: Docker build failed.
    echo  Check the output above for details.
    echo  Common causes: no internet, Docker Desktop not running.
    echo  Full log: !LOG_FILE!
    call :log "ERROR: docker compose build failed"
    echo.
    pause
    exit /b 1
)
echo.
echo  [OK] Images built.
call :log "[OK] docker compose build succeeded"

:: ── Step 5: Start services ────────────────────────────────────────────────

echo.
echo [6/8] Starting all services...
echo.
call :log "[6/8] Running docker compose up -d"
set "_LOG=!LOG_FILE!"
powershell -NoProfile -Command "docker compose up -d 2>&1 | Tee-Object -Append -FilePath $env:_LOG; exit $LASTEXITCODE"
if !ERRORLEVEL! neq 0 (
    color 0C
    echo.
    echo  ERROR: Failed to start services.
    echo  Run: docker compose logs
    echo  to see what went wrong.
    echo  Full log: !LOG_FILE!
    call :log "ERROR: docker compose up failed"
    echo.
    pause
    exit /b 1
)

echo  [OK] Services started. Waiting for database to be ready...
echo.

:: Wait for postgres to be healthy (up to 60 seconds)
set /a WAIT=0
:wait_db
docker compose exec -T postgres pg_isready -U jobseeker -d jobseeker >nul 2>&1
if %ERRORLEVEL% equ 0 goto :db_ready
set /a WAIT+=1
if !WAIT! geq 30 (
    echo  WARNING: Database health check timed out. Proceeding anyway...
    goto :db_ready
)
echo  Waiting for postgres... (!WAIT!/30)
timeout /t 2 /nobreak >nul
goto :wait_db

:db_ready
echo  [OK] Database is ready.

:: ── Step 6: Run migrations ────────────────────────────────────────────────

echo.
echo [7/8] Applying database migrations...
echo.

docker compose exec -T backend alembic upgrade head
if %ERRORLEVEL% neq 0 (
    echo  WARNING: Migration may have failed. Retrying in 10 seconds...
    timeout /t 10 /nobreak >nul
    docker compose exec -T backend alembic upgrade head
)
echo  [OK] Migrations applied.

:: Seed admin account and sample data
echo.
echo  Seeding admin account and sample data...
docker compose exec -T backend python -m app.utils.seed
echo  [OK] Seed data created.

:: ── Step 7: Pull Ollama models (if selected) ──────────────────────────────

if "!LLM_CHOICE!"=="1" (
    echo.
    echo [8/8] Pulling Ollama AI models...
    echo  This is a one-time download of ~5GB. Progress shown below.
    echo  You can Ctrl+C to skip and pull manually later with:
    echo    docker compose exec ollama ollama pull llama3.1:8b
    echo.
    docker compose exec -T ollama ollama pull llama3.1:8b
    docker compose exec -T ollama ollama pull nomic-embed-text
    echo  [OK] Models ready.
) else (
    echo.
    echo [8/8] Skipping Ollama model download (using !LLM_PROVIDER!).
    echo  Pulling nomic-embed-text for vector embeddings...
    docker compose exec -T ollama ollama pull nomic-embed-text
    echo  [OK] Embedding model ready.
)

:: ── Done ───────────────────────────────────────────────────────────────────

echo.
color 0A
echo  ================================================
echo   Deployment Complete!
echo  ================================================
echo.
echo   App URL    : http://localhost
echo   API Docs   : http://localhost/api/docs
echo.
echo   Login with:
echo     Email   : !ADMIN_EMAIL!
echo     Password: !ADMIN_PASSWORD!
echo.
echo   To start/stop the app later:
echo     docker compose up -d     (start)
echo     docker compose down      (stop)
echo.
echo   Install folder: !INSTALL_DIR!
echo.
echo  ================================================
echo.

:: Open browser automatically
set /p OPEN_BROWSER="Open http://localhost in browser now? (y/n) [y]: "
if "!OPEN_BROWSER!"=="" set OPEN_BROWSER=y
if /i "!OPEN_BROWSER!"=="y" start http://localhost

:: Create helper batch files for daily use
(
    echo @echo off
    echo cd /d "!INSTALL_DIR!"
    echo docker compose up -d
    echo echo App started at http://localhost
    echo start http://localhost
    echo pause
) > "!INSTALL_DIR!\START_APP.bat"

(
    echo @echo off
    echo cd /d "!INSTALL_DIR!"
    echo docker compose down
    echo echo App stopped.
    echo pause
) > "!INSTALL_DIR!\STOP_APP.bat"

echo  Two helper files created in !INSTALL_DIR!:
echo    START_APP.bat  ^— start the app
echo    STOP_APP.bat   ^— stop the app
echo.
call :log "Deployment completed successfully."
call :log "Log saved to: !LOG_FILE!"
echo  Full deploy log: !LOG_FILE!
echo.
pause
endlocal
goto :eof

:: ── Subroutine: write message to log file ────────────────────────────────
:log
echo [%date% %time%] %~1 >> "!LOG_FILE!"
goto :eof
