# Деплой на kaktus (www.kanstancin.net/alcogames/)

Проект живёт в `~/dev/alcogames` на kaktus. Контейнер слушает `127.0.0.1:7002`, nginx отдаёт его по
`/alcogames/`. Логи уходят в ClickHouse через уже работающий `vector-agent` (метка `logging=true` в compose),
дашборд — https://click.kanstancin.net/d/alcogames/.

## Обновление

```bash
# с локальной машины: залить код (без .git, data, .env, venv и кэшей)
rsync -az --delete --exclude .git --exclude data --exclude .env --exclude .venv \
  --exclude __pycache__ --exclude .pytest_cache \
  ~/Documents/projects/alcogames/ kaktus:~/dev/alcogames/

# на сервере: docker compose up -d --build + проверки (health, главная, число игр, логи)
ssh kaktus '~/dev/alcogames/deploy/deploy-alcogames.sh'
```

`.env` на сервере создаётся один раз: `ADMIN_TOKEN`, `PORT=7002`, при желании `LOG_LEVEL` и значения LLM
по умолчанию (см. `.env.example`). Данные лежат в `~/dev/alcogames/data/`: `games.json` (каталог игр) и
`llm_settings.json` (провайдер и ключи LLM, права `0600`).

## Настройка LLM на проде

Обычный путь — раздел «Настройки LLM» в `https://www.kanstancin.net/alcogames/admin.html`. Через API
(ключ читается из файла, в терминал не попадает):

```bash
python3 -c 'import json,pathlib; print(json.dumps({"provider":"yandex",
  "yandex_api_key": pathlib.Path.home().joinpath(".yandex/cloud/<key-id>").read_text().strip(),
  "yandex_folder_id":"b1g..."}))' \
  | ssh kaktus 'curl -s -X PUT http://127.0.0.1:7002/api/admin/llm-settings \
      -H "X-Admin-Token: $(grep ^ADMIN_TOKEN ~/dev/alcogames/.env | cut -d= -f2-)" \
      -H content-type:application/json --data-binary @-'

ssh kaktus 'curl -s -X POST http://127.0.0.1:7002/api/admin/llm-settings/test \
  -H "X-Admin-Token: $(grep ^ADMIN_TOKEN ~/dev/alcogames/.env | cut -d= -f2-)"'
```

## Проверка

- `curl -I https://www.kanstancin.net/alcogames/` → 200; `/alcogames/api/health` → `{"status":"ok"}`.
- Grafana https://click.kanstancin.net → дашборд `alcogames`: событие `startup` с `provider`, после
  разбора — `llm_parsed` с `provider` и `model`. Все панели: `ssh click '~/logs/probe-dashboard.py alcogames'`.
