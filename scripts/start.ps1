param(
  [string]$ModelDir = 'models',
  [string]$ApiKey = $env:CASH_REVIEW_API_KEY,
  [string]$Python = 'python',
  [int]$Port = 8000
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
if (Test-Path -LiteralPath '.venv/Scripts/python.exe') { $Python = (Resolve-Path -LiteralPath '.venv/Scripts/python.exe').Path }
if (-not (Test-Path -LiteralPath 'frontend/dist/index.html')) { throw 'Build the interface first: cd frontend; npm ci; npm run build' }
if (-not (Test-Path -LiteralPath $ModelDir)) { throw 'Prepare and train the model first. See README.md.' }
$env:CASH_REVIEW_MODEL_DIR = (Resolve-Path -LiteralPath $ModelDir).Path
$runtimePath = Join-Path $projectRoot 'runtime'
New-Item -ItemType Directory -Path $runtimePath -Force | Out-Null
$env:CASH_REVIEW_DATA_DIR = $runtimePath
if (-not $ApiKey) {
  $keyPath = Join-Path $runtimePath 'jury-key.txt'
  if (Test-Path -LiteralPath $keyPath) { $ApiKey = (Get-Content -LiteralPath $keyPath -Raw).Trim() }
  else {
    $keyBytes = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($keyBytes) } finally { $rng.Dispose() }
    $ApiKey = [Convert]::ToBase64String($keyBytes)
    Set-Content -LiteralPath $keyPath -Value $ApiKey -NoNewline
  }
  Write-Host "Jury key is stored privately in $keyPath."
}
$env:CASH_REVIEW_API_KEY = $ApiKey
Write-Host "Cash Review: http://127.0.0.1:$Port  (Ctrl+C to stop)"
& $Python -m uvicorn cash_review.app:app --app-dir backend --host 127.0.0.1 --port $Port --workers 1 --no-access-log
exit $LASTEXITCODE
