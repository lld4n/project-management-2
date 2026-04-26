# Music Agent

Локальная мультиагентная система для анализа музыкальной истории пользователя из `data/raw`.

## Кратко

- Движок LLM: `Ollama`.
- Основная модель: `gemma3:4b`.
- Backup-модель: `phi4-mini`.
- Данные: `DuckDB`.
- Агент: custom multi-agent runtime.
- UI: `Open WebUI` через OpenAI-compatible API агента.
- Изоляция: `Ollama` на хосте, agent app и WebUI в Docker Compose.

## Решения по требованиям

Диаграммы для защиты: `ARCHITECTURE_DIAGRAMS.md`.

### 1. Локальный движок LLM

Рассмотрены `Ollama`, `llama.cpp`, `MLX-LM`, `LM Studio`, `vLLM`.

Выбран `Ollama`, потому что он проще всего запускается локально на `MacBook Air M1 16GB`, даёт удобный HTTP API, быстро переключает модели и хорошо подходит для MVP агента.

### 2. Лёгкие локальные LLM

Протестированы:

- `gemma3:4b`
- `phi4-mini`
- `llama3.2:3b`
- `qwen3:4b`

Критерии: factual accuracy, hallucination resistance, abstention quality, JSON stability, tool-use readiness, speed, memory fit.

Итог: выбрана `gemma3:4b`, backup — `phi4-mini`. `llama3.2:3b` использовалась как baseline, `qwen3:4b` не выбрана из-за нестабильного output behavior в текущем Ollama setup.

### 3. ИИ-агент

Реализован `Music Agent`: локальный data-aware агент, который отвечает на вопросы по музыкальной истории, вызывает tools, строит аналитику и проверяет claims через verifier.

Основной код: `src/music_agent/`.

### 4. ТЗ агента

ТЗ оформлено в `AGENT_SPEC.md`.

Агент должен отвечать на factual, comparative, trend и report-запросы, не делать психологических выводов и не придумывать факты вне данных.

### 5. Изоляция

Рассмотрены варианты:

- всё на хосте;
- всё в Docker;
- host LLM runtime + containerized agent stack;
- VM;
- microVM / gVisor-like isolation.

Выбран компромисс: `Ollama` на хосте macOS, `music-agent` и `Open WebUI` в Docker Compose. Это лучше подходит для Apple Silicon и сохраняет изоляцию agent app от хоста.

Детали: `ISOLATION_DESIGN.md`, `docker-compose.yml`.

### 6. LLM под капотом

Используется локальная open-source модель через Ollama API.

Основная: `gemma3:4b`.

### 7. Фреймворк

Рассмотрены `LangGraph`, `LangChain`, `CrewAI`, `AutoGen`.

В MVP выбран custom orchestration без внешнего agent framework, потому что workflow небольшой, маршруты в основном детерминированы, а главная логика находится в SQL tools, verifier и grounded reporting.

`LangGraph` оставлен как основной кандидат для следующей версии, где нужны явные graph nodes, cycles, checkpointing и tracing.

### 8. Архитектура

Выбрана компактная мультиагентная архитектура:

```text
Planner -> Memory -> Data -> Analysis -> Verifier -> Report
```

Для простых factual-запросов есть fast path без лишних LLM-шагов.

Архитектура описана в `MULTI_AGENT_ARCHITECTURE.md`.

C4/Sequence diagrams нужно держать рядом с этим документом как защитные артефакты.

### 9. System prompts

System prompts для ролей описаны в `SYSTEM_PROMPTS.md`.

Роли: Orchestrator, Data Analyst, Insight Agent, Verifier, Report Agent.

### 10. Skills

Созданы skill-файлы:

- `skills/sql_analytics.md`
- `skills/timeline_insights.md`
- `skills/grounded_reporting.md`
- `skills/self_check.md`

### 11. Semantic `.md` files

Созданы смысловые knowledge-файлы:

- `knowledge/domain_guide.md`
- `knowledge/reporting_policy.md`
- `knowledge/metrics_glossary.md`
- `knowledge/failure_modes.md`

Они используются как semantic context для агента.

### 12. Память

Реализована hybrid memory:

- factual memory: `DuckDB`;
- semantic memory: `data/memory/semantic_index.jsonl`;
- episodic memory: `data/memory/run_log.jsonl`;
- short-term memory: `AgentState` внутри одного запуска.

Почему не naive RAG: задача требует точных агрегатов, дедупликации, сравнений периодов и verifier-friendly evidence. RAG оставлен как вспомогательный semantic layer, а не источник истины.

Недостатки текущего выбора: semantic search пока lightweight, без vector DB и embeddings. Улучшения: LanceDB/Chroma, hybrid search, hierarchical summaries, GraphRAG, evidence links.

### 13. Evals

Оцениваются LLM и agentic system.

LLM evals: hallucination traps, abstention, grounded factual QA, JSON/schema stability, tool-use readiness.

Agent evals: правильный route, вызов нужного tool, корректность answer, latency, pass rate.

Артефакты:

- `evals/MODEL_EVAL_RESULTS.md`
- `evals/agent_eval_cases.json`
- `evals/agent_eval_results.json`
- `src/music_agent/eval_runner.py`

### 14. Observability

Рассмотрены `LangSmith`, `Langfuse`, `Langtrace`, `OpenTelemetry`, `Prometheus`, `Grafana`, `Loki`, `Alertmanager`.

Целевой стек описан в `OBSERVABILITY_DESIGN.md`.

В MVP реализован observability-lite:

- structured run log;
- latency;
- planner summary;
- tool count;
- memory hit count;
- approved/rejected claims;
- final answer.

Хранение: `data/memory/run_log.jsonl`.

Ограничение: полноценные metrics, traces, dashboards и alerting описаны, но не подняты как отдельный стек.

## Запуск

```bash
python3 -m pip install -e .
music-agent-build-db
music-agent-build-memory
docker compose up -d --build
```

Open WebUI: `http://127.0.0.1:3000`

Agent API: `http://127.0.0.1:8080`

В Open WebUI выбрать модель:

```text
music-agent
```
