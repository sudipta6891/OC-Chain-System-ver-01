param(
    [ValidateSet("prod", "test")]
    [string]$Mode = "prod",

    [string]$Branch = "main",

    [string]$CommitMessage = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Exec([string]$Cmd) {
    Write-Host ">> $Cmd"
    Invoke-Expression $Cmd
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $Cmd"
    }
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "git command not found."
}

$repoRoot = (git rev-parse --show-toplevel 2>$null)
if (-not $repoRoot) {
    throw "Current folder is not inside a git repository."
}

$currentBranch = (git rev-parse --abbrev-ref HEAD).Trim()
if ($currentBranch -ne $Branch) {
    throw "Current branch is '$currentBranch'. Switch to '$Branch' and retry."
}

$dirty = git status --porcelain
if ($dirty) {
    Exec "git add -A"

    if ([string]::IsNullOrWhiteSpace($CommitMessage)) {
        $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        $CommitMessage = "chore: auto deploy sync $ts"
    }

    Exec "git commit -m `"$CommitMessage`""
} else {
    Write-Host "No local code changes detected. Skipping commit."
}

Exec "git push origin $Branch"
Exec "powershell -ExecutionPolicy Bypass -File .\ops\droplet-manage.ps1 -Action deploy -Mode $Mode"
