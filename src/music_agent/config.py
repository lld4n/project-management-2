import os
from pathlib import Path


_SOURCE_ROOT_DIR = Path(__file__).resolve().parents[2]
_DEFAULT_ROOT_DIR = _SOURCE_ROOT_DIR if (_SOURCE_ROOT_DIR / "data").exists() else Path.cwd()

ROOT_DIR = Path(os.getenv("MUSIC_AGENT_ROOT_DIR", str(_DEFAULT_ROOT_DIR))).resolve()
DATA_DIR = Path(os.getenv("MUSIC_AGENT_DATA_DIR", str(ROOT_DIR / "data"))).resolve()
RAW_DATA_DIR = DATA_DIR / "raw"
CURATED_DIR = DATA_DIR / "curated"
DB_PATH = CURATED_DIR / "music_history.duckdb"
MEMORY_DIR = DATA_DIR / "memory"
RUN_LOG_PATH = MEMORY_DIR / "run_log.jsonl"
SEMANTIC_INDEX_PATH = MEMORY_DIR / "semantic_index.jsonl"
KNOWLEDGE_DIR = Path(os.getenv("MUSIC_AGENT_KNOWLEDGE_DIR", str(ROOT_DIR / "knowledge"))).resolve()


def get_ollama_base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")


def get_primary_model() -> str:
    return os.getenv("MUSIC_AGENT_MODEL", "gemma3:4b")


def get_fallback_model() -> str:
    return os.getenv("MUSIC_AGENT_FALLBACK_MODEL", "phi4-mini")


def get_server_host() -> str:
    return os.getenv("MUSIC_AGENT_HOST", "0.0.0.0")


def get_server_port() -> int:
    return int(os.getenv("MUSIC_AGENT_PORT", "8080"))
