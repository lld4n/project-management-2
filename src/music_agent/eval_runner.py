from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .agent_runtime import MusicAgentRuntime
from .config import ROOT_DIR


EVAL_CASES_PATH = ROOT_DIR / "evals" / "agent_eval_cases.json"
EVAL_RESULTS_PATH = ROOT_DIR / "evals" / "agent_eval_results.json"


def run_agent_evals(cases_path: Path = EVAL_CASES_PATH) -> Dict[str, Any]:
    runtime = MusicAgentRuntime()
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    results: List[Dict[str, Any]] = []

    for case in cases:
        try:
            result = runtime.run(case["query"])
            task_names = [task["tool_name"] for task in result.get("tasks", [])]
            answer = result.get("answer", "")
            passed_task = case["expected_task"] in task_names
            passed_answer = case["expected_substring"].lower() in answer.lower()
            row = {
                "id": case["id"],
                "query": case["query"],
                "expected_task": case["expected_task"],
                "task_names": task_names,
                "expected_substring": case["expected_substring"],
                "answer": answer,
                "latency_ms": result.get("latency_ms"),
                "passed_task": passed_task,
                "passed_answer": passed_answer,
                "passed": passed_task and passed_answer,
            }
        except Exception as exc:
            row = {
                "id": case["id"],
                "query": case["query"],
                "expected_task": case["expected_task"],
                "task_names": [],
                "expected_substring": case["expected_substring"],
                "answer": "",
                "latency_ms": None,
                "passed_task": False,
                "passed_answer": False,
                "passed": False,
                "error": repr(exc),
            }
        results.append(row)
        _write_results(results)

    passed = sum(1 for row in results if row["passed"])
    payload = {
        "status": "ok",
        "cases": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass_rate": round((passed / len(results)) * 100, 2) if results else 0.0,
        "results": results,
    }
    EVAL_RESULTS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def _write_results(results: List[Dict[str, Any]]) -> None:
    passed = sum(1 for row in results if row.get("passed"))
    payload = {
        "status": "running",
        "cases": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass_rate": round((passed / len(results)) * 100, 2) if results else 0.0,
        "results": results,
    }
    EVAL_RESULTS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
