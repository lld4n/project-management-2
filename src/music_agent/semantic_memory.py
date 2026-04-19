from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .config import KNOWLEDGE_DIR, SEMANTIC_INDEX_PATH
from .tools import MusicHistoryTools


TOKEN_RE = re.compile(r"[A-Za-zА-Яа-я0-9_!?.-]+")


def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


@dataclass
class SemanticDocument:
    doc_id: str
    source_type: str
    title: str
    content: str
    metadata: Dict[str, Any]

    def to_json(self) -> str:
        return json.dumps(
            {
                "doc_id": self.doc_id,
                "source_type": self.source_type,
                "title": self.title,
                "content": self.content,
                "metadata": self.metadata,
            },
            ensure_ascii=False,
        )

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "SemanticDocument":
        return cls(
            doc_id=payload["doc_id"],
            source_type=payload["source_type"],
            title=payload["title"],
            content=payload["content"],
            metadata=payload.get("metadata", {}),
        )


class SemanticMemoryBuilder:
    def __init__(self, output_path: Path = SEMANTIC_INDEX_PATH) -> None:
        self.output_path = output_path
        self.tools = MusicHistoryTools()

    def build(self) -> int:
        documents = []
        documents.extend(self._knowledge_documents())
        documents.extend(self._weekly_documents())
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with self.output_path.open("w", encoding="utf-8") as f:
            for doc in documents:
                f.write(doc.to_json() + "\n")
        return len(documents)

    def _knowledge_documents(self) -> Iterable[SemanticDocument]:
        docs = []
        for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
            docs.append(
                SemanticDocument(
                    doc_id=f"knowledge:{path.stem}",
                    source_type="knowledge",
                    title=path.stem,
                    content=path.read_text(encoding="utf-8"),
                    metadata={"path": str(path)},
                )
            )
        return docs

    def _weekly_documents(self) -> Iterable[SemanticDocument]:
        docs = []
        payload = self.tools.weekly_rollup()["data"]
        for week_id, week_data in payload.items():
            artist_line = ", ".join(
                f"{row['artist_name']} ({row['count']})" for row in week_data.get("top_artists", [])
            )
            genre_line = ", ".join(
                f"{row['genre']} ({row['count']})" for row in week_data.get("top_genres", [])
            )
            content = (
                f"Week {week_id}. "
                f"Top artists: {artist_line}. "
                f"Top genres: {genre_line}."
            )
            docs.append(
                SemanticDocument(
                    doc_id=f"weekly:{week_id}",
                    source_type="weekly_summary",
                    title=f"Weekly summary {week_id}",
                    content=content,
                    metadata={"week_id": week_id},
                )
            )
        return docs


class SemanticMemory:
    def __init__(self, index_path: Path = SEMANTIC_INDEX_PATH) -> None:
        self.index_path = index_path
        self.documents = self._load_documents()
        self.doc_tokens = {doc.doc_id: Counter(_tokenize(f"{doc.title} {doc.content}")) for doc in self.documents}
        self.doc_freq = self._build_doc_freq()

    def _load_documents(self) -> List[SemanticDocument]:
        if not self.index_path.exists():
            return []
        docs = []
        with self.index_path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    docs.append(SemanticDocument.from_dict(json.loads(line)))
        return docs

    def _build_doc_freq(self) -> Counter:
        freq: Counter = Counter()
        for token_counter in self.doc_tokens.values():
            for token in token_counter.keys():
                freq[token] += 1
        return freq

    def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        if not self.documents:
            return {
                "status": "empty",
                "data": [],
                "summary": "Semantic index is empty.",
                "limitations": ["semantic_index_missing"],
            }

        query_tokens = Counter(_tokenize(query))
        total_docs = max(len(self.documents), 1)
        scored = []

        for doc in self.documents:
            score = 0.0
            token_counter = self.doc_tokens[doc.doc_id]
            for token, q_count in query_tokens.items():
                tf = token_counter.get(token, 0)
                if not tf:
                    continue
                df = self.doc_freq.get(token, 1)
                idf = math.log((1 + total_docs) / df)
                score += q_count * tf * idf
            if score > 0:
                scored.append((score, doc))

        scored.sort(key=lambda item: item[0], reverse=True)
        results = [
            {
                "doc_id": doc.doc_id,
                "source_type": doc.source_type,
                "title": doc.title,
                "score": round(score, 4),
                "content_preview": doc.content[:280],
                "metadata": doc.metadata,
            }
            for score, doc in scored[:limit]
        ]
        return {
            "status": "ok",
            "data": results,
            "summary": f"Returned {len(results)} semantic matches.",
            "limitations": [],
        }
