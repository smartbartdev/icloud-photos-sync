from __future__ import annotations

import datetime as dt
import logging
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from .auth import login_icloud
from .db import (
    ensure_schema,
    get_latest_downloaded_created_at,
    get_meta,
    init_db,
    is_downloaded,
    mark_downloaded,
    set_meta,
)
from .logging_utils import setup_logging
from .paths import build_output_dir, log_file_path, parse_created_at, unique_path, validate_target_dir


VIDEO_EXTENSIONS = {
    ".3gp",
    ".avi",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".webm",
}

SPINNER_FRAMES = ("|", "/", "-", "\\")


def to_utc_datetime(value: dt.datetime) -> dt.datetime:
    """Normalize datetimes to UTC for safe comparisons."""
    if value.tzinfo is None:
        return value.replace(tzinfo=dt.timezone.utc)
    return value.astimezone(dt.timezone.utc)


def format_bytes(num_bytes: int) -> str:
    """Return a human-readable byte size string."""
    if num_bytes < 1024:
        return f"{num_bytes} B"

    units = ("KB", "MB", "GB", "TB")
    value = float(num_bytes)
    for unit in units:
        value /= 1024.0
        if value < 1024.0:
            return f"{value:.1f} {unit}"
    return f"{value:.1f} PB"


class LiveSyncProgress:
    """Render a single-line live progress indicator in TTY sessions."""

    def __init__(self, *, enabled: bool) -> None:
        self.enabled = enabled and sys.stdout.isatty()
        self._frame_index = 0
        self._line_len = 0
        self._started_at = time.monotonic()
        self._last_downloaded_bytes = 0

    def render(
        self,
        *,
        downloaded_bytes: int,
        photos: int,
        videos: int,
        skipped: int,
        failed: int,
    ) -> None:
        """Render or update the live progress line."""
        if not self.enabled:
            return

        elapsed_seconds = max(time.monotonic() - self._started_at, 0.001)
        displayed_downloaded_bytes = max(downloaded_bytes, self._last_downloaded_bytes)
        self._last_downloaded_bytes = displayed_downloaded_bytes
        bytes_per_second = int(displayed_downloaded_bytes / elapsed_seconds)
        spinner = SPINNER_FRAMES[self._frame_index % len(SPINNER_FRAMES)]
        self._frame_index += 1

        line = (
            f"[{spinner}] Downloaded: {format_bytes(displayed_downloaded_bytes)} "
            f"/ {photos} Photos / {videos} Videos "
            f"| Skipped: {skipped} | Failed: {failed} "
            f"| Rate: {format_bytes(bytes_per_second)}/s"
        )
        padding = " " * max(self._line_len - len(line), 0)
        sys.stdout.write(f"\r{line}{padding}")
        sys.stdout.flush()
        self._line_len = len(line)

    def clear_line(self) -> None:
        """Clear active live line before standard log output."""
        if not self.enabled or self._line_len == 0:
            return

        sys.stdout.write(f"\r{' ' * self._line_len}\r")
        sys.stdout.flush()
        self._line_len = 0

    def finish(self) -> None:
        """End the live renderer and move to the next line."""
        if not self.enabled:
            return
        if self._line_len > 0:
            sys.stdout.write("\n")
            sys.stdout.flush()
            self._line_len = 0


class LiveScanProgress:
    """Render single-line scan progress while iterating assets."""

    def __init__(self, *, enabled: bool) -> None:
        self.enabled = enabled and sys.stdout.isatty()
        self._frame_index = 0
        self._line_len = 0
        self._started_at = time.monotonic()
        self._last_render_at = 0.0

    def render(
        self,
        *,
        scanned: int,
        matched: int,
        cursor: Optional[dt.datetime],
        force: bool = False,
    ) -> None:
        """Render scanning status, throttled unless forced."""
        if not self.enabled:
            return

        now = time.monotonic()
        if not force and (now - self._last_render_at) < 0.2:
            return
        self._last_render_at = now

        elapsed_seconds = max(now - self._started_at, 0.001)
        assets_per_second = scanned / elapsed_seconds
        spinner = SPINNER_FRAMES[self._frame_index % len(SPINNER_FRAMES)]
        self._frame_index += 1

        cursor_text = cursor.isoformat() if cursor is not None else "none"
        line = (
            f"[{spinner}] Scanning: {scanned} seen / {matched} candidates "
            f"| Cursor: {cursor_text} | Rate: {assets_per_second:.1f} assets/s"
        )
        padding = " " * max(self._line_len - len(line), 0)
        sys.stdout.write(f"\r{line}{padding}")
        sys.stdout.flush()
        self._line_len = len(line)

    def clear_line(self) -> None:
        """Clear active scan line before other output."""
        if not self.enabled or self._line_len == 0:
            return
        sys.stdout.write(f"\r{' ' * self._line_len}\r")
        sys.stdout.flush()
        self._line_len = 0

    def finish(self) -> None:
        """End scan renderer and move to next line."""
        if not self.enabled:
            return
        if self._line_len > 0:
            sys.stdout.write("\n")
            sys.stdout.flush()
            self._line_len = 0


