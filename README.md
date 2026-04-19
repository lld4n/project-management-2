# Music Agent

Локальная мультиагентная система для анализа музыкальной истории пользователя из `data/raw`.

Система работает на `MacBook Air M1 16GB` с локальной open-source LLM и умеет:

- отвечать на factual-вопросы по истории прослушиваний;
- анализировать недельные паттерны и изменения по периодам;
- отделять устойчивые сигналы от краткосрочных всплесков;
- работать через `Open WebUI`, но не как "голая модель", а как data-aware agent system.

## Что под капотом

- inference runtime: `Ollama`
- основная модель: `gemma3:4b`
- backup-модель: `phi4-mini`
- storage: `DuckDB`
- memory:
  - factual layer в SQL
  - semantic memory в `data/memory/semantic_index.jsonl`
  - run log в `data/memory/run_log.jsonl`
- multi-agent pipeline:
  - `Planner Agent`
  - `Memory Agent`
  - `Data Agent`
  - `Analysis Agent`
  - `Verifier Agent`
  - `Report Agent`

## Быстрый старт

1. Установить зависимости и собрать базу:

```bash
python3 -m pip install -e .
music-agent-build-db
music-agent-build-memory
```

2. Убедиться, что локально запущен `Ollama` и скачана `gemma3:4b`.

3. Поднять сервис и UI:

```bash
docker compose up -d --build
```

4. Открыть:

- `Open WebUI`: `http://127.0.0.1:3000`
- `Agent API`: `http://127.0.0.1:8080`

В `Open WebUI` нужно выбирать модель:

```text
music-agent
```

## Как пользоваться

Прямо из CLI:

```bash
music-agent-answer "Какие артисты встречаются чаще всего?"
music-agent-answer "Какие контексты встречаются чаще всего?"
music-agent-answer "Когда я чаще всего слушал nyan.mp3?"
music-agent-answer "Какие тренды по неделям можно увидеть в музыкальной истории?"
```

Через WebUI можно задавать те же вопросы модели `music-agent`.

## Какие запросы уже хорошо работают

- `Какие артисты встречаются чаще всего?`
- `Какие треки встречаются чаще всего?`
- `Какие жанры встречаются чаще всего?`
- `Какие контексты встречаются чаще всего?`
- `Что происходило 2026-04-13?`
- `Когда я чаще всего слушал nyan.mp3?`
- `Какие тренды по неделям можно увидеть в музыкальной истории?`
- `Какие артисты были устойчивыми, а какие были всплеском?`
- `Как менялся вкус по времени?`

## Что важно про текущую версию

- Для простых factual-вопросов включён `fast factual path`: они не гоняются через лишние LLM-шаги и отвечают быстро.
- Для широких аналитических вопросов используется полный multi-agent pipeline.
- Агент знает только данные музыкальной истории и не должен делать психологические или причинные выводы без подтверждения.

## Основные файлы

- [RUN_LOCAL.md](/Users/luffy/Desktop/project-management-2/RUN_LOCAL.md)
- [WORK_PLAN.md](/Users/luffy/Desktop/project-management-2/WORK_PLAN.md)
- [MODEL_DECISION.md](/Users/luffy/Desktop/project-management-2/MODEL_DECISION.md)
- [MULTI_AGENT_ARCHITECTURE.md](/Users/luffy/Desktop/project-management-2/MULTI_AGENT_ARCHITECTURE.md)
- [AGENT_SPEC.md](/Users/luffy/Desktop/project-management-2/AGENT_SPEC.md)
- [EVALS.md](/Users/luffy/Desktop/project-management-2/EVALS.md)
- [OBSERVABILITY_LITE.md](/Users/luffy/Desktop/project-management-2/OBSERVABILITY_LITE.md)
