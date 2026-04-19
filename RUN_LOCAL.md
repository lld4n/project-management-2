# RUN LOCAL

## Что теперь есть

- HTTP API сервиса агента
- `Dockerfile` для app-контейнера
- `docker-compose.yml` для локального запуска
- запуск с `host Ollama` на macOS
- готовый web UI через `Open WebUI`

## Важная схема

`Ollama` остаётся на хосте macOS, а агент работает в контейнере.

Это соответствует выбранной архитектуре:

- inference на хосте
- app runtime в контейнере
- данные и memory монтируются через volume

## 1. Установить Docker Desktop

На текущей машине в этом окружении `docker` не найден, поэтому сам compose-запуск здесь не был проверен. Файлы запуска подготовлены, но поднимать их нужно уже у вас локально с установленным Docker Desktop.

## 2. Убедиться, что работает Ollama

На хосте должен отвечать:

```bash
ollama list
curl http://127.0.0.1:11434/api/tags
```

Модель по умолчанию:

- primary: `gemma3:4b`
- fallback: `phi4-mini`

## 3. Собрать аналитическую базу и semantic memory

Если хотите сделать это локально без контейнера:

```bash
python3 -m pip install -e .
music-agent-build-db
music-agent-build-memory
```

## 4. Поднять сервис

```bash
docker compose up --build
```

Или в фоне:

```bash
docker compose up -d --build
```

По умолчанию сервис поднимается на:

```text
http://127.0.0.1:8080
```

Готовый чат-интерфейс Open WebUI:

```text
http://127.0.0.1:3000
```

Важно: теперь `Open WebUI` подключён не к прямому `Ollama`, а к `music-agent` через OpenAI-compatible API.
В интерфейсе нужно использовать модель:

```text
music-agent
```

Если в UI всё ещё видны старые модели вроде `qwen3` или `gemma3:4b`, обновите страницу или проверьте connection settings в Open WebUI: backend должен смотреть на `music-agent`, а не на Ollama напрямую.

Для простых factual-вопросов вроде `Какие контексты встречаются чаще всего?`, `Какие артисты встречаются чаще всего?`, `Что происходило 2026-04-13?` и `Когда я чаще всего слушал nyan.mp3?` включён fast factual path: такие запросы отвечают детерминированно и без тяжёлого multi-agent reasoning.

Под капотом это уже не один chat-бот, а мультиагентный pipeline:

- `Planner Agent`
- `Memory Agent`
- `Data Agent`
- `Analysis Agent`
- `Verifier Agent`
- `Report Agent`

Поднять только UI:

```bash
docker compose up -d open-webui
```

Поднять UI и agent API:

```bash
docker compose up -d
```

## 5. Проверить healthcheck

```bash
curl http://127.0.0.1:8080/health
```

Для Open WebUI первый запуск может занимать заметное время: контейнер тянет внутренние зависимости и может некоторое время оставаться в состоянии `health: starting`.

## 6. Получить overview

```bash
curl http://127.0.0.1:8080/overview
```

## 7. Задать вопрос агенту

```bash
curl -X POST http://127.0.0.1:8080/answer \
  -H 'Content-Type: application/json' \
  -d '{"query":"Какие артисты встречаются чаще всего?"}'
```

Пример аналитического вопроса:

```bash
curl -X POST http://127.0.0.1:8080/answer \
  -H 'Content-Type: application/json' \
  -d '{"query":"Какие тренды по неделям можно увидеть в музыкальной истории?"}'
```

## 8. Пересобрать semantic memory

```bash
curl -X POST http://127.0.0.1:8080/rebuild-memory
```

## Переменные окружения

- `OLLAMA_BASE_URL`
- `MUSIC_AGENT_MODEL`
- `MUSIC_AGENT_FALLBACK_MODEL`
- `MUSIC_AGENT_HOST`
- `MUSIC_AGENT_PORT`

Для Docker на macOS базовое значение уже выставлено:

```text
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

## Что не проверено в этом окружении

- полная готовность Open WebUI после первого длинного старта

Что уже проверено:

- Docker Desktop установлен и daemon поднят
- `docker compose build` для agent app проходит
- `docker compose up` поднимает `music-agent`
- `music-agent` отвечает по `/health`, `/overview`, `/answer`
- `open-webui` контейнер поднят и подключён к `music-agent` через OpenAI-compatible API
- fast factual route отвечает быстро на `top_entities`, `daily_snapshot` и `entity_peak_dates`
