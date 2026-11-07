$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$EnvironmentRoot = Join-Path $ProjectRoot ".venv"
$CacheRoot = Join-Path $ProjectRoot ".pip-cache"
$TempRoot = Join-Path $ProjectRoot ".tmp"
$HuggingFaceRoot = Join-Path $ProjectRoot ".hf-cache"
$LayaRoot = Join-Path $ProjectRoot ".laya-cache"

foreach ($Path in @($CacheRoot, $TempRoot, $HuggingFaceRoot, $LayaRoot)) {
    New-Item -ItemType Directory -Force -Path $Path | Out-Null
}

$env:TEMP = $TempRoot
$env:TMP = $TempRoot
$env:PIP_CACHE_DIR = $CacheRoot
$env:HF_HOME = $HuggingFaceRoot
$env:TRANSFORMERS_CACHE = $HuggingFaceRoot
$env:LAYA_CACHE_DIR = $LayaRoot
$env:VIRTUAL_ENV = $EnvironmentRoot
$env:PATH = (Join-Path $EnvironmentRoot "Scripts") + ";" + $env:PATH

Write-Output "F-drive project environment configured."
Write-Output "Python: $(Join-Path $EnvironmentRoot 'Scripts\python.exe')"
Write-Output "Caches: $CacheRoot"
Write-Output "Temporary files: $TempRoot"
