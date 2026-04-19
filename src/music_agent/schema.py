DDL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS snapshots (
      snapshot_id BIGINT PRIMARY KEY,
      filename TEXT NOT NULL,
      captured_at_utc TIMESTAMP,
      history_day_count INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS days (
      day_id BIGINT PRIMARY KEY,
      snapshot_id BIGINT NOT NULL,
      history_date DATE NOT NULL,
      day_index INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS recommendation_items (
      item_id BIGINT PRIMARY KEY,
      day_id BIGINT NOT NULL,
      item_index INTEGER NOT NULL,
      context_type TEXT,
      context_title TEXT,
      context_header TEXT,
      context_station_id TEXT,
      seed_count INTEGER
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS track_occurrences (
      occurrence_id BIGINT PRIMARY KEY,
      item_id BIGINT NOT NULL,
      track_index INTEGER NOT NULL,
      track_id TEXT,
      real_id TEXT,
      title TEXT,
      available BOOLEAN,
      error TEXT,
      duration_ms BIGINT,
      lyrics_available BOOLEAN,
      content_warning TEXT,
      track_source TEXT,
      album_id TEXT,
      album_title TEXT,
      album_genre TEXT,
      artist_count INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS track_artists (
      occurrence_id BIGINT NOT NULL,
      artist_index INTEGER NOT NULL,
      artist_id TEXT,
      artist_name TEXT
    )
    """,
    """
    CREATE OR REPLACE VIEW valid_track_occurrences AS
    SELECT *
    FROM track_occurrences
    WHERE title IS NOT NULL
    """,
    """
    CREATE OR REPLACE VIEW canonical_days AS
    WITH latest_snapshot_per_date AS (
      SELECT history_date, MAX(snapshot_id) AS snapshot_id
      FROM days
      GROUP BY 1
    )
    SELECT d.*
    FROM days d
    JOIN latest_snapshot_per_date l
      ON d.history_date = l.history_date
     AND d.snapshot_id = l.snapshot_id
    """,
    """
    CREATE OR REPLACE VIEW canonical_recommendation_items AS
    SELECT ri.*
    FROM recommendation_items ri
    JOIN canonical_days d ON ri.day_id = d.day_id
    """,
    """
    CREATE OR REPLACE VIEW canonical_track_occurrences AS
    SELECT t.*, d.history_date
    FROM track_occurrences t
    JOIN canonical_recommendation_items ri ON t.item_id = ri.item_id
    JOIN canonical_days d ON ri.day_id = d.day_id
    """,
    """
    CREATE OR REPLACE VIEW canonical_track_artists AS
    SELECT ta.*, t.history_date
    FROM track_artists ta
    JOIN canonical_track_occurrences t ON ta.occurrence_id = t.occurrence_id
    """,
]


RESET_STATEMENTS = [
    "DROP VIEW IF EXISTS canonical_track_artists",
    "DROP VIEW IF EXISTS canonical_track_occurrences",
    "DROP VIEW IF EXISTS canonical_recommendation_items",
    "DROP VIEW IF EXISTS canonical_days",
    "DROP VIEW IF EXISTS valid_track_occurrences",
    "DROP TABLE IF EXISTS track_artists",
    "DROP TABLE IF EXISTS track_occurrences",
    "DROP TABLE IF EXISTS recommendation_items",
    "DROP TABLE IF EXISTS days",
    "DROP TABLE IF EXISTS snapshots",
]
