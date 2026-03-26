# Changelog

All notable changes to this project are documented in this file.

## [0.1.0] - 2026-03-26

### Added

- Initial `ipb` CLI with subcommands:
  - `init`, `sync`, `config show`, `doctor`, `login`, `logout`, `status`
- Incremental iCloud Photos sync with SQLite manifest (`.ipb.sqlite3`)
- Date-based destination layout (`YYYY/MM` and `unknown_date`)
- Safe file writes with `.part` temporary files and atomic rename
- Filename collision handling (`_1`, `_2`, ...)
- 2FA interactive auth flow via `pyicloud`
- Optional keychain-backed credential storage
- Live sync progress UI in TTY with spinner and transfer stats
- Cursor support for faster incremental scans:
  - `last_downloaded_created_at` stored in `sync_meta`
  - `ipb cursor rebuild [DESTINATION]` utility
- CI workflow for tests and compile checks
- Project tests for DB, CLI behavior, sync helpers, and progress logic

### Notes

- This is the first open-source release candidate baseline.
