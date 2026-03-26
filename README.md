# iCloud Photo Backup (`ipb`)

`ipb` is a Python CLI for incremental iCloud Photos backup on macOS.

It downloads new photo/video assets into a destination folder, tracks downloaded
asset IDs in SQLite, and safely skips already-downloaded items on repeat runs.

## Important note about where files live

- Keep the script/tool installed on your Mac (internal storage), not on the external drive.
- The external drive is only the storage target.
- If the drive is unplugged or unmounted, the sync fails cleanly.

## Requirements

- macOS
- Python 3.10+
- iCloud account with Photos enabled

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

After editable install, the `ipb` command is available in the active venv.

## First-time setup

```bash
ipb init
```

This creates:

- `~/.config/ipb/config.json`
- `~/.config/ipb/logs/ipb.log`
- `~/.config/ipb/session/`

You will be prompted for:

- iCloud username
- iCloud password
- whether to store password in macOS keychain
- optional default destination

## Minimal usage

```bash
ipb init
cd /Volumes/MyDrive/iCloud-backup
ipb sync
```

## Commands

- `ipb init` - interactive setup
- `ipb sync [DESTINATION]` - incremental sync
- `ipb config show` - print config with secret redaction
- `ipb doctor` - local checks (config, sqlite, pyicloud, destination)
- `ipb login` - update credentials
- `ipb logout` - clear credentials and session files
- `ipb status [DESTINATION]` - print config and sync status
- `ipb cursor rebuild [DESTINATION]` - rebuild incremental cursor from existing DB rows

## Sync options

```bash
ipb sync "/Volumes/MyExternalDrive/iCloud-backup" --dry-run --limit 20 --verbose
```

Available sync flags:

- `--dry-run`
- `--limit N`
- `--after YYYY-MM-DD`
- `--skip-videos`
- `--verbose`
- `--db-path PATH`

Destination resolution order for `ipb sync`:

1. CLI `DESTINATION`
2. `default_destination` in config
3. current working directory

## Authentication and 2FA

`ipb` uses `pyicloud`.

- Logs in with credentials from config or keychain.
- If 2FA is required, prompts for code in terminal.
- Validates code and attempts to trust session.

Passwords and 2FA codes are never written to logs.

## SQLite manifest

Default DB path per destination:

- `<destination>/.ipb.sqlite3`

Tables:

- `downloaded_assets`
- `sync_meta`

`downloaded_assets` uses iCloud asset ID as the primary key for deduplication.
Rows are inserted only after successful final file write.

`sync_meta` stores run metadata, including `last_downloaded_created_at`. On later
sync runs, `ipb` uses that timestamp as an incremental cursor so it does not need
to scan all historical assets every time.

If you already have a large existing manifest and want to bootstrap/fix the cursor,
run:

```bash
ipb cursor rebuild "/Volumes/MyExternalDrive/iCloud-backup"
```

## Destination layout

```text
DEST/
  2024/
    01/
    02/
  2025/
    03/
  unknown_date/
  .ipb.sqlite3
```

Rules:

- with creation date -> `YYYY/MM/`
- missing date -> `unknown_date/`

## Logging

File log path:

- `~/.config/ipb/logs/ipb.log`

Includes timestamps, errors, and sync summary.

## CI

GitHub Actions CI is defined in `.github/workflows/ci.yml`.

It runs on pushes to `main` and on pull requests, and it currently:

- tests Python `3.10`, `3.11`, and `3.12`
- runs on `macos-latest` and `ubuntu-latest`
- installs the package with dev dependencies
- verifies Python files compile
- runs `pytest -q`

## Tests

```bash
pytest -q
```

Or with Makefile helpers:

```bash
make install-dev
make test
make smoke
```

`make smoke` prints a manual operator checklist for a quick real-world sanity pass.

## Open source

- License: `MIT` (see `LICENSE`)
- Contributing guide: `CONTRIBUTING.md`
- Code of conduct: `CODE_OF_CONDUCT.md`
- Security reporting: `SECURITY.md`
- Changelog: `CHANGELOG.md`
- Release checklist: `docs/release.md`
