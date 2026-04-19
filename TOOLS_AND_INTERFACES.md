# TOOLS AND INTERFACES

## Цель

Зафиксировать минимально необходимый набор инструментов для мультиагентной системы анализа музыкальной истории.

Инструменты нужны, чтобы:

- модель не считала "из головы";
- расчёты были воспроизводимы;
- factual layer был отделён от reasoning layer.

---

## 1. Принцип выбора tools

Мы не даём агенту “произвольный shell” как основной путь работы.

Причины:

- это ухудшает управляемость;
- повышает риск ошибок;
- сложнее защищать такую архитектуру;
- труднее отслеживать, что именно сделал агент.

Поэтому инструменты должны быть узкими, явными и наблюдаемыми.

---

## 2. Минимальный набор tools

## 2.1 `dataset_overview`

### Назначение

Возвращает высокоуровневую сводку по датасету.

### Что должен уметь

- число файлов;
- диапазон дат;
- число дней;
- число recommendation items;
- число track occurrences;
- типы контекстов;
- число неполных / broken records.

### Кто использует

- `Orchestrator`
- `Data Analyst`
- `Verifier`

---

## 2.2 `top_entities`

### Назначение

Возвращает top-N по сущности.

### Поддерживаемые сущности

- artists
- tracks
- genres
- contexts

### Параметры

- `entity_type`
- `limit`
- `date_from`
- `date_to`

### Кто использует

- `Data Analyst`
- `Insight Agent`

---

## 2.3 `period_compare`

### Назначение

Сравнивает два периода между собой.

### Что должен возвращать

- top entities по каждому периоду;
- рост / падение;
- новые сущности;
- исчезнувшие сущности;
- summary по change patterns.

### Кто использует

- `Data Analyst`
- `Insight Agent`

---

## 2.4 `daily_snapshot`

### Назначение

Возвращает срез по конкретной дате.

### Что должен возвращать

- top artists for day;
- top genres for day;
- top tracks for day;
- count of contexts;
- count of recommendations;
- data gaps if present.

### Кто использует

- `Data Analyst`
- `Verifier`

---

## 2.5 `weekly_rollup`

### Назначение

Строит weekly aggregation.

### Что должен возвращать

- top artists by week;
- top genres by week;
- repeated tracks by week;
- stable vs emerging signals.

### Кто использует

- `Data Analyst`
- `Insight Agent`

---

## 2.6 `claim_evidence_lookup`

### Назначение

Даёт verifier-у возможность проверить конкретный claim.

### Пример задач

- подтвердить, что жанр доминировал;
- подтвердить, что артист вырос по частоте;
- подтвердить, что паттерн был устойчивым, а не разовым.

### Кто использует

- `Verifier`

---

## 2.7 `report_formatter`

### Назначение

Преобразует approved claims в структурированный report payload.

### Кто использует

- `Report Agent`

---

## 3. Интерфейс ответа tools

Чтобы модель вела себя устойчиво, tools должны возвращать предсказуемый формат.

### Базовый контракт

Каждый tool должен возвращать:

- `status`
- `data`
- `summary`
- `limitations`

Пример:

```json
{
  "status": "ok",
  "data": {},
  "summary": "Top genre is rusrap.",
  "limitations": []
}
```

---

## 4. Кто какие tools может использовать

### Orchestrator

- `dataset_overview`

### Data Analyst

- `dataset_overview`
- `top_entities`
- `period_compare`
- `daily_snapshot`
- `weekly_rollup`

### Insight Agent

- не должен ходить в произвольные данные
- работает либо по factual bundle, либо по:
  - `top_entities`
  - `period_compare`
  - `weekly_rollup`

### Verifier

- `claim_evidence_lookup`
- `daily_snapshot`
- `dataset_overview`

### Report Agent

- `report_formatter`

---

## 5. Почему это хороший минимум

### Плюсы

- достаточно узкий набор;
- понятно, что и зачем вызывает агент;
- хорошо ложится на observability;
- легко защитить как инженерное решение.

### Минусы

- некоторые сложные запросы могут потребовать composition нескольких tools;
- часть логики агрегации нужно заранее реализовать;
- меньше гибкости, чем у свободного shell-доступа.

---

## 6. Следующий шаг

Теперь нужно зафиксировать memory architecture:

- factual memory;
- semantic memory;
- episodic memory;
- short-term run state.
