# QUICKSTART

## 1. Установить зависимости

```bash
python3 -m pip install duckdb
```

## 2. Собрать локальную базу

```bash
python3 -c "import sys; sys.path.insert(0, 'src'); from music_agent.ingest import build_database; stats = build_database(); print(stats)"
```

Или через entrypoint после установки проекта:

```bash
music-agent-build-db
```

## 3. Проверить tools

```bash
python3 -c "import sys, json; sys.path.insert(0, 'src'); from music_agent.tools import MusicHistoryTools; t = MusicHistoryTools(); print(json.dumps(t.dataset_overview(), ensure_ascii=False, indent=2))"
```

Проверка deterministic weekly summary:

```bash
python3 -c "import sys, json; sys.path.insert(0, 'src'); from music_agent.tools import MusicHistoryTools; t = MusicHistoryTools(); print(json.dumps(t.weekly_trend_summary(), ensure_ascii=False, indent=2))"
```

## 4. Собрать semantic memory

```bash
python3 -c "import sys; sys.path.insert(0, 'src'); from music_agent.semantic_memory import SemanticMemoryBuilder; print(SemanticMemoryBuilder().build())"
```

Или через entrypoint после установки проекта:

```bash
music-agent-build-memory
```

## 5. Запустить минимальный agent runtime

Убедитесь, что локально запущен `Ollama` и доступна модель `gemma3:4b`.

```bash
python3 -c "import sys, json; sys.path.insert(0, 'src'); from music_agent.agent_runtime import MusicAgentRuntime; rt = MusicAgentRuntime(); print(json.dumps(rt.run('Какие артисты встречаются чаще всего?'), ensure_ascii=False, indent=2))"
```

Пример аналитического маршрута:

```bash
python3 -c "import sys, json; sys.path.insert(0, 'src'); from music_agent.agent_runtime import MusicAgentRuntime; rt = MusicAgentRuntime(); print(json.dumps(rt.run('Какие тренды по неделям можно увидеть в музыкальной истории?'), ensure_ascii=False, indent=2))"
```

Или через entrypoint после установки проекта:

```bash
music-agent-answer "Какие артисты встречаются чаще всего?"
```

Запуск eval suite:

```bash
music-agent-run-evals
```

## Что уже работает

- ingestion `data/raw -> DuckDB`
- canonical analytical layer
- базовые tools:
  - dataset overview
  - top entities
  - daily snapshot
- richer tools:
  - weekly rollup
  - weekly trend summary
  - period compare
- semantic memory:
  - lexical index over `knowledge/*.md`
  - weekly summary documents in `data/memory/semantic_index.jsonl`
- multi-step end-to-end pipeline:
  - routing
  - factual lookup
  - optional insight step
  - verification note
  - grounded final answer через `gemma3:4b`
- hardened weekly route:
  - weekly trend requests now use deterministic insight/report generation instead of extra LLM steps
- fallback path:
  - если primary model не отвечает, runtime может переключиться на `phi4-mini`
- minimal memory:
  - каждый run пишется в `data/memory/run_log.jsonl`
- evals:
  - минимальный eval runner для мультиагентной системы

## Repo artifacts

- `skills/`
  - operational skills for routing, analytics, reporting and self-check
- `knowledge/`
  - semantic markdown files with policies, domain notes and failure modes
- `RUN_LOCAL.md`
  - containerized launch flow for app runtime with host `Ollama`
