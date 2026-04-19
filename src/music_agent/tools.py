from __future__ import annotations

from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Optional

from .config import DB_PATH


try:
    import duckdb
except ModuleNotFoundError as exc:  # pragma: no cover - runtime guidance
    raise RuntimeError(
        "duckdb is not installed. Install project dependencies first."
    ) from exc


class MusicHistoryTools:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path

    def _conn(self):
        return duckdb.connect(str(self.db_path), read_only=True)

    def list_tool_specs(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "dataset_overview",
                "description": "High-level overview of the dataset, date range, counts, and contexts.",
                "params": {},
            },
            {
                "name": "top_entities",
                "description": "Top artists, tracks, genres, or contexts, optionally filtered by date range.",
                "params": {
                    "entity_type": ["artists", "tracks", "genres", "contexts"],
                    "limit": "int",
                    "date_from": "YYYY-MM-DD optional",
                    "date_to": "YYYY-MM-DD optional",
                },
            },
            {
                "name": "daily_snapshot",
                "description": "Top artists, genres, and tracks for one exact date.",
                "params": {"history_date": "YYYY-MM-DD"},
            },
            {
                "name": "entity_peak_dates",
                "description": "Peak dates for one artist or track.",
                "params": {"entity_type": ["artist", "track"], "entity_name": "string", "limit": "int"},
            },
            {
                "name": "weekly_trend_summary",
                "description": "Deterministic weekly leaders, recurring entities, and leadership changes.",
                "params": {},
            },
            {
                "name": "period_compare",
                "description": "Compare top artists and genres between two time windows.",
                "params": {
                    "date_from": "YYYY-MM-DD",
                    "split_date": "YYYY-MM-DD",
                    "date_to": "YYYY-MM-DD",
                },
            },
            {
                "name": "period_compare_summary",
                "description": "Deterministic summary of what persisted, appeared, and disappeared across two periods.",
                "params": {
                    "date_from": "YYYY-MM-DD",
                    "split_date": "YYYY-MM-DD",
                    "date_to": "YYYY-MM-DD",
                },
            },
            {
                "name": "stability_vs_spikes",
                "description": "Find artists that were stable across weeks versus short-lived weekly leaders.",
                "params": {"dimension": ["artist", "genre"]},
            },
        ]

    def run_tool(self, tool_name: str, **params: Any) -> Dict[str, Any]:
        if tool_name == "dataset_overview":
            return self.dataset_overview()
        if tool_name == "top_entities":
            return self.top_entities(**params)
        if tool_name == "daily_snapshot":
            return self.daily_snapshot(**params)
        if tool_name == "entity_peak_dates":
            return self.entity_peak_dates(**params)
        if tool_name == "weekly_rollup":
            return self.weekly_rollup()
        if tool_name == "weekly_trend_summary":
            return self.weekly_trend_summary()
        if tool_name == "period_compare":
            return self.period_compare(**params)
        if tool_name == "period_compare_summary":
            return self.period_compare_summary(**params)
        if tool_name == "stability_vs_spikes":
            return self.stability_vs_spikes(**params)
        raise ValueError(f"Unsupported tool_name: {tool_name}")

    def dataset_overview(self) -> Dict[str, Any]:
        conn = self._conn()
        overview = conn.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM snapshots) AS snapshots,
              (SELECT COUNT(*) FROM days) AS raw_days,
              (SELECT COUNT(*) FROM canonical_days) AS canonical_days,
              (SELECT COUNT(*) FROM recommendation_items) AS raw_items,
              (SELECT COUNT(*) FROM canonical_recommendation_items) AS canonical_items,
              (SELECT COUNT(*) FROM track_occurrences) AS raw_track_occurrences,
              (SELECT COUNT(*) FROM canonical_track_occurrences) AS canonical_track_occurrences,
              (SELECT COUNT(*) FROM canonical_track_occurrences WHERE title IS NULL) AS incomplete_tracks,
              (SELECT MIN(history_date) FROM days) AS date_min,
              (SELECT MAX(history_date) FROM days) AS date_max
            """
        ).fetchone()
        contexts = conn.execute(
            """
            SELECT context_type, COUNT(*) AS cnt
            FROM canonical_recommendation_items
            GROUP BY 1
            ORDER BY cnt DESC
            """
        ).fetchall()
        conn.close()
        return {
            "status": "ok",
            "data": {
                "snapshots": overview[0],
                "raw_days": overview[1],
                "canonical_days": overview[2],
                "raw_items": overview[3],
                "canonical_items": overview[4],
                "raw_track_occurrences": overview[5],
                "canonical_track_occurrences": overview[6],
                "incomplete_tracks": overview[7],
                "date_min": str(overview[8]),
                "date_max": str(overview[9]),
                "contexts": [{"context_type": row[0], "count": row[1]} for row in contexts],
            },
            "summary": "High-level dataset overview.",
            "limitations": [],
        }

    def top_entities(
        self,
        entity_type: str,
        limit: int = 10,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        conn = self._conn()
        where = []
        params: List[Any] = []
        if date_from:
            where.append("d.history_date >= ?")
            params.append(date_from)
        if date_to:
            where.append("d.history_date <= ?")
            params.append(date_to)
        where_sql = f"WHERE {' AND '.join(where)}" if where else ""

        if entity_type == "artists":
            query = f"""
                SELECT ta.artist_name AS entity, COUNT(*) AS cnt
                FROM canonical_track_artists ta
                JOIN canonical_track_occurrences t ON ta.occurrence_id = t.occurrence_id
                JOIN canonical_recommendation_items ri ON t.item_id = ri.item_id
                JOIN canonical_days d ON ri.day_id = d.day_id
                {where_sql} AND ta.artist_name IS NOT NULL
                GROUP BY 1
                ORDER BY cnt DESC
                LIMIT ?
            """ if where else """
                SELECT ta.artist_name AS entity, COUNT(*) AS cnt
                FROM canonical_track_artists ta
                WHERE ta.artist_name IS NOT NULL
                GROUP BY 1
                ORDER BY cnt DESC
                LIMIT ?
            """
        elif entity_type == "tracks":
            query = f"""
                SELECT t.title AS entity, COUNT(*) AS cnt
                FROM canonical_track_occurrences t
                JOIN canonical_recommendation_items ri ON t.item_id = ri.item_id
                JOIN canonical_days d ON ri.day_id = d.day_id
                {where_sql} AND t.title IS NOT NULL
                GROUP BY 1
                ORDER BY cnt DESC
                LIMIT ?
            """ if where else """
                SELECT title AS entity, COUNT(*) AS cnt
                FROM canonical_track_occurrences
                WHERE title IS NOT NULL
                GROUP BY 1
                ORDER BY cnt DESC
                LIMIT ?
            """
        elif entity_type == "genres":
            query = f"""
                SELECT t.album_genre AS entity, COUNT(*) AS cnt
                FROM canonical_track_occurrences t
                JOIN canonical_recommendation_items ri ON t.item_id = ri.item_id
                JOIN canonical_days d ON ri.day_id = d.day_id
                {where_sql} AND t.album_genre IS NOT NULL
                GROUP BY 1
                ORDER BY cnt DESC
                LIMIT ?
            """ if where else """
                SELECT album_genre AS entity, COUNT(*) AS cnt
                FROM canonical_track_occurrences
                WHERE album_genre IS NOT NULL
                GROUP BY 1
                ORDER BY cnt DESC
                LIMIT ?
            """
        elif entity_type == "contexts":
            query = f"""
                SELECT ri.context_type AS entity, COUNT(*) AS cnt
                FROM canonical_recommendation_items ri
                JOIN canonical_days d ON ri.day_id = d.day_id
                {where_sql} AND ri.context_type IS NOT NULL
                GROUP BY 1
                ORDER BY cnt DESC
                LIMIT ?
            """ if where else """
                SELECT context_type AS entity, COUNT(*) AS cnt
                FROM canonical_recommendation_items
                WHERE context_type IS NOT NULL
                GROUP BY 1
                ORDER BY cnt DESC
                LIMIT ?
            """
        else:
            conn.close()
            raise ValueError(f"Unsupported entity_type: {entity_type}")

        rows = conn.execute(query, [*params, limit]).fetchall()
        conn.close()
        return {
            "status": "ok",
            "data": [{"entity": row[0], "count": row[1]} for row in rows],
            "summary": f"Top {entity_type}.",
            "limitations": [],
        }

    def daily_snapshot(self, history_date: str) -> Dict[str, Any]:
        conn = self._conn()
        top_artists = conn.execute(
            """
            SELECT ta.artist_name, COUNT(*) AS cnt
            FROM canonical_track_artists ta
            JOIN canonical_track_occurrences t ON ta.occurrence_id = t.occurrence_id
            JOIN canonical_recommendation_items ri ON t.item_id = ri.item_id
            JOIN canonical_days d ON ri.day_id = d.day_id
            WHERE d.history_date = ? AND ta.artist_name IS NOT NULL
            GROUP BY 1
            ORDER BY cnt DESC
            LIMIT 5
            """,
            [history_date],
        ).fetchall()
        top_genres = conn.execute(
            """
            SELECT album_genre, COUNT(*) AS cnt
            FROM canonical_track_occurrences t
            JOIN canonical_recommendation_items ri ON t.item_id = ri.item_id
            JOIN canonical_days d ON ri.day_id = d.day_id
            WHERE d.history_date = ? AND album_genre IS NOT NULL
            GROUP BY 1
            ORDER BY cnt DESC
            LIMIT 5
            """,
            [history_date],
        ).fetchall()
        top_tracks = conn.execute(
            """
            SELECT title, COUNT(*) AS cnt
            FROM canonical_track_occurrences t
            JOIN canonical_recommendation_items ri ON t.item_id = ri.item_id
            JOIN canonical_days d ON ri.day_id = d.day_id
            WHERE d.history_date = ? AND title IS NOT NULL
            GROUP BY 1
            ORDER BY cnt DESC
            LIMIT 5
            """,
            [history_date],
        ).fetchall()
        conn.close()
        return {
            "status": "ok",
            "data": {
                "history_date": history_date,
                "top_artists": [{"artist_name": row[0], "count": row[1]} for row in top_artists],
                "top_genres": [{"genre": row[0], "count": row[1]} for row in top_genres],
                "top_tracks": [{"title": row[0], "count": row[1]} for row in top_tracks],
            },
            "summary": f"Daily snapshot for {history_date}.",
            "limitations": [],
        }

    def entity_peak_dates(self, entity_type: str, entity_name: str, limit: int = 5) -> Dict[str, Any]:
        conn = self._conn()
        normalized_name = entity_name.strip()

        if entity_type == "artist":
            rows = conn.execute(
                """
                SELECT
                  d.history_date,
                  COUNT(*) AS cnt
                FROM canonical_track_artists ta
                JOIN canonical_track_occurrences t ON ta.occurrence_id = t.occurrence_id
                JOIN canonical_recommendation_items ri ON t.item_id = ri.item_id
                JOIN canonical_days d ON ri.day_id = d.day_id
                WHERE lower(ta.artist_name) = lower(?)
                GROUP BY 1
                ORDER BY cnt DESC, d.history_date ASC
                LIMIT ?
                """,
                [normalized_name, limit],
            ).fetchall()
        elif entity_type == "track":
            rows = conn.execute(
                """
                SELECT
                  d.history_date,
                  COUNT(*) AS cnt
                FROM canonical_track_occurrences t
                JOIN canonical_recommendation_items ri ON t.item_id = ri.item_id
                JOIN canonical_days d ON ri.day_id = d.day_id
                WHERE lower(t.title) = lower(?)
                GROUP BY 1
                ORDER BY cnt DESC, d.history_date ASC
                LIMIT ?
                """,
                [normalized_name, limit],
            ).fetchall()
        else:
            conn.close()
            raise ValueError(f"Unsupported entity_type: {entity_type}")

        conn.close()
        return {
            "status": "ok",
            "data": {
                "entity_type": entity_type,
                "entity_name": normalized_name,
                "peak_dates": [{"history_date": str(row[0]), "count": row[1]} for row in rows],
            },
            "summary": f"Peak dates for {entity_type} '{normalized_name}'.",
            "limitations": [] if rows else ["entity_not_found"],
        }

    def weekly_rollup(self) -> Dict[str, Any]:
        conn = self._conn()
        top_artists = conn.execute(
            """
            WITH artist_weeks AS (
              SELECT
                strftime(history_date, '%Y-W%W') AS week_id,
                ta.artist_name,
                COUNT(*) AS cnt,
                ROW_NUMBER() OVER (
                  PARTITION BY strftime(history_date, '%Y-W%W')
                  ORDER BY COUNT(*) DESC, ta.artist_name ASC
                ) AS rn
              FROM canonical_track_artists ta
              WHERE ta.artist_name IS NOT NULL
              GROUP BY 1, 2
            )
            SELECT week_id, artist_name, cnt
            FROM artist_weeks
            WHERE rn <= 3
            ORDER BY week_id, cnt DESC, artist_name ASC
            """
        ).fetchall()
        top_genres = conn.execute(
            """
            WITH genre_weeks AS (
              SELECT
                strftime(history_date, '%Y-W%W') AS week_id,
                album_genre,
                COUNT(*) AS cnt,
                ROW_NUMBER() OVER (
                  PARTITION BY strftime(history_date, '%Y-W%W')
                  ORDER BY COUNT(*) DESC, album_genre ASC
                ) AS rn
              FROM canonical_track_occurrences
              WHERE album_genre IS NOT NULL
              GROUP BY 1, 2
            )
            SELECT week_id, album_genre, cnt
            FROM genre_weeks
            WHERE rn <= 3
            ORDER BY week_id, cnt DESC, album_genre ASC
            """
        ).fetchall()
        conn.close()

        by_week: Dict[str, Dict[str, Any]] = {}
        for week_id, artist_name, cnt in top_artists:
            by_week.setdefault(week_id, {"top_artists": [], "top_genres": []})
            by_week[week_id]["top_artists"].append({"artist_name": artist_name, "count": cnt})
        for week_id, genre, cnt in top_genres:
            by_week.setdefault(week_id, {"top_artists": [], "top_genres": []})
            by_week[week_id]["top_genres"].append({"genre": genre, "count": cnt})

        return {
            "status": "ok",
            "data": by_week,
            "summary": "Weekly rollup with top artists and genres.",
            "limitations": [],
        }

    def weekly_trend_summary(self) -> Dict[str, Any]:
        weekly = self.weekly_rollup()
        by_week = weekly["data"]
        ordered_weeks = sorted(by_week.keys())

        artist_leader_counts: Dict[str, int] = {}
        genre_leader_counts: Dict[str, int] = {}
        recurring_artists: Dict[str, int] = {}
        recurring_genres: Dict[str, int] = {}
        leadership_changes: List[Dict[str, Any]] = []

        previous_artist_leader: Optional[str] = None
        previous_genre_leader: Optional[str] = None

        for week_id in ordered_weeks:
            week_data = by_week[week_id]
            artists = week_data.get("top_artists", [])
            genres = week_data.get("top_genres", [])

            for row in artists:
                artist_name = row["artist_name"]
                recurring_artists[artist_name] = recurring_artists.get(artist_name, 0) + 1
            for row in genres:
                genre = row["genre"]
                recurring_genres[genre] = recurring_genres.get(genre, 0) + 1

            artist_leader = artists[0]["artist_name"] if artists else None
            genre_leader = genres[0]["genre"] if genres else None

            if artist_leader is not None:
                artist_leader_counts[artist_leader] = artist_leader_counts.get(artist_leader, 0) + 1
            if genre_leader is not None:
                genre_leader_counts[genre_leader] = genre_leader_counts.get(genre_leader, 0) + 1

            if previous_artist_leader and artist_leader and previous_artist_leader != artist_leader:
                leadership_changes.append(
                    {
                        "week_id": week_id,
                        "dimension": "artist",
                        "from": previous_artist_leader,
                        "to": artist_leader,
                    }
                )
            if previous_genre_leader and genre_leader and previous_genre_leader != genre_leader:
                leadership_changes.append(
                    {
                        "week_id": week_id,
                        "dimension": "genre",
                        "from": previous_genre_leader,
                        "to": genre_leader,
                    }
                )

            previous_artist_leader = artist_leader
            previous_genre_leader = genre_leader

        def _rank(counter: Dict[str, int], field_name: str) -> List[Dict[str, Any]]:
            return [
                {field_name: name, "weeks": weeks}
                for name, weeks in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
            ]

        return {
            "status": "ok",
            "data": {
                "weeks": ordered_weeks,
                "week_count": len(ordered_weeks),
                "artist_leaders": _rank(artist_leader_counts, "artist_name"),
                "genre_leaders": _rank(genre_leader_counts, "genre"),
                "recurring_artists": _rank(recurring_artists, "artist_name"),
                "recurring_genres": _rank(recurring_genres, "genre"),
                "leadership_changes": leadership_changes,
                "weekly_rollup": by_week,
            },
            "summary": "Deterministic weekly trend summary with leaders, recurrence, and leadership changes.",
            "limitations": [],
        }

    def period_compare(self, date_from: str, date_to: str, split_date: str) -> Dict[str, Any]:
        conn = self._conn()

        def _top_entities(entity_sql: str, params: List[Any]) -> List[Dict[str, Any]]:
            rows = conn.execute(entity_sql, params).fetchall()
            return [{"entity": row[0], "count": row[1]} for row in rows]

        artist_sql = """
            SELECT ta.artist_name AS entity, COUNT(*) AS cnt
            FROM canonical_track_artists ta
            WHERE ta.artist_name IS NOT NULL AND history_date BETWEEN ? AND ?
            GROUP BY 1
            ORDER BY cnt DESC, entity ASC
            LIMIT 5
        """
        genre_sql = """
            SELECT album_genre AS entity, COUNT(*) AS cnt
            FROM canonical_track_occurrences
            WHERE album_genre IS NOT NULL AND history_date BETWEEN ? AND ?
            GROUP BY 1
            ORDER BY cnt DESC, entity ASC
            LIMIT 5
        """

        left_artists = _top_entities(artist_sql, [date_from, split_date])
        left_genres = _top_entities(genre_sql, [date_from, split_date])
        right_artists = _top_entities(artist_sql, [split_date, date_to])
        right_genres = _top_entities(genre_sql, [split_date, date_to])
        conn.close()

        return {
            "status": "ok",
            "data": {
                "left_period": {
                    "date_from": date_from,
                    "date_to": split_date,
                    "top_artists": left_artists,
                    "top_genres": left_genres,
                },
                "right_period": {
                    "date_from": split_date,
                    "date_to": date_to,
                    "top_artists": right_artists,
                    "top_genres": right_genres,
                },
            },
            "summary": "Comparison of two periods.",
            "limitations": [],
        }

    def period_compare_summary(self, date_from: str, date_to: str, split_date: str) -> Dict[str, Any]:
        payload = self.period_compare(date_from=date_from, date_to=date_to, split_date=split_date)["data"]
        left_artists = payload["left_period"]["top_artists"]
        right_artists = payload["right_period"]["top_artists"]
        left_genres = payload["left_period"]["top_genres"]
        right_genres = payload["right_period"]["top_genres"]

        left_artist_set = {row["entity"] for row in left_artists}
        right_artist_set = {row["entity"] for row in right_artists}
        left_genre_set = {row["entity"] for row in left_genres}
        right_genre_set = {row["entity"] for row in right_genres}

        return {
            "status": "ok",
            "data": {
                "left_period": payload["left_period"],
                "right_period": payload["right_period"],
                "artist_persistence": sorted(left_artist_set & right_artist_set),
                "artist_new_in_right": sorted(right_artist_set - left_artist_set),
                "artist_missing_in_right": sorted(left_artist_set - right_artist_set),
                "genre_persistence": sorted(left_genre_set & right_genre_set),
                "genre_new_in_right": sorted(right_genre_set - left_genre_set),
                "genre_missing_in_right": sorted(left_genre_set - right_genre_set),
            },
            "summary": "Deterministic comparison summary for two periods.",
            "limitations": [],
        }

    def stability_vs_spikes(self, dimension: str = "artist") -> Dict[str, Any]:
        weekly = self.weekly_trend_summary()["data"]
        recurring_artists = weekly["recurring_artists"]
        artist_leaders = weekly["artist_leaders"]
        recurring_genres = weekly["recurring_genres"]
        genre_leaders = weekly["genre_leaders"]
        leadership_changes = weekly["leadership_changes"]

        stable_artists = [row for row in recurring_artists if row["weeks"] >= 4][:5]
        spike_artists = [row for row in artist_leaders if row["weeks"] == 1][:5]
        stable_genres = [row for row in recurring_genres if row["weeks"] >= 4][:5]
        spike_genres = [row for row in genre_leaders if row["weeks"] == 1][:5]

        return {
            "status": "ok",
            "data": {
                "dimension": dimension,
                "stable_artists": stable_artists,
                "spike_artists": spike_artists,
                "stable_genres": stable_genres,
                "spike_genres": spike_genres,
                "leadership_change_count": len(leadership_changes),
                "leadership_changes": leadership_changes[:5],
            },
            "summary": "Stable artists versus short-lived weekly leaders.",
            "limitations": [],
        }
