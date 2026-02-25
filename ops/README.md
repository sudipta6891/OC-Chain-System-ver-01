# Droplet Ops (VS Code)

Run these from your project root in VS Code terminal.

Script:
- `ops/droplet-manage.ps1`

Default target:
- Host: `143.110.241.235`
- User: `root`
- Service: `oc-chain`

## Common Commands

### Morning deploy in production mode
```powershell
powershell -ExecutionPolicy Bypass -File .\ops\droplet-manage.ps1 -Action deploy -Mode prod
```

### Switch to test mode
```powershell
powershell -ExecutionPolicy Bypass -File .\ops\droplet-manage.ps1 -Action mode -Mode test
```

### Switch back to production mode
```powershell
powershell -ExecutionPolicy Bypass -File .\ops\droplet-manage.ps1 -Action mode -Mode prod
```

### Service controls
```powershell
powershell -ExecutionPolicy Bypass -File .\ops\droplet-manage.ps1 -Action start
powershell -ExecutionPolicy Bypass -File .\ops\droplet-manage.ps1 -Action stop
powershell -ExecutionPolicy Bypass -File .\ops\droplet-manage.ps1 -Action status
powershell -ExecutionPolicy Bypass -File .\ops\droplet-manage.ps1 -Action logs
```

### Report web page service controls
```powershell
powershell -ExecutionPolicy Bypass -File .\ops\droplet-manage.ps1 -Action webstart
powershell -ExecutionPolicy Bypass -File .\ops\droplet-manage.ps1 -Action webstop
powershell -ExecutionPolicy Bypass -File .\ops\droplet-manage.ps1 -Action webstatus
powershell -ExecutionPolicy Bypass -File .\ops\droplet-manage.ps1 -Action weblogs
```

### Upload only local `.env` to server
```powershell
powershell -ExecutionPolicy Bypass -File .\ops\droplet-manage.ps1 -Action syncenv
```

### Quick config check (no DB check)
```powershell
powershell -ExecutionPolicy Bypass -File .\ops\droplet-manage.ps1 -Action check
```

### Generate FYERS token on droplet (interactive)
```powershell
powershell -ExecutionPolicy Bypass -File .\ops\droplet-manage.ps1 -Action token
```
Notes:
- Script prints login URL in terminal.
- Open URL in browser, login, copy `auth_code`.
- Paste `auth_code` into terminal prompt.
- Copy generated access token and update `FYERS_ACCESS_TOKEN` in local `option_chain_system/.env`.
- Run deploy after update.

## Mode Behavior

### `-Mode prod`
- `TEST_MODE=False`
- `ENABLE_ALL_ENHANCEMENTS=True`

### `-Mode test`
- `TEST_MODE=True`
- `ENABLE_ALL_ENHANCEMENTS=False`
- Safety toggles forced:
  - `ENABLE_GUARDRAILS=True`
  - `ENABLE_OUTCOME_TRACKING=False`
  - `ENABLE_TIMING_V2=False`
  - `ENABLE_REGIME_V2=False`
  - `ENABLE_DYNAMIC_OTM=False`
  - `ENABLE_CALIBRATION=False`

## Daily Easiest Flow
1. Power on droplet in DigitalOcean UI.
2. In VS Code terminal, run:
   - `powershell -ExecutionPolicy Bypass -File .\ops\droplet-manage.ps1 -Action deploy -Mode prod`
3. Check health:
   - `powershell -ExecutionPolicy Bypass -File .\ops\droplet-manage.ps1 -Action status`
4. End of day:
   - `powershell -ExecutionPolicy Bypass -File .\ops\droplet-manage.ps1 -Action stop`
   - then power off from DO UI.

## Report Viewer URL
- Default port is `8080`.
- Open: `http://143.110.241.235:8080`
- If unreachable, allow inbound TCP `8080` in DigitalOcean Cloud Firewall.
