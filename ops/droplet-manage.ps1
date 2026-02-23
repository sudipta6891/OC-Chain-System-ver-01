param(
    [ValidateSet("deploy", "start", "stop", "status", "logs", "mode", "check", "syncenv")]
    [string]$Action = "status",

    [ValidateSet("test", "prod")]
    [string]$Mode = "prod",

    [string]$DropletHost = "143.110.241.235",
    [string]$User = "root",
    [string]$RepoPath = "/opt/oc-chain/option_chain_system",
    [string]$ServiceName = "oc-chain",
    [string]$LocalEnvPath = "option_chain_system/.env"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-Remote([string]$Cmd) {
    $clean = $Cmd -replace "`r",""
    $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($clean))
    ssh "$User@$DropletHost" "python3 - <<'PY'
import base64
import subprocess

cmd = base64.b64decode('$b64').decode('utf-8')
subprocess.run(['bash', '-lc', cmd], check=True)
PY"
}

function Upload-Env() {
    if (-not (Test-Path $LocalEnvPath)) {
        throw "Local env file not found: $LocalEnvPath"
    }
    scp $LocalEnvPath "$User@$DropletHost`:$RepoPath/.env"
    Write-Host "Uploaded .env to ${DropletHost}:$RepoPath/.env"
}

function Validate-LocalEnv() {
    if (-not (Test-Path $LocalEnvPath)) {
        throw "Local env file not found: $LocalEnvPath"
    }
    $content = Get-Content $LocalEnvPath
    $map = @{}
    foreach ($line in $content) {
        $ln = $line.Trim()
        if (-not $ln -or $ln.StartsWith("#")) { continue }
        if ($ln.Contains("=")) {
            $parts = $ln.Split("=",2)
            $map[$parts[0].Trim()] = $parts[1].Trim()
        }
    }
    $required = @("FYERS_CLIENT_ID","FYERS_SECRET_KEY","FYERS_REDIRECT_URI","FYERS_ACCESS_TOKEN")
    $missing = @()
    foreach ($k in $required) {
        if (-not $map.ContainsKey($k) -or [string]::IsNullOrWhiteSpace($map[$k])) {
            $missing += $k
        }
    }
    if ($missing.Count -gt 0) {
        throw "Missing required keys in ${LocalEnvPath}: $($missing -join ', ')"
    }
}

function Set-Mode([string]$RuntimeMode) {
    $testValue = if ($RuntimeMode -eq "test") { "True" } else { "False" }
    $allEnhValue = if ($RuntimeMode -eq "prod") { "True" } else { "False" }

    $py = @"
from pathlib import Path
p = Path("$RepoPath/.env")
if not p.exists():
    raise SystemExit("Missing .env on server: " + str(p))
text = p.read_text(encoding="utf-8", errors="ignore")
kv = {}
for ln in text.splitlines():
    if "=" in ln and not ln.lstrip().startswith("#"):
        k, v = ln.split("=", 1)
        kv[k.strip()] = v.strip()
kv["TEST_MODE"] = "$testValue"
kv["ENABLE_ALL_ENHANCEMENTS"] = "$allEnhValue"
if "$RuntimeMode" == "test":
    kv["ENABLE_GUARDRAILS"] = "True"
    kv["ENABLE_OUTCOME_TRACKING"] = "False"
    kv["ENABLE_TIMING_V2"] = "False"
    kv["ENABLE_REGIME_V2"] = "False"
    kv["ENABLE_DYNAMIC_OTM"] = "False"
    kv["ENABLE_CALIBRATION"] = "False"
order = [
 "FYERS_CLIENT_ID","FYERS_SECRET_KEY","FYERS_REDIRECT_URI","FYERS_ACCESS_TOKEN",
 "TIMEZONE","TEST_MODE","DATA_RETENTION_DAYS","OPTION_CHAIN_STRIKE_COUNT",
 "ENABLE_ALL_ENHANCEMENTS","ENABLE_GUARDRAILS","ENABLE_REGIME_V2","ENABLE_TIMING_V2",
 "ENABLE_DYNAMIC_OTM","ENABLE_OUTCOME_TRACKING","ENABLE_CALIBRATION","CALIBRATION_MIN_SAMPLES",
 "DB_NAME","DB_USER","DB_PASSWORD","DB_HOST","DB_PORT",
 "EMAIL_SENDER","EMAIL_APP_PASSWORD","EMAIL_RECIPIENTS"
]
out = []
seen = set()
for k in order:
    if k in kv:
        out.append(f"{k}={kv[k]}")
        seen.add(k)
for k,v in kv.items():
    if k not in seen:
        out.append(f"{k}={v}")
p.write_text("\n".join(out) + "\n", encoding="utf-8")
print("MODE_SET", "$RuntimeMode")
"@
    $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($py))
    Invoke-Remote "python3 - <<'PY'
