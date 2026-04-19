# Metrics Glossary

## Raw vs canonical

- `raw_*` метрики считают все snapshot-level записи как есть;
- `canonical_*` метрики считают уникальные дни через latest snapshot per date.

Для аналитики агента использовать нужно именно canonical layer.

## Track occurrence

Одна встречаемость трека внутри recommendation item.

## Context type

Тип recommendation context:

- wave
- album
- playlist
- artist
- search
- other
