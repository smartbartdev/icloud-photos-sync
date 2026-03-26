from __future__ import annotations

import datetime as dt
import sqlite3
from pathlib import Path
from typing import Optional


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Ensure required SQLite tables exist."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS downloaded_assets (
            asset_id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            local_path TEXT NOT NULL,
            created_at TEXT,
            downloaded_at TEXT NOT NULL,
            file_size INTEGER,
            media_type TEXT,
            status TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sync_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    conn.commit()


def init_db(db_path: Path) -> sqlite3.Connection:
    """Create/open SQLite database and ensure schema exists."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    ensure_schema(conn)
    return conn


def is_downloaded(conn: sqlite3.Connection, asset_id: str) -> bool:
    """Return True when an asset_id exists in the manifest."""
    row = conn.execute(
        "SELECT 1 FROM downloaded_assets WHERE asset_id = ? LIMIT 1", (asset_id,)
    ).fetchone()
    return row is not None


def mark_downloaded(
    conn: sqlite3.Connection,
    *,
    asset_id: str,
    filename: str,
    local_path: Path,
    created_at: Optional[dt.datetime],
    file_size: int,
    media_type: Optional[str] = None,
    status: str = "downloaded",
) -> None:
    """Insert a completed download record into SQLite."""
    downloaded_at = dt.datetime.now(dt.timezone.utc).isoformat()
    created_at_iso = created_at.isoformat() if created_at else None
    conn.execute(
        """
        INSERT INTO downloaded_assets (
            asset_id,
            filename,
            local_path,
            created_at,
            downloaded_at,
            file_size,
            media_type,
            status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            asset_id,
            filename,
            str(local_path),
            created_at_iso,
            downloaded_at,
            file_size,
            media_type,
            status,
        ),
    )
    conn.commit()


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    """Set a key/value metadata entry."""
    conn.execute(
        """
        INSERT INTO sync_meta(key, value)
        VALUES(?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )
    conn.commit()


def get_meta(conn: sqlite3.Connection, key: str) -> Optional[str]:
    """Get a metadata value by key."""
    row = conn.execute("SELECT value FROM sync_meta WHERE key = ?", (key,)).fetchone()
    if row is None:
        return None
    return str(row[0])


def get_downloaded_count(conn: sqlite3.Connection) -> int:
    """Return total number of downloaded assets."""
    row = conn.execute("SELECT COUNT(*) FROM downloaded_assets").fetchone()
    if row is None:
        return 0
    return int(row[0])


def get_latest_downloaded_created_at(conn: sqlite3.Connection) -> Optional[str]:
    """Return latest non-null created_at value from downloaded assets."""
    row = conn.execute(
        """
        SELECT MAX(created_at)
        FROM downloaded_assets
        WHERE status = 'downloaded' AND created_at IS NOT NULL
        """
    ).fetchone()
    if row is None or row[0] is None:
        return None
    return str(row[0])
