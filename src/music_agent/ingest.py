from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .config import CURATED_DIR, DB_PATH, RAW_DATA_DIR
from .schema import DDL_STATEMENTS, RESET_STATEMENTS


try:
    import duckdb
except ModuleNotFoundError as exc:  # pragma: no cover - runtime guidance
    raise RuntimeError(
        "duckdb is not installed. Install project dependencies first."
    ) from exc


@dataclass
class BuildStats:
    snapshot_count: int = 0
    day_count: int = 0
    item_count: int = 0
    occurrence_count: int = 0
    artist_edge_count: int = 0


def _parse_snapshot_timestamp(filename: str) -> Optional[dt.datetime]:
    stem = Path(filename).stem
    if not stem.isdigit():
        return None
    return dt.datetime.utcfromtimestamp(int(stem) / 1000)


def _safe_get_context_fields(item: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], int]:
    context = item.get("context", {})
    context_type = context.get("type")
    data = context.get("data", {})
    full_model = data.get("fullModel", {})

    station_id = None
    title = None
    header = None
    seed_count = 0

    wave_model = full_model.get("wave", {})
    if isinstance(wave_model, dict):
        station_id = wave_model.get("stationId")
        title = wave_model.get("title")
        header = wave_model.get("header")
        seeds = wave_model.get("seeds", []) or []
        seed_count = len(seeds)

    if not title:
        title = full_model.get("title")
    if not header:
        header = full_model.get("header")
    if not station_id:
        station_id = full_model.get("stationId")

    return context_type, title, header, station_id, seed_count


def _extract_album_fields(full_model: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    albums = full_model.get("albums", []) or []
    if not albums:
        return None, None, None
    first_album = albums[0]
    return (
        str(first_album.get("id")) if first_album.get("id") is not None else None,
        first_album.get("title"),
        first_album.get("genre"),
    )


def _extract_track_row(full_model: Dict[str, Any]) -> Dict[str, Any]:
    album_id, album_title, album_genre = _extract_album_fields(full_model)
    artists = full_model.get("artists", []) or []
    return {
        "track_id": full_model.get("id"),
        "real_id": full_model.get("realId"),
        "title": full_model.get("title"),
        "available": full_model.get("available"),
        "error": full_model.get("error"),
        "duration_ms": full_model.get("durationMs"),
        "lyrics_available": full_model.get("lyricsAvailable"),
        "content_warning": full_model.get("contentWarning"),
        "track_source": full_model.get("trackSource"),
        "album_id": album_id,
        "album_title": album_title,
        "album_genre": album_genre,
        "artist_count": len(artists),
    }


def _iter_raw_files(raw_dir: Path) -> Iterable[Path]:
    return sorted(path for path in raw_dir.iterdir() if path.suffix == ".json")


def build_database(
    raw_dir: Path = RAW_DATA_DIR,
    db_path: Path = DB_PATH,
    reset: bool = True,
) -> BuildStats:
    CURATED_DIR.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(str(db_path))
    stats = BuildStats()

    if reset:
        for stmt in RESET_STATEMENTS:
            conn.execute(stmt)

    for stmt in DDL_STATEMENTS:
        conn.execute(stmt)

    snapshot_rows: List[Tuple[Any, ...]] = []
    day_rows: List[Tuple[Any, ...]] = []
    item_rows: List[Tuple[Any, ...]] = []
    occurrence_rows: List[Tuple[Any, ...]] = []
    artist_rows: List[Tuple[Any, ...]] = []

    for snapshot_idx, path in enumerate(_iter_raw_files(raw_dir), start=1):
        payload = json.loads(path.read_text())
        history = payload.get("history", []) or []
        snapshot_id = snapshot_idx
        captured_at = _parse_snapshot_timestamp(path.name)
        snapshot_rows.append((snapshot_id, path.name, captured_at, len(history)))
        stats.snapshot_count += 1

        for day_index, day in enumerate(history):
            day_id = snapshot_id * 10_000 + day_index
            history_date = day.get("date")
            day_rows.append((day_id, snapshot_id, history_date, day_index))
            stats.day_count += 1

            for item_index, item in enumerate(day.get("items", []) or []):
                item_id = day_id * 1_000 + item_index
                context_type, context_title, context_header, context_station_id, seed_count = _safe_get_context_fields(item)
                item_rows.append(
                    (
                        item_id,
                        day_id,
                        item_index,
                        context_type,
                        context_title,
                        context_header,
                        context_station_id,
                        seed_count,
                    )
                )
                stats.item_count += 1

                for track_index, track in enumerate(item.get("tracks", []) or []):
                    occurrence_id = item_id * 10_000 + track_index
                    full_model = track.get("data", {}).get("fullModel", {}) or {}
                    track_row = _extract_track_row(full_model)
                    occurrence_rows.append(
                        (
                            occurrence_id,
                            item_id,
                            track_index,
                            track_row["track_id"],
                            track_row["real_id"],
                            track_row["title"],
                            track_row["available"],
                            track_row["error"],
                            track_row["duration_ms"],
                            track_row["lyrics_available"],
                            track_row["content_warning"],
                            track_row["track_source"],
                            track_row["album_id"],
                            track_row["album_title"],
                            track_row["album_genre"],
                            track_row["artist_count"],
                        )
                    )
                    stats.occurrence_count += 1

                    for artist_index, artist in enumerate(full_model.get("artists", []) or []):
                        artist_rows.append(
                            (
                                occurrence_id,
                                artist_index,
                                str(artist.get("id")) if artist.get("id") is not None else None,
                                artist.get("name"),
                            )
                        )
                        stats.artist_edge_count += 1

    conn.executemany(
        "INSERT INTO snapshots VALUES (?, ?, ?, ?)",
        snapshot_rows,
    )
    conn.executemany(
        "INSERT INTO days VALUES (?, ?, ?, ?)",
        day_rows,
    )
    conn.executemany(
        "INSERT INTO recommendation_items VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        item_rows,
    )
    conn.executemany(
        "INSERT INTO track_occurrences VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        occurrence_rows,
    )
    conn.executemany(
        "INSERT INTO track_artists VALUES (?, ?, ?, ?)",
        artist_rows,
    )

    conn.close()
    return stats
