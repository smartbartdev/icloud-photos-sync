# Launch Notes Template

Use this template when announcing a new release.

## Release: vX.Y.Z

`ipb` is a macOS CLI for incremental iCloud Photos backups to local/external storage.

### Highlights

-
-
-

### Install

Homebrew:

```bash
brew tap smartbartdev/tap
brew install smartbartdev/tap/ipb
```

Python:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### Quick start

```bash
ipb init
ipb doctor
ipb sync --dry-run --limit 20
```

### Links

- Release notes: <release-url>
- Changelog: `CHANGELOG.md`
- Issues: https://github.com/smartbartdev/icloud-photos-sync/issues