def get_asset_id(asset: Any) -> Optional[str]:
    """Extract stable unique id from asset metadata."""
    for field in ("id", "asset_id", "uuid", "guid"):
        value = getattr(asset, field, None)
        if value:
            return str(value)
    return None


def get_asset_filename(asset: Any) -> Optional[str]:
    """Extract filename from asset metadata."""
    for field in ("filename", "name"):
        value = getattr(asset, field, None)
        if value:
            return str(value)
    return None


def is_video_asset(asset: Any, filename: Optional[str]) -> bool:
    """Best-effort video detection using metadata and extension."""
    for field in ("item_type", "media_type", "type"):
        value = getattr(asset, field, None)
        if isinstance(value, str) and "video" in value.lower():
            return True

    if filename:
        ext = Path(filename).suffix.lower()
        if ext in VIDEO_EXTENSIONS:
            return True
    return False


def detect_media_type(asset: Any, filename: Optional[str]) -> str:
    """Return best-effort media type value."""
    for field in ("item_type", "media_type", "type"):
        value = getattr(asset, field, None)
        if isinstance(value, str) and value:
            lowered = value.lower()
            if "video" in lowered:
                return "video"
            if "photo" in lowered or "image" in lowered:
                return "photo"

    if is_video_asset(asset, filename):
        return "video"
    return "photo"


def parse_meta_datetime(value: Optional[str]) -> Optional[dt.datetime]:
    """Parse ISO datetime stored in sync metadata."""
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def effective_after_datetime(
    user_after: Optional[dt.date],
    stored_cursor: Optional[str],
) -> Optional[dt.datetime]:
    """Resolve the effective lower-bound datetime for scanning assets."""
    if user_after is not None:
        return dt.datetime.combine(user_after, dt.time.min)
    return parse_meta_datetime(stored_cursor)


def album_is_descending(album: Any) -> bool:
    """Return True when album iteration direction is descending."""
    direction = getattr(album, "_direction", None)
    if direction is None:
        return False

    raw_value = getattr(direction, "value", direction)
    return str(raw_value).upper() == "DESCENDING"


def iter_assets(
    api: Any,
    after: Optional[dt.datetime],
    skip_videos: bool,
    include_missing_created_at: bool = False,
    on_scan: Optional[Callable[[int, int], None]] = None,
) -> Iterable[Any]:
    """Yield assets from iCloud Photos with optional filtering."""
    photos = getattr(api, "photos", None)
    if photos is None:
        raise RuntimeError("iCloud Photos is unavailable for this account.")

    album = photos.all
    scanned_count = 0
    matched_count = 0
    after_utc = to_utc_datetime(after) if after is not None else None

    for asset in album:
        scanned_count += 1
        created_at = parse_created_at(getattr(asset, "created", None))
        created_at_utc = to_utc_datetime(created_at) if created_at is not None else None

        if after_utc is not None:
            if created_at_utc is None:
                if not include_missing_created_at:
                    if on_scan is not None:
                        on_scan(scanned_count, matched_count)
                    continue
            elif created_at_utc < after_utc:
                if on_scan is not None:
                    on_scan(scanned_count, matched_count)
                continue

        filename = get_asset_filename(asset)
        if skip_videos and is_video_asset(asset, filename):
            if on_scan is not None:
                on_scan(scanned_count, matched_count)
            continue

        matched_count += 1
        if on_scan is not None:
            on_scan(scanned_count, matched_count)
        yield asset


