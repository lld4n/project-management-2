# EVALS

## Что оцениваем

Оцениваем не только локальную LLM, а всю мультиагентную систему:

- `Planner Agent`
- `Memory Agent`
- `Data Agent`
- `Analysis Agent`
- `Verifier Agent`
- `Report Agent`

## Категории evals

### 1. Factual

Проверяем:

- правильный выбор tool;
- корректность factual answer;
- отсутствие лишних выдуманных утверждений.

Примеры:

- `Какие артисты встречаются чаще всего?`
- `Когда я чаще всего слушал nyan.mp3?`
- `Что происходило 2026-04-13?`

### 2. Analytical

Проверяем:

- может ли система строить осмысленный multi-step plan;
- умеет ли она использовать несколько tool results;
- делает ли она осторожные выводы без лишней галлюцинации.

Примеры:

- `Какие тренды по неделям можно увидеть в музыкальной истории?`
- `Какие артисты были устойчивыми, а какие были всплеском?`
- `Как менялся вкус по времени?`
- `Проанализируй мою историю прослушиваний и скажи, что в ней интересного`

### 3. Refusal / limitation

Проверяем:

- умеет ли система честно говорить, что данных недостаточно;
- не подменяет ли отсутствие данных красивыми догадками.

Примеры:

- вопросы про эмоции, настроение, психологию;
- вопросы про причины поведения;
- вопросы, на которые в датасете нет прямых подтверждений.

## Что уже реализовано

- файл кейсов: [evals/agent_eval_cases.json](/Users/luffy/Desktop/project-management-2/evals/agent_eval_cases.json)
- минимальный runner: [src/music_agent/eval_runner.py](/Users/luffy/Desktop/project-management-2/src/music_agent/eval_runner.py)
- CLI entrypoint:

```bash
music-agent-run-evals
```

или локально:

```bash
python3 -c "import json, sys; sys.path.insert(0, 'src'); from music_agent.eval_runner import run_agent_evals; print(json.dumps(run_agent_evals(), ensure_ascii=False, indent=2))"
```

## Метрики

Для каждого кейса фиксируем:

- `expected_task`
- `actual task_names`
- `expected_substring`
- `final answer`
- `latency_ms`
- `passed_task`
- `passed_answer`
- `passed`

## Текущий статус

Рабочими и подтверждёнными руками считаются:

- top artists
- peak dates по артисту
- weekly trend summary
- stability vs spikes
- open-ended broad analysis

## Что ещё можно улучшить

- добавить cases на отказ;
- добавить cases на track-level analytics;
- ввести отдельную метрику `planner correctness`;
- отдельно считать `verifier rejection rate`;
- сохранять финальный eval report в стабильный machine-readable артефакт.
