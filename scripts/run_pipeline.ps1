# Pipeline complet LIORA (Windows PowerShell)
param(
    [int]$MaxReviews = 80
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
Set-Location $Root

$env:PYTHONPATH = "$Root\src"
$env:DATA_DIR = "$Root\data"

Write-Host "=== 1. Scraping Trustpilot ===" -ForegroundColor Cyan
python -m liora.scraper.run_scraper --max-reviews $MaxReviews

Write-Host "=== 2. PostgreSQL ===" -ForegroundColor Cyan
python -m liora.etl.load_postgres

Write-Host "=== 3. MongoDB + Elasticsearch ===" -ForegroundColor Cyan
python -m liora.etl.load_mongodb

Write-Host "=== 4. ML + MLflow ===" -ForegroundColor Cyan
python -m liora.ml.train

Write-Host "=== 5. Dérive ===" -ForegroundColor Cyan
python -m liora.ml.drift

Write-Host "Pipeline terminé." -ForegroundColor Green