def stream_to_file(response: Any, output_path: Path) -> int:
    """Write downloaded response to file and return bytes written."""
    written = 0
    with output_path.open("wb") as fh:
        if isinstance(response, (bytes, bytearray)):
            fh.write(response)
            return len(response)

        if hasattr(response, "iter_content"):
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                fh.write(chunk)
                written += len(chunk)
            return written

        raw = getattr(response, "raw", None)
        if raw is not None and hasattr(raw, "stream"):
            for chunk in raw.stream(1024 * 1024, decode_content=False):
                if not chunk:
                    continue
                fh.write(chunk)
                written += len(chunk)
            return written

        content = getattr(response, "content", None)
        if content is not None:
            fh.write(content)
            return len(content)

        if hasattr(response, "read"):
            content = response.read()
            if isinstance(content, str):
                content = content.encode("utf-8")
            if content:
                fh.write(content)
                return len(content)

    raise RuntimeError("Download response did not contain readable binary data.")


def download_asset(
    asset: Any,
    destination_dir: Path,
    filename: str,
    retries: int = 3,
    retry_delay_seconds: float = 2.0,
) -> tuple[Path, int]:
    """Download one iCloud asset with retries and atomic rename."""
    destination_dir.mkdir(parents=True, exist_ok=True)

    final_path = unique_path(destination_dir / filename)
    temp_path = final_path.with_name(final_path.name + ".part")
    temp_path.unlink(missing_ok=True)

    last_error: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            response = asset.download()
            if response is None:
                raise RuntimeError("Asset returned no downloadable data.")
            bytes_written = stream_to_file(response, temp_path)
            temp_path.replace(final_path)
            return final_path, bytes_written
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            temp_path.unlink(missing_ok=True)
            if attempt < retries:
                time.sleep(retry_delay_seconds)

    raise RuntimeError(f"Download failed after {retries} attempts: {last_error}")


def cleanup_stale_parts(target_dir: Path, logger: logging.Logger) -> None:
    """Remove stale .part files from previous interrupted runs."""
    removed = 0
    for part_file in target_dir.rglob("*.part"):
        try:
            part_file.unlink()
            removed += 1
        except OSError:
            continue

    if removed:
        logger.info("Removed %s stale .part file(s).", removed)


