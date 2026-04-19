from __future__ import annotations

import json
import urllib.request
from typing import Any, Dict


class OllamaClient:
    def __init__(self, base_url: str = "http://127.0.0.1:11434", model: str = "gemma3:4b") -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    def generate(self, prompt: str, options: Dict[str, Any] | None = None) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": options or {"temperature": 0.2, "num_predict": 300},
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("response", "").strip()


class ResilientOllamaClient:
    def __init__(self, primary_model: str = "gemma3:4b", fallback_model: str = "phi4-mini", base_url: str = "http://127.0.0.1:11434") -> None:
        self.primary = OllamaClient(base_url=base_url, model=primary_model)
        self.fallback = OllamaClient(base_url=base_url, model=fallback_model)
        self.primary_model = primary_model
        self.fallback_model = fallback_model

    def generate(self, prompt: str, options: Dict[str, Any] | None = None) -> Dict[str, str]:
        try:
            response = self.primary.generate(prompt, options=options)
            if response:
                return {"model": self.primary_model, "response": response}
        except Exception:
            pass

        response = self.fallback.generate(prompt, options=options)
        return {"model": self.fallback_model, "response": response}
