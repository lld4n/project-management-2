# Work Plan / Current Status

Этот файл отражает фактическое состояние проекта, а не исходный черновой план.

## 1. Цель проекта

Собрать локальную мультиагентную систему на базе open-source LLM для анализа музыкальной истории пользователя из `data/raw`.

## 2. Что реализовано

### LLM runtime

- Рассмотрены: `Ollama`, `llama.cpp`, `MLX-LM`, `LM Studio`, `vLLM`.
- Выбран: `Ollama`.
- Причина: самый простой локальный запуск на `MacBook Air M1 16GB`, удобный HTTP API, быстрый model switching.

### Model selection

- Протестированы: `gemma3:4b`, `phi4-mini`, `llama3.2:3b`, `qwen3:4b`.
- Основная модель: `gemma3:4b`.
- Backup: `phi4-mini`.
- Критерии: hallucination resistance, abstention quality, factual QA, JSON/schema stability, tool-use readiness, speed, memory fit.

### Agent spec

- ТЗ агента оформлено в `AGENT_SPEC.md`.
- Основной домен: анализ музыкальной истории.
- Главный принцип: grounded answers only.

### Multi-agent architecture

- Реализованный flow:

```text
Planner -> Memory -> Data -> Analysis -> Verifier -> Report
```

- Реализация: `src/music_agent/agents.py`, `src/music_agent/agent_runtime.py`.
- Есть fast factual path для простых factual-запросов.
- Диаграммы: `ARCHITECTURE_DIAGRAMS.md`.

### Framework decision

- Рассмотрены: `LangGraph`, `LangChain`, `CrewAI`, `AutoGen`.
- В MVP выбран custom shared-state orchestration.
- Причина: workflow небольшой, маршруты в основном детерминированы, критичная логика находится в SQL tools, memory и verifier.
- `LangGraph` оставлен как upgrade path.

### Data and tools

- Реализован ingestion `data/raw -> DuckDB`.
- База: `data/curated/music_history.duckdb`.
- Tools реализованы в `src/music_agent/tools.py`:
  - `dataset_overview`
  - `top_entities`
  - `daily_snapshot`
  - `entity_peak_dates`
  - `weekly_rollup`
  - `weekly_trend_summary`
  - `period_compare`
  - `period_compare_summary`
  - `stability_vs_spikes`

### Prompts, skills, knowledge

- System prompts: `SYSTEM_PROMPTS.md`.
- Skills:
  - `skills/sql_analytics.md`
  - `skills/timeline_insights.md`
  - `skills/grounded_reporting.md`
  - `skills/self_check.md`
- Knowledge files:
  - `knowledge/domain_guide.md`
  - `knowledge/reporting_policy.md`
  - `knowledge/failure_modes.md`
  - `knowledge/metrics_glossary.md`

### Memory

- Factual memory: `DuckDB`.
- Semantic memory: `data/memory/semantic_index.jsonl`.
- Episodic memory: `data/memory/run_log.jsonl`.
- Short-term memory: `AgentState`.
- Подробности: `MEMORY_ARCHITECTURE.md`.

### Isolation

- Рассмотрены: host runtime, Docker, mixed host/container, VM, microVM-like isolation.
- Выбрано: `Ollama` на host macOS, `music-agent` и `Open WebUI` в Docker Compose.
- Полноценный отдельный tool sandbox не поднят в MVP; это upgrade path.
- Подробности: `ISOLATION_DESIGN.md`.

### Evals

- Model eval docs:
  - `evals/MODEL_EVAL_CASES.md`
  - `evals/MODEL_EVAL_RESULTS.md`
- Agent evals:
  - `evals/agent_eval_cases.json`
  - `evals/agent_eval_results.json`
  - `src/music_agent/eval_runner.py`
- Текущий runner: `music-agent-run-evals`.
- Известное ограничение: текущий pass rate не 100%, часть broad analytical сценариев требует hardening.

### Observability

- MVP: structured run log в `data/memory/run_log.jsonl`.
- Логируются: `run_id`, latency, query, planner summary, tasks, memory hits, tool count, approved/rejected claims, answer.
- Target stack описан в `OBSERVABILITY_DESIGN.md`: OpenTelemetry, Langfuse, Prometheus, Grafana, Loki, Alertmanager.
- Target stack не поднят как отдельные сервисы в MVP.

## 3. Что осталось как upgrade path

- Перенести custom orchestration на `LangGraph`.
- Добавить vector/hybrid semantic retrieval через LanceDB/Chroma.
- Доработать verifier loop `Verifier -> Data`.
- Поднять полноценный observability stack.
- Добавить Prometheus/Grafana dashboards и alerting.
- Усилить Docker isolation: `read_only`, `cap_drop`, `no-new-privileges`, resource limits.
- Довести eval pass rate и добавить refusal/security cases.

## 4. Главная позиция для защиты

Проект реализован как рабочий MVP агента, а не как набор отдельных single-agent скриптов.

Фактический центр системы:

- локальная LLM;
- SQL tools;
- hybrid memory;
- verifier;
- deterministic fast path;
- Dockerized app/API;
- Open WebUI interface;
- eval artifacts;
- structured run log.