import base64
exec(base64.b64decode('$b64').decode('utf-8'))
PY"
}

function Ensure-ServerDbEnv() {
    $py = @"
from pathlib import Path
p = Path("$RepoPath/.env")
if not p.exists():
    raise SystemExit("Missing .env on server: " + str(p))
text = p.read_text(encoding="utf-8", errors="ignore")
kv = {}
for ln in text.splitlines():
    if "=" in ln and not ln.lstrip().startswith("#"):
        k, v = ln.split("=", 1)
        kv[k.strip()] = v.strip()
kv["DB_NAME"] = "oc_chain_db"
kv["DB_USER"] = "oc_chain_user"
kv["DB_PASSWORD"] = "OcChain@2026#Db"
kv["DB_HOST"] = "localhost"
kv["DB_PORT"] = "5432"
order = [
 "FYERS_CLIENT_ID","FYERS_SECRET_KEY","FYERS_REDIRECT_URI","FYERS_ACCESS_TOKEN",
 "TIMEZONE","TEST_MODE","DATA_RETENTION_DAYS","OPTION_CHAIN_STRIKE_COUNT",
 "ENABLE_ALL_ENHANCEMENTS","ENABLE_GUARDRAILS","ENABLE_REGIME_V2","ENABLE_TIMING_V2",
 "ENABLE_DYNAMIC_OTM","ENABLE_OUTCOME_TRACKING","ENABLE_CALIBRATION","CALIBRATION_MIN_SAMPLES",
 "DB_NAME","DB_USER","DB_PASSWORD","DB_HOST","DB_PORT",
 "EMAIL_SENDER","EMAIL_APP_PASSWORD","EMAIL_RECIPIENTS"
]
out = []
seen = set()
for k in order:
    if k in kv:
        out.append(f"{k}={kv[k]}")
        seen.add(k)
for k,v in kv.items():
    if k not in seen:
        out.append(f"{k}={v}")
p.write_text("\n".join(out) + "\n", encoding="utf-8")
print("DB_ENV_SET")
"@
    $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($py))
    Invoke-Remote "python3 - <<'PY'
import base64
exec(base64.b64decode('$b64').decode('utf-8'))
PY"
}

switch ($Action) {
    "syncenv" {
        Validate-LocalEnv
        Upload-Env
    }
    "mode" {
        Set-Mode $Mode
        Invoke-Remote "systemctl restart $ServiceName"
        Invoke-Remote "systemctl --no-pager status $ServiceName | sed -n '1,20p'"
    }
    "start" {
        Invoke-Remote "systemctl start $ServiceName"
        Invoke-Remote "systemctl --no-pager status $ServiceName | sed -n '1,20p'"
    }
    "stop" {
        Invoke-Remote "systemctl stop $ServiceName"
        Invoke-Remote "systemctl --no-pager status $ServiceName | sed -n '1,20p'"
    }
    "status" {
        Invoke-Remote "systemctl --no-pager status $ServiceName | sed -n '1,30p'"
    }
    "logs" {
        Invoke-Remote "journalctl -u $ServiceName -n 120 --no-pager"
    }
    "check" {
        Invoke-Remote "cd $RepoPath && . .venv/bin/activate && PYTHONPATH=$RepoPath python ./check_runtime.py --skip-db"
    }
    "deploy" {
        Validate-LocalEnv
        Upload-Env
        Invoke-Remote "cd /opt/oc-chain && git fetch origin && git checkout main && git pull --ff-only origin main"
        Invoke-Remote "cd $RepoPath && python3 -m venv .venv && . .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"
        Ensure-ServerDbEnv
        Invoke-Remote "cd $RepoPath && . .venv/bin/activate && PYTHONPATH=$RepoPath python database/apply_schema.py"
        Set-Mode $Mode
        Invoke-Remote "systemctl daemon-reload && systemctl restart $ServiceName"
        Invoke-Remote "systemctl --no-pager status $ServiceName | sed -n '1,30p'"
    }
}
