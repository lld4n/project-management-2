# MULTI-AGENT ARCHITECTURE

## Цель

Построить локальную мультиагентную систему для анализа музыкальной истории пользователя на базе локальной LLM (`gemma3:4b`) и factual tools поверх `DuckDB`.

Главная цель архитектуры: не дать LLM отвечать "из головы", а заставить систему строить ответ через route, tools, evidence и verification.

---

## 1. Фактически реализованная архитектура

В коде реализован shared-state pipeline:

```text
Planner -> Memory -> Data -> Analysis -> Verifier -> Report
```

Основные файлы:

- `src/music_agent/agent_runtime.py`
- `src/music_agent/agents.py`
- `src/music_agent/tools.py`
- `src/music_agent/semantic_memory.py`

Это не набор независимых single-agent ботов, а один управляемый workflow с общим состоянием `AgentState`.

---

## 2. Роли агентов

## 2.1 Planner Agent

### Задача

Определяет тип запроса и выбирает нужные tools.

### Что делает

- классифицирует factual / analytical / comparative запрос;
- строит список `AgentTask`;
- выбирает fast factual route для простых вопросов;
- использует heuristic routing, а при необходимости LLM-planning.

### Реализация

- `PlannerAgent` в `src/music_agent/agents.py`.

---

## 2.2 Memory Agent

### Задача

Добавляет semantic context для широких аналитических запросов.

### Что делает

- ищет релевантные knowledge notes и weekly summaries;
- не является source of truth;
- не используется в fast factual path.

### Реализация

- `MemoryAgent` в `src/music_agent/agents.py`;
- `SemanticMemory` в `src/music_agent/semantic_memory.py`.

---

## 2.3 Data Agent

### Задача

Выполняет factual tools поверх `DuckDB`.

### Что делает

- считает top artists / tracks / genres / contexts;
- строит daily snapshot;
- ищет peak dates;
- строит weekly trend summary;
- сравнивает периоды;
- разделяет stable patterns и spikes.

### Реализация

- `DataAgent` в `src/music_agent/agents.py`;
- `MusicHistoryTools` в `src/music_agent/tools.py`.

---

## 2.4 Analysis Agent

### Задача

Строит осторожные claims на базе factual results.

### Что делает

- для части сценариев формирует deterministic claims без LLM;
- для широких запросов может вызвать LLM;
- не должен делать психологические или причинные выводы без evidence.

### Реализация

- `AnalysisAgent` в `src/music_agent/agents.py`.

---

## 2.5 Verifier Agent

### Задача

Отсекает рискованные и неподтверждённые claims.

### Что делает

- собирает limitations из tool results;
- пропускает approved claims;
- отклоняет claims с признаками overclaim, causal leap или psychological inference.

### Реализация

- `VerifierAgent` в `src/music_agent/agents.py`.

---

## 2.6 Report Agent

### Задача

Собирает финальный grounded ответ пользователю.

### Что делает

- для factual routes рендерит deterministic answer;
- для широких отчётов использует approved claims и factual results;
- не должен возвращать rejected claims.

### Реализация

- `ReportAgent` в `src/music_agent/agents.py`.

---

## 3. Граф исполнения

## Fast factual route

```text
User Query
-> Planner
-> Data
-> Verifier
-> Report
```

Используется для:

- `dataset_overview`
- `top_entities`
- `daily_snapshot`
- `entity_peak_dates`

Причина: простые factual-запросы не должны проходить через лишние LLM-шаги.

## Full analytical route

```text
User Query
-> Planner
-> Memory
-> Data
-> Analysis
-> Verifier
-> Report
```

Используется для:

- weekly trends;
- stable vs spikes;
- period comparison;
- broad open-ended analysis.

---

## 4. Почему эта архитектура выбрана

### Почему не single-agent

Single-agent слишком легко смешивает planning, расчёты, интерпретацию и финальный ответ. Для задачи с фактическими данными это повышает риск галлюцинаций.

### Почему не overly complex multi-agent

Сеть из большого числа агентов не нужна для локального MVP на `MacBook Air M1 16GB`: она увеличит latency и усложнит отладку.

### Почему текущий вариант подходит

- роли разделены;
- factual data идёт через tools;
- verifier стоит перед финальным ответом;
- есть короткий deterministic path;
- система легко переносится в graph framework позже.

---

## 5. Фреймворк

Рассмотрены:

- `LangGraph`
- `LangChain`
- `CrewAI`
- `AutoGen`

В текущем MVP выбран custom orchestration без внешнего agent framework.

Причины:

- workflow небольшой;
- маршруты в основном детерминированы;
- критичная логика находится в SQL tools, memory и verifier;
- меньше зависимостей и меньше риск сломать локальный запуск перед защитой.

`LangGraph` остаётся главным кандидатом для следующей версии, потому что текущие роли уже выглядят как graph nodes и могут быть перенесены почти без изменения бизнес-логики.

---

## 6. Что даст LangGraph в следующей версии

- явные nodes и conditional edges;
- verifier loop `Verifier -> Data`;
- checkpointing состояния;
- retry policies;
- более удобный tracing;
- формальная graph-схема для защиты и расширения.

Сейчас эти возможности описаны архитектурно, но в коде не подключены.

---

## 7. Диаграммы

Диаграммы для защиты вынесены в:

- `ARCHITECTURE_DIAGRAMS.md`

Там есть:

- стек по пунктам задания;
- C4 Container Diagram;
- Agent Flow;
- Sequence Diagram;
- Memory Diagram.

