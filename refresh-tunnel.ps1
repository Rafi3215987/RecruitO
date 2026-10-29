# Point PUBLIC_BASE_URL at the current Cloudflare quick-tunnel URL and reload the API.
# Run this whenever the tunnel restarts (the free URL changes each time):
#   powershell -ExecutionPolicy Bypass -File .\refresh-tunnel.ps1
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$logs = docker compose logs cloudflared 2>&1 | Out-String
$m = [regex]::Matches($logs, "https://[a-z0-9-]+\.trycloudflare\.com")
if ($m.Count -eq 0) {
  Write-Host "Could not find a trycloudflare.com URL in cloudflared logs."
  Write-Host "Is the tunnel running?  docker compose up -d cloudflared"
  exit 1
}
$url = $m[$m.Count - 1].Value

$envPath = Join-Path $PSScriptRoot ".env"
$lines = Get-Content $envPath
if ($lines -match "^PUBLIC_BASE_URL=") {
  $lines = $lines -replace "^PUBLIC_BASE_URL=.*", "PUBLIC_BASE_URL=$url"
} else {
  $lines += "PUBLIC_BASE_URL=$url"
}
Set-Content -Path $envPath -Value $lines -Encoding utf8

docker compose up -d --force-recreate api | Out-Null
Write-Host "PUBLIC_BASE_URL set to: $url"
Write-Host "Emailed invite / reset / interview links now use this address."