def run_sync(
    *,
    target_dir: Path,
    db_path: Path,
    dry_run: bool,
    limit: Optional[int],
    verbose: bool,
    after: Optional[dt.date],
    skip_videos: bool,
    missing_created_at_strategy: str,
    username: str,
    password: Optional[str],
    app_log_file: Optional[Path] = None,
) -> int:
    """Run incremental sync and return process exit code."""
    validate_target_dir(target_dir)
    logger = setup_logging(app_log_file or log_file_path(), verbose)

    logger.info("Using destination: %s", target_dir)

    api = login_icloud(username or "", password, logger)

    if dry_run:
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            ensure_schema(conn)
        else:
            conn = sqlite3.connect(":memory:")
            ensure_schema(conn)
    else:
        conn = init_db(db_path)

    downloaded_count = 0
    skipped_count = 0
    failed_count = 0
    processed = 0
    downloaded_bytes = 0
    downloaded_photos = 0
    downloaded_videos = 0
    progress = LiveSyncProgress(enabled=not dry_run)
    scan_progress = LiveScanProgress(enabled=not dry_run)
    latest_created_at_downloaded: Optional[dt.datetime] = None
    saw_future_created_at = False
    scanned_assets = 0
    matched_assets = 0

    try:
        if not dry_run:
            cleanup_stale_parts(target_dir, logger)

        stored_cursor = get_meta(conn, "last_downloaded_created_at")
        if stored_cursor is None:
            stored_cursor = get_latest_downloaded_created_at(conn)

        scan_after = effective_after_datetime(after, stored_cursor)
        include_missing_created_at = missing_created_at_strategy == "download"
        if scan_after is not None:
            logger.info(
                "Using incremental timestamp cursor: %s",
                scan_after.isoformat(),
            )
            if include_missing_created_at:
                logger.info(
                    "Including assets with missing created_at during cursor scan."
                )

        logger.info("\nScanning iCloud Photos...")

        def on_scan(scanned: int, matched: int) -> None:
            nonlocal scanned_assets, matched_assets
            scanned_assets = scanned
            matched_assets = matched
            scan_progress.render(
                scanned=scanned_assets,
                matched=matched_assets,
                cursor=scan_after,
            )

        for asset in iter_assets(
            api,
            after=scan_after,
            skip_videos=skip_videos,
            include_missing_created_at=include_missing_created_at,
            on_scan=on_scan,
        ):
            scan_progress.clear_line()
            if limit is not None and processed >= limit:
                break

            processed += 1

            asset_id = get_asset_id(asset)
            filename = get_asset_filename(asset)
            created_at = parse_created_at(getattr(asset, "created", None))

            if not asset_id:
                failed_count += 1
                progress.clear_line()
                logger.warning("Failed: missing asset ID")
                progress.render(
                    downloaded_bytes=downloaded_bytes,
                    photos=downloaded_photos,
                    videos=downloaded_videos,
                    skipped=skipped_count,
                    failed=failed_count,
                )
                continue

            if not filename:
                failed_count += 1
                progress.clear_line()
                logger.warning("Failed: asset %s has no filename metadata", asset_id)
                progress.render(
                    downloaded_bytes=downloaded_bytes,
                    photos=downloaded_photos,
                    videos=downloaded_videos,
                    skipped=skipped_count,
                    failed=failed_count,
                )
                continue

            media_type = detect_media_type(asset, filename)

            if is_downloaded(conn, asset_id):
                skipped_count += 1
                if verbose:
                    progress.clear_line()
                    logger.info("Skipping already downloaded: %s", filename)
                progress.render(
                    downloaded_bytes=downloaded_bytes,
                    photos=downloaded_photos,
                    videos=downloaded_videos,
                    skipped=skipped_count,
                    failed=failed_count,
                )
                continue

            output_dir = build_output_dir(target_dir, created_at)
            if dry_run:
                planned = unique_path(output_dir / filename)
                logger.info("[DRY-RUN] Would download: %s", planned)
                downloaded_count += 1
                continue

            try:
                final_path, size = download_asset(asset, output_dir, filename)
                mark_downloaded(
                    conn,
                    asset_id=asset_id,
                    filename=final_path.name,
                    local_path=final_path,
                    created_at=created_at,
                    file_size=size,
                    media_type=media_type,
                    status="downloaded",
                )
                downloaded_count += 1
                if created_at is not None:
                    created_at_utc = to_utc_datetime(created_at)
                    now = dt.datetime.now(dt.timezone.utc)
                    if created_at_utc > now:
                        saw_future_created_at = True
                        logger.warning(
                            "Skipping asset with future timestamp: %s > %s (%s)",
                            created_at_utc,
                            now,
                            filename,
                        )
                    elif latest_created_at_downloaded is None:
                        latest_created_at_downloaded = created_at_utc
                    else:
                        latest_created_at_downloaded = max(
                            latest_created_at_downloaded,
                            created_at_utc,
                        )
                downloaded_bytes += size
                if media_type == "video":
                    downloaded_videos += 1
                else:
                    downloaded_photos += 1
                progress.render(
                    downloaded_bytes=downloaded_bytes,
                    photos=downloaded_photos,
                    videos=downloaded_videos,
                    skipped=skipped_count,
                    failed=failed_count,
                )

                if verbose:
                    progress.clear_line()
                    logger.info("Downloaded file: %s", final_path)
                    progress.render(
                        downloaded_bytes=downloaded_bytes,
                        photos=downloaded_photos,
                        videos=downloaded_videos,
                        skipped=skipped_count,
                        failed=failed_count,
                    )
            except Exception as exc:  # noqa: BLE001
                failed_count += 1
                progress.clear_line()
                logger.error("Failed: %s (%s)", filename, exc)
                progress.render(
                    downloaded_bytes=downloaded_bytes,
                    photos=downloaded_photos,
                    videos=downloaded_videos,
                    skipped=skipped_count,
                    failed=failed_count,
                )

        set_meta(conn, "last_sync_at", dt.datetime.now(dt.timezone.utc).isoformat())
        set_meta(conn, "last_sync_downloaded", str(downloaded_count))
        set_meta(conn, "last_sync_skipped", str(skipped_count))
        set_meta(conn, "last_sync_failed", str(failed_count))
        if latest_created_at_downloaded is not None:
            set_meta(
                conn,
                "last_downloaded_created_at",
                latest_created_at_downloaded.isoformat(),
            )
        elif downloaded_count > 0 and saw_future_created_at:
            logger.warning(
                "Cursor unchanged: downloaded assets included only future "
                "created_at values in this run."
            )

    finally:
        scan_progress.render(
            scanned=scanned_assets,
            matched=matched_assets,
            cursor=scan_after if "scan_after" in locals() else None,
            force=True,
        )
        scan_progress.finish()
        progress.finish()
        conn.close()

    logger.info("\nDone.")
    logger.info("Scanned assets: %s", scanned_assets)
    logger.info("Candidate assets: %s", matched_assets)
    logger.info("Downloaded: %s", downloaded_count)
    logger.info("Skipped: %s", skipped_count)
    logger.info("Failed: %s", failed_count)
    return 0
