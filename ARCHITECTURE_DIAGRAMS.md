# Architecture Diagrams

Этот файл нужен для устной защиты: сначала показываем стек и диаграммы, потом по ним объясняем flow агента.

## 1. Стек по пунктам задания

| Пункт | Решение |
|---|---|
| Local LLM runtime | `Ollama` |
| Рассмотренные runtime | `Ollama`, `llama.cpp`, `MLX-LM`, `LM Studio`, `vLLM` |
| Основная LLM | `gemma3:4b` |
| Backup LLM | `phi4-mini` |
| Протестированные LLM | `gemma3:4b`, `phi4-mini`, `llama3.2:3b`, `qwen3:4b` |
| Agent framework | custom orchestration в MVP |
| Рассмотренные фреймворки | `LangGraph`, `LangChain`, `CrewAI`, `AutoGen` |
| Следующий кандидат framework | `LangGraph` |
| Agent API | OpenAI-compatible HTTP API |
| UI | `Open WebUI` |
| Structured storage | `DuckDB` |
| Semantic memory | JSONL semantic index |
| Episodic memory | JSONL run log |
| Isolation | `Ollama` на host, agent app + WebUI в Docker Compose |
| Evals | model eval docs + agent eval runner |
| Observability MVP | structured run log |
| Target observability | OpenTelemetry, Langfuse, Prometheus, Grafana, Loki, Alertmanager |

## 2. C4 Container Diagram

```mermaid
flowchart LR
    User["User / Examiner"]
    WebUI["Open WebUI\nDocker container"]
    AgentAPI["Music Agent API\nDocker container\nOpenAI-compatible API"]
    Runtime["Agent Runtime\nPlanner, Memory, Data,\nAnalysis, Verifier, Report"]
    Tools["SQL Tools\nfactual analytics"]
    DuckDB[("DuckDB\ncurated music history")]
    Semantic[("Semantic Memory\nsemantic_index.jsonl")]
    RunLog[("Episodic Memory\nrun_log.jsonl")]
    Knowledge["Knowledge .md files\npolicies, domain guide,\nfailure modes, metrics"]
    Ollama["Ollama\nhost macOS"]
    LLM["Local open-source LLM\ngemma3:4b / phi4-mini"]

    User --> WebUI
    WebUI --> AgentAPI
    AgentAPI --> Runtime
    Runtime --> Tools
    Tools --> DuckDB
    Runtime --> Semantic
    Runtime --> Knowledge
    Runtime --> RunLog
    Runtime --> Ollama
    Ollama --> LLM
```

Как объяснять: пользователь общается не с голой LLM, а с `Music Agent API`. Агент сам выбирает маршрут, вызывает tools, проверяет claims и только потом формирует ответ.

## 3. Agent Flow

```mermaid
flowchart TD
    Q["User query"]
    Planner["Planner Agent\nclassifies request\nselects route/tools"]
    Fast{"Fast factual?"}
    Memory["Memory Agent\nsemantic context"]
    Data["Data Agent\nDuckDB tools"]
    Analysis["Analysis Agent\ncareful claims"]
    Verifier["Verifier Agent\nrejects unsupported claims"]
    Report["Report Agent\nfinal grounded answer"]
    Log["Run log\nlatency, route, tools,\napproved/rejected claims"]

    Q --> Planner
    Planner --> Fast
    Fast -- yes --> Data
    Fast -- no --> Memory
    Memory --> Data
    Data --> Analysis
    Analysis --> Verifier
    Verifier --> Report
    Report --> Log
    Report --> A["Answer"]
```

Как объяснять: простые factual-вопросы идут коротким путём, чтобы не тратить LLM-вызовы. Аналитические вопросы проходят через memory, analysis и verifier.

## 4. Sequence Diagram

```mermaid
sequenceDiagram
    participant U as User
    participant UI as Open WebUI
    participant API as Music Agent API
    participant P as Planner
    participant M as Memory
    participant D as Data Tools
    participant DB as DuckDB
    participant A as Analysis
    participant V as Verifier
    participant R as Report
    participant O as Ollama LLM
    participant L as Run Log

    U->>UI: Ask question
    UI->>API: POST /v1/chat/completions
    API->>P: plan(query)
    P-->>API: route + tool tasks

    alt simple factual query
        API->>D: run selected tool
        D->>DB: SQL query
        DB-->>D: factual result
    else analytical query
        API->>M: semantic search
        M-->>API: memory hits
        API->>D: run tools
        D->>DB: SQL queries
        DB-->>D: factual results
        API->>A: build cautious claims
        A->>O: LLM call when needed
        O-->>A: draft claims
    end

    API->>V: verify claims against evidence
    V-->>API: approved / rejected claims
    API->>R: render final answer
    R->>O: LLM call only for non-deterministic reports
    O-->>R: final draft
    API->>L: append structured run record
    API-->>UI: OpenAI-compatible response
    UI-->>U: Answer
```

Как объяснять: verifier стоит после analysis и перед report, поэтому финальный ответ не должен включать неподтверждённые утверждения.

## 5. Memory Diagram

```mermaid
flowchart TD
    Raw["data/raw\nJSON snapshots"]
    Ingest["Ingest pipeline"]
    Curated[("DuckDB\ncanonical tables")]
    Tools["SQL tools\nfacts and aggregates"]
    Knowledge["knowledge/*.md"]
    Builder["SemanticMemoryBuilder"]
    Semantic[("semantic_index.jsonl")]
    Runtime["Agent Runtime"]
    State["AgentState\nshort-term run state"]
    RunLog[("run_log.jsonl\nepisodic memory")]

    Raw --> Ingest
    Ingest --> Curated
    Curated --> Tools
    Tools --> Runtime
    Knowledge --> Builder
    Curated --> Builder
    Builder --> Semantic
    Semantic --> Runtime
    Runtime --> State
    Runtime --> RunLog
```

Как объяснять: DuckDB является source of truth. Semantic memory помогает контекстом, но не заменяет факты. Поэтому naive RAG не выбран как основной подход.

## 6. Что показать первым на защите

1. Стек из раздела 1.
2. C4 Container Diagram.
3. Agent Flow.
4. Sequence Diagram.
5. Потом коротко пройтись по пунктам задания.

