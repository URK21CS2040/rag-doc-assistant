# PowerShell startup script for RAG Technical Documentation Assistant
Set-Location -Path $PSScriptRoot

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Starting RAG Technical Documentation Assistant" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

docker info > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Docker is not running. Please launch Docker Desktop first." -ForegroundColor Red
    exit 1
}

Write-Host "Bringing up containers with docker-compose..." -ForegroundColor Yellow
docker-compose up -d

Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host "Application is live and ready!" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host "Web Dashboard:   http://localhost" -ForegroundColor White
Write-Host "API Swagger UI:  http://localhost:8000/docs" -ForegroundColor White
Write-Host "API Documents:   http://localhost:8000/documents" -ForegroundColor White
Write-Host "========================================================" -ForegroundColor Green

