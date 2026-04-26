# OBSERVABILITY DESIGN

## Цель

Настроить наблюдаемость для мультиагентной системы так, чтобы можно было:

- понимать, что делает система по шагам;
- видеть, где именно она ошибается;
- отслеживать latency, failures и routing quality;
- анализировать качество agent workflow;
- готовить материал для защиты и отчёта.

---

## 1. Что именно нужно наблюдать

Для agentic system недостаточно обычных application logs.

Нужно видеть:

1. `LLM invocations`
2. `agent routing`
3. `tool calls`
4. `verification decisions`
5. `performance metrics`
6. `system health`

---

## 2. Целевой стек

Этот раздел описывает целевой production-ready стек. В текущем MVP фактически реализован облегчённый вариант, описанный в `OBSERVABILITY_LITE.md`.

### Основной целевой выбор

- `OpenTelemetry`
- `Langfuse`
- `Prometheus`
- `Grafana`
- `Loki`
- `Alertmanager`

---

## 3. Почему именно этот стек

## 3.1 OpenTelemetry

### Зачем

- единый стандарт для traces / metrics / logs integration;
- снижает vendor lock-in;
- хорошо ложится на observability architecture в целом.

### Роль в проекте

- instrumentation layer;
- трассировка agent workflow;
- основа для дальнейшего экспорта.

---

## 3.2 Langfuse

### Зачем

- LLM-specific tracing;
- prompts, generations, model runs;
- сравнение prompt versions;
- удобный слой именно для agent / LLM use cases.

### Роль в проекте

- наблюдение за agent runs;
- фиксация prompt / response / intermediate steps;
- анализ ошибок reasoning chain и verifier loop.

---

## 3.3 Prometheus + Grafana

### Зачем

- стандартный metrics stack;
- удобно строить dashboards;
- понятно и defendable на защите.

### Роль в проекте

- latency;
- request counts;
- error rates;
- tool call counts;
- verifier rejection rates;
- resource usage.

---

## 3.4 Loki

### Зачем

- structured logs;
- удобно для локального Grafana-based стека;
- хорошо работает вместе с observability dashboard.

### Роль в проекте

- логи orchestration;
- логи tool calls;
- логи validation / failure paths;
- технический дебаг.

---

## 3.5 Alertmanager

### Зачем

- даже локальной системе нужны понятные alert rules;
- это полезно не только operationally, но и как часть engineering maturity.

### Роль в проекте

- алерты на деградацию latency;
- spikes по failure rate;
- рост verifier rejection rate;
- repeated tool failures.

---

## 4. Что трейсить

## 4.1 Agent run trace

Каждый пользовательский запрос должен иметь:

- `run_id`
- `user_query`
- `selected_route`
- `start_time`
- `end_time`
- `final_status`

---

## 4.2 LLM call trace

Для каждого LLM вызова:

- agent role;
- model id;
- prompt version;
- latency;
- input length;
- output length;
- refusal / non-refusal;
- parsing success / failure.

---

## 4.3 Tool call trace

Для каждого tool call:

- tool name;
- parameters;
- success / failure;
- latency;
- result size;
- downstream agent that used it.

---

## 4.4 Verification trace

Для verifier:

- number of claims;
- approved count;
- rejected count;
- rejection reasons;
- need for re-query / re-computation.

---

## 5. Какие метрики собирать

## 5.1 Model-level

- model invocation count
- average latency
- p95 latency
- output parse failure rate
- refusal rate
- JSON validity rate

## 5.2 Agent-level

- route distribution
- average steps per run
- verifier rejection rate
- reroute rate
- report success rate

## 5.3 Tool-level

- tool invocation count
- tool failure rate
- tool timeout rate
- average tool latency

## 5.4 System-level

- CPU
- memory
- container health
- local service uptime

---

## 6. Какие логи писать

### Обязательные structured logs

- `route_selected`
- `tool_called`
- `tool_failed`
- `claim_generated`
- `claim_rejected`
- `claim_softened`
- `final_response_sent`
- `run_failed`

### Принцип

- логи должны быть machine-readable;
- не должно быть бессмысленного log spam;
- критически важные decision points должны быть видны явно.

---

## 7. Alert rules

Минимально полезные алерты:

- `high_llm_latency`
- `tool_failure_spike`
- `verifier_rejection_spike`
- `json_parse_failure_spike`
- `agent_run_failure`

---

## 8. Почему это хороший выбор

### Плюсы

- закрывает traces, metrics, logs и alerts;
- хорошо подходит под LLM / agent workflow;
- нормально self-hostится локально;
- хорошо защищается как engineering stack.

### Минусы

- для локального проекта стек немаленький;
- требует initial setup effort;
- часть наблюдаемости может выглядеть "overkill" для маленького демо.

---

## 9. Почему не брать что-то сильно проще

### Только stdout logs

- плохо подходит для multi-agent debugging;
- нет нормальных traces;
- нет quality analytics.

### Только Grafana без LLM-specific layer

- не хватает видимости по prompts, generations и agent chain.

### Только Langfuse без Prometheus/Loki

- недостаточно для полноценной system observability.

---

## 10. Итог

Целевой observability stack:

- instrumentation: `OpenTelemetry`
- LLM traces: `Langfuse`
- metrics: `Prometheus`
- dashboards: `Grafana`
- logs: `Loki`
- alerting: `Alertmanager`

Это даёт:

- трассируемость;
- дебаггируемость;
- defendable engineering design.

Фактический MVP сейчас:

- structured run log в `data/memory/run_log.jsonl`;
- `run_id`;
- latency;
- planner summary;
- tool count;
- memory hit count;
- approved/rejected claims;
- final answer.

Alertmanager, Grafana dashboards, Loki и Langfuse не подняты как отдельные сервисы в текущем `docker-compose.yml`; они остаются целевым upgrade path.
