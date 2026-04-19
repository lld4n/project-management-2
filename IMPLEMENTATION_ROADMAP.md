# IMPLEMENTATION ROADMAP

## Цель

Перевести текущие архитектурные решения в реализацию без расползания по фронтам.

Ключевой принцип:

- не пытаться сразу собирать весь стек;
- сначала сделать working core;
- потом добавлять memory, verifier loop и observability.

---

## 1. Когда реализовывать

Ответ коротко:

- **уже сейчас**

Проект уже достаточно спроектирован:

- модель выбрана;
- роли агентов определены;
- prompts определены;
- tools определены;
- memory design определён;
- isolation и observability описаны.

Дальше затягивать проектирование смысла почти нет. Следующий этап — implementation-first.

---

## 2. Правильный порядок реализации

## Этап 1. Data layer

### Что делаем

- нормализуем `data/raw`;
- создаём curated storage;
- поднимаем SQL-first слой.

### Артефакты

- ingestion script
- schema
- локальная база (`DuckDB`)
- несколько проверочных запросов

### Результат

- агент может получать факты не из JSON вручную, а из нормального data layer.

---

## Этап 2. Minimal single-flow agent

### Что делаем

- делаем не сразу полный multi-agent stack;
- сначала собираем минимальный рабочий маршрут:
  - `Orchestrator -> Data Analyst -> Verifier -> Report Agent`

### Артефакты

- app skeleton
- вызов выбранной модели
- 2-3 tools
- один рабочий pipeline

### Результат

- появляется end-to-end демо, которое уже отвечает на данные.

---

## Этап 3. Full multi-agent graph

### Что делаем

- добавляем `Insight Agent`;
- добавляем ветвление маршрутов;
- добавляем возврат из verifier в analyst при недостатке evidence.

### Артефакты

- graph orchestration
- agent state
- handoff logic

### Результат

- система становится именно multi-agent, а не просто цепочкой вызовов.

---

## Этап 4. Memory layer

### Что делаем

- подключаем `DuckDB` как factual memory;
- добавляем semantic notes;
- подключаем episodic logs.

### Артефакты

- factual queries
- semantic notes storage
- run history

### Результат

- система получает память, а не только одноразовый расчёт.

---

## Этап 5. Hardening

### Что делаем

- JSON formatting guardrails;
- prompt hardening;
- post-processing;
- verifier strictness;
- fallback на `phi4-mini`.

### Результат

- система становится заметно стабильнее.

---

## Этап 6. Observability и isolation

### Что делаем

- подключаем ровно тот объём observability, который нужен;
- не тащим весь enterprise-stack сразу;
- оформляем execution boundaries.

### Результат

- система становится инженерно защищаемой.

---

## 3. Что реализовывать прямо сейчас

Прямо сейчас надо делать не Grafana, не Loki и не dashboards.

Прямо сейчас надо делать:

1. ingestion pipeline
2. DuckDB schema
3. 3-5 tools
4. минимальный agent runtime
5. verifier loop

Это critical path.

---

## 4. Приоритеты

### P0

- нормализовать данные
- поднять SQL
- реализовать минимальные tools
- собрать working agent flow

### P1

- full multi-agent routing
- semantic memory
- fallback model logic

### P2

- расширенная observability
- dashboards
- alerts
- более сильная isolation automation

---

## 5. Что считать done

### MVP done

- можно задать вопрос по музыкальной истории;
- агент делает расчёт;
- verifier отсекает недоказуемые claims;
- report agent отдаёт grounded ответ.

### Project done

- есть working multi-agent system;
- есть prompts;
- есть skills;
- есть memory;
- есть evals;
- есть isolation design;
- есть observability design;
- есть отчёт.
