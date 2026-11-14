@echo off
cd /d "%~dp0"
echo Stopping RAG Technical Documentation Assistant containers...
docker-compose down
echo All containers stopped.
pause

