# Вопросы и короткие ответы для защиты

## Что такое LLM?

LLM, или large language model, — большая языковая модель, обученная предсказывать и генерировать текст. Она умеет понимать инструкции, обобщать, классифицировать, писать код и отвечать на вопросы, но сама по себе не имеет доступа к данным и инструментам, если ей их не подключить.

## Что такое агент?

Агент — это система вокруг LLM, которая умеет не только отвечать текстом, но и выполнять workflow: планировать шаги, вызывать tools, использовать память, проверять результат и возвращать grounded answer.

## Чем LLM и агент отличаются?

LLM — это модель генерации текста. Агент — это приложение, где LLM встроена в orchestration: есть роли, tools, memory, routing, verifier, logging и ограничения поведения.

## По какому принципу выбирали LLM? Какие пробовали?

Выбирали лёгкие модели, которые реально запускаются локально на `MacBook Air M1 16GB`.

Пробовали:

- `gemma3:4b`
- `phi4-mini`
- `llama3.2:3b`
- `qwen3:4b`

Критерии: качество factual answers, устойчивость к галлюцинациям, умение отказываться при нехватке данных, JSON/schema stability, tool-use readiness, скорость и fit по памяти.

Выбрана `gemma3:4b`, backup — `phi4-mini`.

## Что значит B в названии LLM?

`B` означает billion, то есть миллиард параметров. Например, `4B` — примерно 4 миллиарда параметров. Обычно больше параметров значит выше потенциальное качество, но больше требования к памяти и скорости.

## Что такое галлюцинации?

Галлюцинации — это когда модель уверенно выдаёт неподтверждённые или ложные факты. Для агента это критично, поэтому в системе есть SQL tools, grounded prompts и `Verifier Agent`.

## Что такое контекстное окно? На что оно влияет?

Контекстное окно — это объём текста, который модель может учитывать за один запрос: prompt, историю, документы, tool results. Чем оно больше, тем больше информации можно передать модели, но это не заменяет память и не гарантирует качество reasoning.

## Как выглядит архитектура агента? Какие есть паттерны?

В проекте архитектура такая:

```text
Planner -> Memory -> Data -> Analysis -> Verifier -> Report
```

Паттерны:

- planner-router;
- tool-using agent;
- verifier / critic;
- report agent;
- fast factual path;
- hybrid memory.

Диаграммы: `ARCHITECTURE_DIAGRAMS.md`.

## Какие фреймворки рассматривали? Какие выбрали?

Рассматривали:

- `LangGraph`
- `LangChain`
- `CrewAI`
- `AutoGen`

В MVP выбран custom orchestration, потому что flow небольшой, маршруты в основном детерминированы, а основная сложность в SQL tools, memory и verifier. `LangGraph` выбран как главный кандидат для следующей версии, если понадобятся явные graph nodes, циклы и checkpointing.

## Какие варианты памяти бывают и какие нужны именно для вашей системы?

Варианты памяти:

- short-term memory — рабочее состояние одного запуска: query, plan, tool results, draft answer;
- long-term episodic memory — история прошлых запусков агента: что спросили, какой route был выбран, какой ответ получился;
- semantic memory — смысловые заметки, summaries, domain knowledge и policies, которые можно подмешивать как контекст;
- factual / structured memory — точные данные в таблицах/БД, источник истины для расчётов и агрегатов;
- vector memory — embeddings + vector DB для поиска похожих документов или заметок по смыслу;
- graph memory — knowledge graph с сущностями и связями, полезен для сложных relation-based запросов.

В проекте нужна hybrid memory:

- `DuckDB` как factual source of truth;
- `semantic_index.jsonl` для semantic context;
- `run_log.jsonl` для episodic memory;
- `AgentState` для short-term state одного запуска.

Naive RAG не выбран как основной подход, потому что задача требует точных агрегатов, дедупликации и сравнений периодов, а это лучше решается SQL/tools.

## Как работаете с долгосрочной памятью?

Долгосрочная память состоит из двух частей:

- factual memory в `DuckDB`;
- episodic memory в `data/memory/run_log.jsonl`.

`DuckDB` хранит нормализованную историю прослушиваний. `run_log.jsonl` хранит историю запусков агента: query, route, tools, latency, approved/rejected claims и answer.

## Как работаете с краткосрочной памятью?

Краткосрочная память — это `AgentState` внутри одного запуска. В нём хранятся user query, planner summary, tasks, memory hits, factual results, analysis, verification и final answer.

## Какие сделали скиллы? Что такое скиллы? Как их правильно создавать?

Скиллы — это `.md` файлы с инструкциями для агента по конкретным типам задач.

В проекте созданы:

- `skills/sql_analytics.md`
- `skills/timeline_insights.md`
- `skills/grounded_reporting.md`
- `skills/self_check.md`

Правильно создавать skills так: один skill — одна зона ответственности, конкретные правила поведения, ограничения, входы/выходы и типичные ошибки.

## Как оцениваете результаты? Какие лучшие практики для оценки?

Используются evals для модели и для agentic system.

Лучшие практики:

- фиксированный eval set;
- одинаковые prompts/settings для моделей;
- отдельные factual, analytical и refusal cases;
- проверка tool routing;
- метрики latency, pass rate, hallucination rate, refusal quality;
- сохранение machine-readable результатов.

В проекте есть `evals/agent_eval_cases.json`, `evals/agent_eval_results.json`, `src/music_agent/eval_runner.py`.

## Как оценивать LLM и agentic system в целом?

LLM оценивается по:

- factual accuracy;
- hallucination resistance;
- abstention quality;
- instruction following;
- JSON/schema stability;
- tool-use readiness;
- speed и memory fit.

Agentic system оценивается по:

- правильности routing;
- правильности tool calls;
- groundedness final answer;
- verifier rejection rate;
- latency;
- pass rate по eval cases;
- качеству отказа при нехватке данных.

Для нашей системы основной eval runner — `music-agent-run-evals`.

## Почему агента нужно запускать в изолированной среде? Какие среды бывают?

Агент может вызывать tools, читать данные и работать с внешними сервисами, поэтому его нужно ограничивать. Иначе ошибка routing или prompt injection может привести к лишнему доступу к файловой системе, сети или секретам.

Варианты изоляции:

- запуск на хосте;
- Docker container;
- Docker Compose;
- отдельный sandbox для tools;
- VM;
- microVM / gVisor-like isolation.

В проекте выбран вариант: `Ollama` на host macOS, agent app и Open WebUI в Docker Compose.

## Как реализовали Observability? Какой стек? Какие метрики мониторите? Куда прилетают алерты?

В MVP реализован observability-lite через structured run log:

- файл: `data/memory/run_log.jsonl`;
- поля: `run_id`, `started_at`, `latency_ms`, `user_query`, `planner_summary`, `tasks`, `memory_hit_count`, `tool_count`, `approved_claims`, `rejected_claims`, `answer`.

Мониторим:

- latency;
- выбранный route;
- tool count;
- memory hit count;
- approved/rejected claims;
- final answer.

Целевой стек описан в `OBSERVABILITY_DESIGN.md`: `OpenTelemetry`, `Langfuse`, `Prometheus`, `Grafana`, `Loki`, `Alertmanager`.

В текущем MVP алерты не настроены как отдельный сервис; это зафиксировано как ограничение и следующий шаг.
