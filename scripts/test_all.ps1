param(
    [ValidateSet("default", "backend", "python", "frontend", "all")]
    [string] $Suite = "default",
    [switch] $IncludeE2E,
    [switch] $IncludeGPU,
    [switch] $SkipFrontend,
    [switch] $SkipPython,
    [string] $CondaEnv = "detect",
    [string] $DatabaseMode = "local"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$env:DATABASE_MODE = $DatabaseMode

$RepoRoot = Split-Path -Parent $PSScriptRoot

function Invoke-Step {
    param(
        [string] $Name,
        [string] $WorkingDirectory,
        [string[]] $Command
    )

    Write-Host ""
    Write-Host "==> $Name" -ForegroundColor Cyan
    Write-Host "    cd $WorkingDirectory"
    Write-Host "    $($Command -join ' ')"

    Push-Location $WorkingDirectory
    try {
        & $Command[0] @($Command[1..($Command.Length - 1)])
        if ($LASTEXITCODE -ne 0) {
            throw "$Name failed with exit code $LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }
}

function Test-CommandExists {
    param([string] $CommandName)
    return $null -ne (Get-Command $CommandName -ErrorAction SilentlyContinue)
}

function Invoke-BackendSuite {
    $BackendDir = Join-Path $RepoRoot "AIDetector/code/backend/backend-code"

    $MarkerExpr = "not gpu and not e2e and not slow"
    if ($IncludeGPU) {
        $MarkerExpr = "not e2e and not slow"
    }

    Invoke-Step `
        -Name "backend migrate" `
        -WorkingDirectory $BackendDir `
        -Command @("conda", "run", "--no-capture-output", "-n", $CondaEnv, "python", "manage.py", "migrate")

    Invoke-Step `
        -Name "backend tests" `
        -WorkingDirectory $BackendDir `
        -Command @("conda", "run", "--no-capture-output", "-n", $CondaEnv, "pytest", "core/tests", "-m", $MarkerExpr, "-q")
}

function Invoke-AiServiceSuite {
    $AiServiceDir = Join-Path $RepoRoot "AIDetector/code/ai-service/ai-service-code"

    $MarkerExpr = "not gpu and not e2e and not slow"
    if ($IncludeGPU) {
        $MarkerExpr = "not e2e and not slow"
    }

    Invoke-Step `
        -Name "ai-service tests" `
        -WorkingDirectory $AiServiceDir `
        -Command @("conda", "run", "--no-capture-output", "-n", $CondaEnv, "pytest", "tests", "-m", $MarkerExpr, "-q")
}

function Invoke-TrainingSuite {
    $TrainingDir = Join-Path $RepoRoot "AIDetector/code/ai-training/ai-training-code"

    $MarkerExpr = "not gpu and not e2e and not slow"
    if ($IncludeGPU) {
        $MarkerExpr = "not e2e and not slow"
    }

    Invoke-Step `
        -Name "ai-training tests" `
        -WorkingDirectory $TrainingDir `
        -Command @("conda", "run", "--no-capture-output", "-n", $CondaEnv, "pytest", "tests", "-m", $MarkerExpr, "-q")
}

function Invoke-FrontendSuites {
    $UserDir = Join-Path $RepoRoot "AIDetector/code/frontend/frontend-user"
    $AdminDir = Join-Path $RepoRoot "AIDetector/code/frontend/frontend-admin"

    if (-not (Test-CommandExists "npx")) {
        throw "npx is required for frontend tests"
    }

    Invoke-Step `
        -Name "frontend-user vitest" `
        -WorkingDirectory $UserDir `
        -Command @("npx", "vitest", "run")

    Invoke-Step `
        -Name "frontend-admin vitest" `
        -WorkingDirectory $AdminDir `
        -Command @("npx", "vitest", "run")

    if ($IncludeE2E) {
        Invoke-Step `
            -Name "frontend-user playwright" `
            -WorkingDirectory $UserDir `
            -Command @("npx", "playwright", "test")

        Invoke-Step `
            -Name "frontend-admin playwright" `
            -WorkingDirectory $AdminDir `
            -Command @("npx", "playwright", "test")
    }
}

$RunPython = -not $SkipPython -and $Suite -in @("default", "backend", "python", "all")
$RunFrontend = -not $SkipFrontend -and $Suite -in @("default", "frontend", "all")

if ($RunPython) {
    Invoke-BackendSuite
    if ($Suite -ne "backend") {
        Invoke-AiServiceSuite
        Invoke-TrainingSuite
    }
}

if ($RunFrontend) {
    Invoke-FrontendSuites
}

Write-Host ""
Write-Host "All selected test suites passed." -ForegroundColor Green
