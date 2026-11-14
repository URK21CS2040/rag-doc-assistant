@echo off
cd /d "%~dp0"
echo ========================================================
echo Starting RAG Technical Documentation Assistant
echo ========================================================
echo Checking Docker...
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

echo.
echo Starting containers with docker-compose...
docker-compose up -d

echo.
echo ========================================================
echo [SUCCESS] Application is up and running!
echo ========================================================
echo - Web Dashboard:  http://localhost
echo - API Docs (Docs): http://localhost:8000/docs
echo - Backend Health: http://localhost:8000/documents
echo.
echo Note: If you want to use OpenAI LLM features (Q&A/embeddings),
echo ensure your OPENAI_API_KEY in .env is set to your actual key.
echo ========================================================
pause

