#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${APP_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
NGINX_CONF_SOURCE="$APP_DIR/deploy/nginx/vibecoding.conf"
NGINX_CONF_TARGET="/etc/nginx/conf.d/vibecoding.conf"

cd "$APP_DIR"

if [ ! -f ".env" ]; then
  echo "Missing $APP_DIR/.env. Create it from .env.example and set DASHSCOPE_API_KEY first." >&2
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "Docker Compose is not installed." >&2
  exit 1
fi

"${COMPOSE[@]}" up -d --build
install -m 0644 "$NGINX_CONF_SOURCE" "$NGINX_CONF_TARGET"
nginx -t

if command -v systemctl >/dev/null 2>&1; then
  systemctl reload nginx
else
  service nginx reload
fi

"${COMPOSE[@]}" ps
curl -fsS http://127.0.0.1:8010/api/health
echo
echo "Deployment finished. Visit http://47.115.133.42"
