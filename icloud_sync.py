#!/usr/bin/env python3
"""Backward-compatible entrypoint for the incremental iCloud sync script."""

from __future__ import annotations

from icloud_photo_backup.auth import login_icloud
from icloud_photo_backup.cli import build_parser, main, parse_after_date
from icloud_photo_backup.db import ensure_schema, init_db, is_downloaded, mark_downloaded
from icloud_photo_backup.logging_utils import setup_logging
from icloud_photo_backup.paths import build_output_dir, parse_created_at, unique_path, validate_target_dir
from icloud_photo_backup.sync import (
    cleanup_stale_parts,
    download_asset,
    get_asset_filename,
    get_asset_id,
    is_video_asset,
    iter_assets,
    run_sync,
    stream_to_file,
)

__all__ = [
    "build_output_dir",
    "build_parser",
    "cleanup_stale_parts",
    "download_asset",
    "ensure_schema",
    "get_asset_filename",
    "get_asset_id",
    "init_db",
    "is_downloaded",
    "is_video_asset",
    "iter_assets",
    "login_icloud",
    "main",
    "mark_downloaded",
    "parse_after_date",
    "parse_created_at",
    "run_sync",
    "setup_logging",
    "stream_to_file",
    "unique_path",
    "validate_target_dir",
]


if __name__ == "__main__":
    raise SystemExit(main())
