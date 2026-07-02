#!/usr/bin/env pwsh
[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('help', 'install', 'run', 'lint', 'test', 'clean')]
    [string]$Command = 'help'
)

$ErrorActionPreference = 'Stop'

function Invoke-Help {
    Write-Host "install  - sync dependencies (uv sync)"
    Write-Host "run      - start the uploader (loads .env)"
    Write-Host "lint     - run ruff check"
    Write-Host "test     - run pytest"
    Write-Host "clean    - remove __pycache__ and local db"
}

function Import-DotEnv {
    if (-not (Test-Path '.env')) {
        throw ".env not found (required by 'run')"
    }
    foreach ($line in Get-Content '.env') {
        $trimmed = $line.Trim()
        if ($trimmed -eq '' -or $trimmed.StartsWith('#')) { continue }
        if ($trimmed.StartsWith('export ')) { $trimmed = $trimmed.Substring(7).Trim() }
        $pair = $trimmed -split '=', 2
        if ($pair.Count -ne 2) { continue }
        $key = $pair[0].Trim()
        $value = $pair[1].Trim().Trim('"').Trim("'")
        Set-Item -Path "Env:$key" -Value $value
    }
}

function Invoke-Install { uv sync }

function Invoke-Run {
    Import-DotEnv
    $env:PYTHONPATH = 'src'
    uv run python -m bootstrap.main
}

function Invoke-Lint { uv run ruff check . }

function Invoke-Test { uv run pytest -q }

function Invoke-Clean {
    Get-ChildItem -Path . -Directory -Recurse -Filter '__pycache__' |
        Remove-Item -Recurse -Force
    Remove-Item -Path 'drive_uploader.db' -Force -ErrorAction SilentlyContinue
}

switch ($Command) {
    'help' { Invoke-Help }
    'install' { Invoke-Install }
    'run' { Invoke-Run }
    'lint' { Invoke-Lint }
    'test' { Invoke-Test }
    'clean' { Invoke-Clean }
}
