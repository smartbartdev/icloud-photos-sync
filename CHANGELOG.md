# Changelog

All notable changes to this project are documented in this file.

## [1.2.3] - 2026-04-06

### Fixed

- Improved 2FA UX when Apple does not return trusted devices for the current session by printing explicit recovery guidance.
- Improved 2FA retry behavior by allowing multiple verification attempts before failing.
- Added guidance for cases where 2FA push notifications aren't received (e.g., when using VPNs like Tailscale).

### Improved

- Added clearer final error messaging with concrete fallback steps when 2FA cannot be completed.
- Updated FAQ with troubleshooting steps for common 2FA issues including VPN interference and device notification problems.
- Added web-based authentication workaround: users can now log into https://appleid.apple.com first to establish a trusted session.

## [1.2.2] - 2026-04-06

### Improved

- Added a fallback 2FA flow that can request a verification code from trusted devices when no push notification appears.
- Added clearer terminal guidance for users authenticating from a new Mac while another trusted device is already signed in.

### Fixed

- Improved 2FA validation compatibility by using the best available verification method (`validate_2fa_code` or `validate_verification_code`).

## [1.2.1] - 2026-04-06

### Fixed

- Improved iCloud client import compatibility by supporting both `pyicloud` and `pyicloud_ipd` module names.
- Improved error messages when iCloud client loading fails, including Homebrew reinstall guidance.
- Enhanced `ipb doctor` output with dependency diagnostic details for faster troubleshooting.

## [1.2.0] - 2026-04-06

### Added

- Added `ipb restore [DESTINATION]` to restore local initialization against an existing backup directory.
- Added restore flow documentation for users migrating to a new Mac while reusing an existing external-drive backup.

### Changed

- `ipb restore` now seeds `last_downloaded_created_at` from existing manifest rows when missing, so incremental sync can continue efficiently.

## [0.1.1] - 2026-03-26

### Added

- Added release automation workflow to open Homebrew formula bump PRs in `smartbartdev/homebrew-tap` on published releases.
- Added operations runbook (`docs/operations.md`) with automation setup, manual fallback, and rollback guidance.
- Added launch template (`docs/launch.md`) and public roadmap (`docs/roadmap.md`).

### Changed

- Hardened Homebrew bump workflow update logic for `Formula/ipb.rb` URL/SHA updates across formatting variations.
- Improved idempotency by skipping duplicate PR creation when an open bump PR already exists.
- Expanded release docs and README links for release and operations visibility.

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
