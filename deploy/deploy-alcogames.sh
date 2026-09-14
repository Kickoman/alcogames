#!/usr/bin/env bash
# Собирает и поднимает alcogames на сервере. sudo не нужен — пользователь в группе docker.
# Запускать: ~/dev/alcogames/deploy/deploy-alcogames.sh
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")/.."   # ~/dev/alcogames

[ -f .env ] || { echo ".env отсутствует: cp .env.example .env и задайте ADMIN_TOKEN, PORT"; exit 1; }
PORT="$(grep -E '^PORT=' .env | cut -d= -f2)"; PORT="${PORT:-8000}"

echo "── 1. Собираю и поднимаю alcogames ──"
docker compose up -d --build

echo "── 2. Проверка ──"
for i in $(seq 1 30); do
    curl -sf -m 2 -o /dev/null "http://127.0.0.1:$PORT/api/health" && break
    sleep 1
done
docker compose ps
echo
echo "health:"; curl -s -m 5 -o /dev/null -w "  HTTP %{http_code}\n" "http://127.0.0.1:$PORT/api/health" || true
echo "главная:"; curl -s -m 5 -o /dev/null -w "  HTTP %{http_code}\n" "http://127.0.0.1:$PORT/" || true
echo "игры на месте:"; curl -s -m 5 "http://127.0.0.1:$PORT/api/games" | python3 -c "import sys,json;print(f\"  {len(json.load(sys.stdin))} игр\")" || true
echo "данные на хосте:"; ls -la data/ | sed 's/^/  /'
echo
echo "логи (JSON, уходят в ClickHouse через vector-agent):"; docker compose logs --tail 6 alcogames
