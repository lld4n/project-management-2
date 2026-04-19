from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict

from .agents import (
    AgentState,
    AnalysisAgent,
    DataAgent,
    MemoryAgent,
    PlannerAgent,
    ReportAgent,
    VerifierAgent,
)
from .config import MEMORY_DIR, RUN_LOG_PATH
from .config import get_fallback_model, get_ollama_base_url, get_primary_model
from .ollama_client import ResilientOllamaClient
from .semantic_memory import SemanticMemory
from .tools import MusicHistoryTools


def _append_run_log(payload: Dict[str, Any]) -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    with RUN_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


class MusicAgentRuntime:
    def __init__(self, model: str | None = None, base_url: str | None = None) -> None:
        self.tools = MusicHistoryTools()
        llm = ResilientOllamaClient(
            primary_model=model or get_primary_model(),
            fallback_model=get_fallback_model(),
            base_url=base_url or get_ollama_base_url(),
        )
        self.memory = SemanticMemory()
        self.planner = PlannerAgent(llm, self.tools)
        self.memory_agent = MemoryAgent(self.memory)
        self.data_agent = DataAgent(self.tools)
        self.analysis_agent = AnalysisAgent(llm)
        self.verifier = VerifierAgent()
        self.reporter = ReportAgent(llm)

    def run(self, user_query: str) -> Dict[str, Any]:
        run_id = str(uuid.uuid4())
        started_at = time.time()
        planner_summary, tasks = self.planner.plan(user_query)
        state = AgentState(user_query=user_query, planner_summary=planner_summary, tasks=tasks)
        fast_factual = self._is_fast_factual(tasks)
        state.memory_hits = [] if fast_factual else self.memory_agent.run(user_query)
        state.factual_results = self.data_agent.run(tasks)
        if fast_factual:
            state.analysis = {
                "status": "ok",
                "model": "deterministic",
                "summary": "Fast factual path.",
                "claims": [],
                "caveats": [],
            }
        else:
            state.analysis = self.analysis_agent.run(state)
        state.verified = self.verifier.verify(state)
        state.final_answer = self.reporter.run(state)
        latency_ms = round((time.time() - started_at) * 1000, 2)
        payload = {
            "run_id": run_id,
            "started_at": started_at,
            "latency_ms": latency_ms,
            "planner_summary": state.planner_summary,
            "tasks": [{"tool_name": task.tool_name, "params": task.params, "rationale": task.rationale} for task in state.tasks],
            "memory_hits": state.memory_hits,
            "factual_results": state.factual_results,
            "analysis": state.analysis,
            "verified": state.verified,
            "answer": state.final_answer,
        }
        _append_run_log(
            {
                "run_id": run_id,
                "started_at": started_at,
                "latency_ms": latency_ms,
                "user_query": user_query,
                "planner_summary": state.planner_summary,
                "tasks": payload["tasks"],
                "memory_hit_count": len(state.memory_hits),
                "tool_count": len(state.factual_results),
                "approved_claims": (state.verified or {}).get("approved_claims", []),
                "rejected_claims": (state.verified or {}).get("rejected_claims", []),
                "answer": state.final_answer,
            }
        )
        return payload

    def _is_fast_factual(self, tasks: list[Any]) -> bool:
        if len(tasks) != 1:
            return False
        return tasks[0].tool_name in {"dataset_overview", "top_entities", "daily_snapshot", "entity_peak_dates"}
