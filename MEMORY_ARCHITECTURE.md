# MEMORY ARCHITECTURE

## Цель

Определить, как система хранит:

- факты о музыкальной истории;
- промежуточные результаты анализа;
- переиспользуемые инсайты;
- состояние текущего agent run.

---

## 1. Почему нельзя ограничиться одной памятью

Для этого проекта одной "общей памяти" недостаточно.

Причины:

- factual data требует точного и воспроизводимого доступа;
- аналитические summaries удобнее хранить отдельно;
- текущее состояние agent run не равно долгосрочной памяти;
- verifier должен проверять claim against evidence, а не against vague memory.

Поэтому выбираем гибридную схему.

---

## 2. Выбранная архитектура памяти

Схема:

1. `Factual memory`
2. `Semantic memory`
3. `Episodic memory`
4. `Short-term run state`

---

## 3. Factual memory

### Назначение

Источник истины для данных.

### Что хранит

- нормализованные таблицы по raw-истории;
- агрегаты;
- weekly rollups;
- day-level snapshots;
- evidence bundles.

### Рекомендуемый storage

- `DuckDB`

### Почему

- очень хорошо подходит под локальную аналитическую задачу;
- сильный SQL-first сценарий;
- удобно считать агрегаты и сравнения;
- локально прост в эксплуатации.

### Плюсы

- воспроизводимость;
- хороший fit для structured analytics;
- verifier-friendly.

### Минусы

- не решает semantic retrieval сам по себе;
- требует явного проектирования схемы.

---

## 4. Semantic memory

### Назначение

Хранить не факты-сырьё, а смысловые summaries и reusable observations.

### Что хранит

- compact summaries по периодам;
- historical insight notes;
- reusable interpretations, которые уже были проверены;
- словари, таксономии, policy notes.

### Фактический storage в MVP

- `data/memory/semantic_index.jsonl`
- lightweight lexical / TF-IDF-like search в `src/music_agent/semantic_memory.py`

### Почему

- нужен для поиска близких аналитических заметок;
- полезен для report generation и повторного использования наблюдений;
- не должен быть источником истины, но полезен как semantic support layer.

### Плюсы

- быстрое retrieval по смыслу;
- удобно для knowledge files и insight reuse.

### Минусы

- риск смешения факта и summary;
- нужен жёсткий policy: semantic memory не заменяет factual evidence.
- текущая реализация проще, чем полноценный vector store;
- нет embeddings и semantic similarity на уровне LanceDB/Chroma.

### Что рассматривалось как upgrade

- `LanceDB`
- `Chroma`
- hybrid search
- hierarchical RAG
- GraphRAG / knowledge graph

---

## 5. Episodic memory

### Назначение

Хранить историю запусков агента.

### Что хранит

- user query;
- выбранный маршрут;
- intermediate claims;
- verifier decisions;
- финальный output;
- ошибки и сбои.

### Зачем нужна

- для observability;
- для анализа качества;
- для дебага;
- для последующего self-improvement.

### Рекомендуемый формат

- JSONL или event storage

---

## 6. Short-term run state

### Назначение

Хранить состояние конкретного текущего исполнения.

### Что хранит

- current user request;
- route decision;
- fetched evidence;
- draft claims;
- verification status;
- final response payload.

### Где живёт в MVP

- в `AgentState` внутри `src/music_agent/agents.py`

### Почему

- это не долгосрочная память;
- это рабочее состояние одного run.

---

## 7. Почему выбран именно hybrid memory

### Почему не naive RAG

- плохо считает агрегаты;
- плохо подходит для строгих factual запросов;
- плохо поддерживает verifier workflow.

### Почему не только SQL

- SQL хорошо хранит факты, но хуже работает как semantic reuse layer;
- summaries, guides и reusable interpretations удобнее искать семантически.

### Почему не GraphRAG / knowledge graph

- для текущего масштаба это избыточно;
- слишком большой operational cost для локального проекта;
- сложно оправдать на защите при таком объёме данных.

---

## 8. Недостатки выбранного подхода

- две или более подсистем памяти вместо одной;
- нужно жёстко различать fact storage и semantic storage;
- требуется дисциплина при записи summaries;
- повышается инженерная сложность.

---

## 9. Что можно улучшить позже

- ввести hierarchical summaries по неделям и месяцам;
- добавить retrieval quality evals;
- ввести automatic evidence linking между semantic notes и factual rows;
- добавить policy, запрещающую verifier-у принимать claim без factual backing id.

---

## 10. Итог

Фактически реализованная память в MVP:

- factual layer: `DuckDB`
- semantic layer: `data/memory/semantic_index.jsonl`
- episodic layer: `data/memory/run_log.jsonl`
- short-term state: `AgentState`

Целевые улучшения:

- заменить lightweight semantic search на LanceDB/Chroma;
- добавить embeddings;
- добавить retrieval evals;
- добавить evidence links между semantic notes и factual rows.
