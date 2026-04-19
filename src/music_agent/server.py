from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List

from .agent_runtime import MusicAgentRuntime
from .config import get_server_host, get_server_port
from .semantic_memory import SemanticMemoryBuilder
from .tools import MusicHistoryTools


class MusicAgentHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int]) -> None:
        super().__init__(server_address, MusicAgentRequestHandler)
        self.runtime = MusicAgentRuntime()
        self.tools = MusicHistoryTools()
        self.model_id = "music-agent"


class MusicAgentRequestHandler(BaseHTTPRequestHandler):
    server: MusicAgentHTTPServer

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send_json(HTTPStatus.OK, {"status": "ok"})
            return

        if self.path == "/overview":
            self._send_json(HTTPStatus.OK, self.server.tools.dataset_overview())
            return

        if self.path == "/v1/models":
            self._send_json(
                HTTPStatus.OK,
                {
                    "object": "list",
                    "data": [
                        {
                            "id": self.server.model_id,
                            "object": "model",
                            "created": 0,
                            "owned_by": "music-agent",
                        }
                    ],
                },
            )
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"status": "error", "message": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/answer":
            payload = self._read_json_body()
            query = payload.get("query")
            if not isinstance(query, str) or not query.strip():
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"status": "error", "message": "Field 'query' must be a non-empty string."},
                )
                return
            response = self.server.runtime.run(query.strip())
            self._send_json(HTTPStatus.OK, response)
            return

        if self.path == "/v1/chat/completions":
            payload = self._read_json_body()
            query = self._extract_query_from_openai_payload(payload)
            if not query:
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": {"message": "No usable user message found.", "type": "invalid_request_error"}},
                )
                return

            response = self.server.runtime.run(query)
            self._send_json(HTTPStatus.OK, self._to_openai_chat_completion(payload, response))
            return

        if self.path == "/rebuild-memory":
            builder = SemanticMemoryBuilder()
            doc_count = builder.build()
            self.server.runtime = MusicAgentRuntime()
            self._send_json(
                HTTPStatus.OK,
                {"status": "ok", "semantic_documents": doc_count, "message": "Semantic memory rebuilt."},
            )
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"status": "error", "message": "Not found"})

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _read_json_body(self) -> Dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            return {}
        raw = self.rfile.read(content_length)
        if not raw:
            return {}
        try:
            payload = json.loads(raw.decode("utf-8"))
            return payload if isinstance(payload, dict) else {}
        except json.JSONDecodeError:
            return {}

    def _send_json(self, status: HTTPStatus, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _extract_query_from_openai_payload(self, payload: Dict[str, Any]) -> str:
        messages = payload.get("messages", [])
        if not isinstance(messages, list):
            return ""

        for message in reversed(messages):
            if not isinstance(message, dict):
                continue
            if message.get("role") != "user":
                continue
            content = message.get("content")
            if isinstance(content, str):
                return content.strip()
            if isinstance(content, list):
                text_parts: List[str] = []
                for item in content:
                    if not isinstance(item, dict):
                        continue
                    if item.get("type") == "text" and isinstance(item.get("text"), str):
                        text_parts.append(item["text"].strip())
                if text_parts:
                    return "\n".join(part for part in text_parts if part).strip()

        return ""

    def _to_openai_chat_completion(self, request_payload: Dict[str, Any], agent_payload: Dict[str, Any]) -> Dict[str, Any]:
        content = agent_payload.get("answer", "")
        model = request_payload.get("model") or self.server.model_id
        return {
            "id": "chatcmpl-music-agent",
            "object": "chat.completion",
            "created": 0,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
            "music_agent_meta": {
                "planner_summary": agent_payload.get("planner_summary"),
                "tasks": agent_payload.get("tasks", []),
            },
        }


def serve() -> None:
    host = get_server_host()
    port = get_server_port()
    httpd = MusicAgentHTTPServer((host, port))
    print(json.dumps({"status": "ok", "host": host, "port": port}, ensure_ascii=False))
    httpd.serve_forever()
