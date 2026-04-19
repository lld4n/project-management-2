# OBSERVABILITY LITE

## Подход

Для MVP не используется тяжёлый стек вроде `Prometheus + Grafana + Loki`.

Вместо этого реализована лёгкая наблюдаемость на уровне agent pipeline.

## Что логируется

Каждый запуск агента пишет structured record в:

- [data/memory/run_log.jsonl](/Users/luffy/Desktop/project-management-2/data/memory/run_log.jsonl)

## Поля run log

- `run_id`
- `started_at`
- `latency_ms`
- `user_query`
- `planner_summary`
- `tasks`
- `memory_hit_count`
- `tool_count`
- `approved_claims`
- `rejected_claims`
- `answer`

## Что это даёт

Позволяет видеть:

- какой план построил `Planner Agent`;
- сколько tools реально было вызвано;
- когда сработал multi-step route;
- сколько verifier пропустил утверждений;
- сколько времени занял ответ;
- какой финальный ответ был отдан пользователю.

## Что уже хорошо видно по логам

- разницу между узкими factual запросами и open-ended analysis;
- латентность отдельных сценариев;
- какие routes становятся слишком тяжёлыми;
- где planner уводит систему не в тот tool.

## Ограничения текущего подхода

- нет real-time dashboards;
- нет алертинга;
- нет отдельного traces UI;
- нет агрегирования по дням/неделям;
- нет автоматической error taxonomy.

## Что можно нарастить дальше

- простой log parser с markdown/json report;
- latency summary по каждому tool;
- planner accuracy summary;
- verifier reject-rate summary;
- позже подключить `Langfuse` или `OpenTelemetry`.
