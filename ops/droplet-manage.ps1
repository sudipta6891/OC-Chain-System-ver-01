param(
    [ValidateSet("deploy", "start", "stop", "fullstop", "status", "logs", "mode", "check", "syncenv", "webstart", "webstop", "webstatus", "weblogs", "webrestart", "token")]
    [string]$Action = "status",

    [ValidateSet("test", "prod")]
    [string]$Mode = "prod",

    [string]$DropletHost = "143.110.241.235",
    [string]$User = "root",
    [string]$RepoPath = "/opt/oc-chain/option_chain_system",
    [string]$ServiceName = "oc-chain",
    [string]$WebServiceName = "oc-report-web",
    [int]$WebPort = 8080,
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

function Invoke-RemoteInteractive([string]$Cmd) {
    $clean = $Cmd -replace "`r",""
    ssh -t "$User@$DropletHost" "bash -lc '$clean'"
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

function Set-LocalMode([string]$RuntimeMode) {
    if (-not (Test-Path $LocalEnvPath)) {
        throw "Local env file not found: $LocalEnvPath"
    }
    $testValue = if ($RuntimeMode -eq "test") { "True" } else { "False" }
    $allEnhValue = if ($RuntimeMode -eq "prod") { "True" } else { "False" }

    $py = @"
from pathlib import Path
p = Path("$LocalEnvPath")
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
 "TIMEZONE","TEST_MODE","TEST_INTERVAL_MINUTES","TEST_SYMBOLS","DATA_RETENTION_DAYS","OPTION_CHAIN_STRIKE_COUNT",
 "ENABLE_ALL_ENHANCEMENTS","ENABLE_GUARDRAILS","ENABLE_REGIME_V2","ENABLE_TIMING_V2",
 "ENABLE_DYNAMIC_OTM","ENABLE_OUTCOME_TRACKING","ENABLE_CALIBRATION","CALIBRATION_MIN_SAMPLES",
 "DB_NAME","DB_USER","DB_PASSWORD","DB_HOST","DB_PORT"
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
print("LOCAL_MODE_SET", "$RuntimeMode")
"@
    $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($py))
    $tmp = Join-Path $env:TEMP "oc_local_mode_set.py"
    @"
import base64
exec(base64.b64decode("$b64").decode("utf-8"))
"@ | Set-Content -Path $tmp -Encoding UTF8
    try {
        python $tmp
    } finally {
        Remove-Item $tmp -ErrorAction SilentlyContinue
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
 "DB_NAME","DB_USER","DB_PASSWORD","DB_HOST","DB_PORT"
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
 "DB_NAME","DB_USER","DB_PASSWORD","DB_HOST","DB_PORT"
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

function Ensure-WebService() {
    $unit = @"
[Unit]
Description=OC Report Web Viewer
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$RepoPath
Environment=PYTHONPATH=$RepoPath
ExecStart=$RepoPath/.venv/bin/python $RepoPath/serve_reports.py --host 0.0.0.0 --port $WebPort
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"@
    $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($unit))
    Invoke-Remote "python3 - <<'PY'
import base64
from pathlib import Path
content = base64.b64decode('$b64').decode('utf-8')
p = Path('/etc/systemd/system/$WebServiceName.service')
p.write_text(content, encoding='utf-8')
print('WEB_UNIT_WRITTEN', p)
PY"
    Invoke-Remote "systemctl daemon-reload && systemctl enable $WebServiceName"
}

switch ($Action) {
    "syncenv" {
        Validate-LocalEnv
        Upload-Env
    }
    "mode" {
        Set-LocalMode $Mode
        Upload-Env
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
    "fullstop" {
        Invoke-Remote "systemctl stop $ServiceName || true"
        Invoke-Remote "systemctl stop $WebServiceName || true"
        Invoke-Remote "systemctl stop nginx || true"
        Invoke-Remote "systemctl --no-pager status $ServiceName | sed -n '1,16p'"
        Invoke-Remote "systemctl --no-pager status $WebServiceName | sed -n '1,16p'"
        Invoke-Remote "systemctl --no-pager status nginx | sed -n '1,16p'"
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
        Set-LocalMode $Mode
        Validate-LocalEnv
        Upload-Env
        Invoke-Remote "cd /opt/oc-chain && git fetch origin && git checkout main && git pull --ff-only origin main"
        Invoke-Remote "cd $RepoPath && python3 -m venv .venv && . .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"
        Ensure-ServerDbEnv
        Invoke-Remote "cd $RepoPath && . .venv/bin/activate && PYTHONPATH=$RepoPath python database/apply_schema.py"
        Set-Mode $Mode
        Ensure-WebService
        Invoke-Remote "systemctl daemon-reload && systemctl restart $ServiceName && systemctl restart $WebServiceName"
        Invoke-Remote "systemctl --no-pager status $ServiceName | sed -n '1,30p'"
        Invoke-Remote "systemctl --no-pager status $WebServiceName | sed -n '1,30p'"
    }
    "webstart" {
        Ensure-WebService
        Invoke-Remote "systemctl start $WebServiceName"
        Invoke-Remote "systemctl --no-pager status $WebServiceName | sed -n '1,20p'"
    }
    "webstop" {
        Invoke-Remote "systemctl stop $WebServiceName"
        Invoke-Remote "systemctl --no-pager status $WebServiceName | sed -n '1,20p'"
    }
    "webrestart" {
        Ensure-WebService
        Invoke-Remote "systemctl restart $WebServiceName"
        Invoke-Remote "systemctl --no-pager status $WebServiceName | sed -n '1,20p'"
    }
    "webstatus" {
        Invoke-Remote "systemctl --no-pager status $WebServiceName | sed -n '1,30p'"
    }
    "weblogs" {
        Invoke-Remote "journalctl -u $WebServiceName -n 120 --no-pager"
    }
    "token" {
        Write-Host "Running FYERS token generator on droplet..."
        Write-Host "Step 1/2: Open login URL below and complete FYERS login."
        Invoke-Remote "cd $RepoPath && . .venv/bin/activate && PYTHONPATH=$RepoPath python - <<'PY'
from fyers_apiv3 import fyersModel
from config.settings import settings

session = fyersModel.SessionModel(
    client_id=settings.FYERS_CLIENT_ID,
    secret_key=settings.FYERS_SECRET_KEY,
    redirect_uri=settings.FYERS_REDIRECT_URI,
    response_type='code',
    grant_type='authorization_code'
)

print('STEP 1: Generate Login URL\\n')
print(session.generate_authcode())
print('\nOpen this URL in browser and login.')
print('\nAfter login, copy the auth_code from redirected URL.\n')
PY"
        $authCode = Read-Host "Step 2/2: Enter auth_code from redirected URL"
        if ([string]::IsNullOrWhiteSpace($authCode)) {
            throw "auth_code cannot be empty."
        }
        $authCodeB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($authCode))
        Invoke-Remote "cd $RepoPath && . .venv/bin/activate && AUTH_CODE_B64='$authCodeB64' PYTHONPATH=$RepoPath python - <<'PY'
import base64
import os
import re
import urllib.parse
from fyers_apiv3 import fyersModel
from config.settings import settings

raw_input = base64.b64decode(os.environ['AUTH_CODE_B64']).decode('utf-8').strip()

# Accept either raw auth_code JWT or full redirected URL.
auth_code = raw_input
if 'auth_code=' in raw_input:
    parsed = urllib.parse.urlparse(raw_input)
    query = urllib.parse.parse_qs(parsed.query)
    auth_code = (query.get('auth_code') or [''])[0]

# If user pasted extra text, extract first JWT-like token.
if auth_code:
    m = re.search(r'[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', auth_code)
    if m:
        auth_code = m.group(0)

if not auth_code:
    raise SystemExit('Token generation failed: auth_code is empty or invalid.')

session = fyersModel.SessionModel(
    client_id=settings.FYERS_CLIENT_ID,
    secret_key=settings.FYERS_SECRET_KEY,
    redirect_uri=settings.FYERS_REDIRECT_URI,
    response_type='code',
    grant_type='authorization_code'
)
session.set_token(auth_code)
response = session.generate_token()
if response.get('s') != 'ok':
    print('\nFYERS token API response:\n')
    print(response)
    raise SystemExit('\nToken generation failed. Use a fresh auth_code and retry within 1-2 minutes.')
print('\\nAccess Token Generated Successfully:\\n')
print(response['access_token'])
print('\\nCopy this token and paste into .env as FYERS_ACCESS_TOKEN\\n')
PY"
    }
}
