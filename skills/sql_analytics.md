# Skill: sql_analytics

## Назначение

Используется, когда агенту нужно получить factual answer через расчёт, а не через свободную генерацию.

## Когда применять

- top artists / tracks / genres
- daily snapshot
- weekly rollup
- period comparison
- ranking / counts / frequency queries

## Правила

- не отвечать "с головы", если нужен расчёт;
- сначала получить factual result;
- только потом передавать его дальше;
- явно отмечать неполные записи и ограничения данных.

## Anti-patterns

- оценивать предпочтения пользователя без расчёта;
- подменять ranking предположением;
- делать causal claims.
