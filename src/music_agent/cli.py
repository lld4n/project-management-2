from __future__ import annotations

import json
import sys

from .agent_runtime import MusicAgentRuntime
from .ingest import build_database
from .eval_runner import run_agent_evals
from .semantic_memory import SemanticMemoryBuilder
from .server import serve
from .tools import MusicHistoryTools


def build_db_main() -> None:
    stats = build_database()
    print(
        json.dumps(
            {
                "status": "ok",
                "snapshots": stats.snapshot_count,
                "days": stats.day_count,
                "items": stats.item_count,
                "track_occurrences": stats.occurrence_count,
                "artist_edges": stats.artist_edge_count,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def demo_tools_main() -> None:
    tools = MusicHistoryTools()
    payload = {
        "overview": tools.dataset_overview(),
        "top_artists": tools.top_entities("artists", limit=5),
        "daily_snapshot": tools.daily_snapshot("2026-04-13"),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def answer_main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: music-agent-answer '<question>'")
    query = " ".join(sys.argv[1:])
    runtime = MusicAgentRuntime()
    payload = runtime.run(query)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def build_memory_main() -> None:
    builder = SemanticMemoryBuilder()
    doc_count = builder.build()
    print(json.dumps({"status": "ok", "semantic_documents": doc_count}, ensure_ascii=False, indent=2))


def serve_main() -> None:
    serve()


def run_evals_main() -> None:
    payload = run_agent_evals()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
