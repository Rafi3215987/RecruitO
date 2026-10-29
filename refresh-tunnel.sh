#!/usr/bin/env bash
# Point PUBLIC_BASE_URL at the current Cloudflare quick-tunnel URL and reload the API.
# Run this whenever the tunnel restarts (the free URL changes each time).
set -euo pipefail
cd "$(dirname "$0")"

URL=$(docker compose logs cloudflared 2>&1 | grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" | tail -n 1)
if [ -z "${URL:-}" ]; then
  echo "Could not find a trycloudflare.com URL in cloudflared logs."
  echo "Is the tunnel running?  docker compose up -d cloudflared"
  exit 1
fi

# Replace (or append) PUBLIC_BASE_URL in .env
if grep -q "^PUBLIC_BASE_URL=" .env; then
  sed -i "s#^PUBLIC_BASE_URL=.*#PUBLIC_BASE_URL=${URL}#" .env
else
  printf '\nPUBLIC_BASE_URL=%s\n' "$URL" >> .env
fi

docker compose up -d --force-recreate api >/dev/null
echo "PUBLIC_BASE_URL set to: ${URL}"
echo "Emailed invite / reset / interview links now use this address."
