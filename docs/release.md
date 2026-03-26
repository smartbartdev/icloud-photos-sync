# Release Checklist

This checklist is used for tagged releases (starting at `v0.1.0`).

## 1) Pre-release validation

- Ensure branch is up to date with `main`
- Run tests:

```bash
source .venv/bin/activate
python -m pytest -q
```

- Run compile check:

```bash
python -m py_compile icloud_sync.py icloud_photo_backup/*.py tests/*.py
```

## 2) Version and notes

- Confirm `pyproject.toml` has the intended release version
- Update `CHANGELOG.md` with release date and highlights
- Verify README usage snippets are current

## 3) Tag and push

```bash
git checkout main
git pull origin main
git tag v0.1.0
git push origin main --tags
```

## 4) GitHub Release

- Create a release from tag `v0.1.0`
- Use changelog content for release notes
- Confirm source archive is available for Homebrew formula use
- Bump tap formula using `homebrew-tap/scripts/bump_ipb_formula.py` with the new tag and SHA
- If automation fails, follow fallback steps in `docs/operations.md`

## 5) Post-release checks

- Validate install from source in a fresh venv
- Validate command entrypoint:

```bash
ipb --help
```

- Run smoke flow:

```bash
ipb init
ipb doctor
ipb sync --dry-run --limit 5
ipb status
```

- Validate Homebrew installation on a clean environment:

```bash
brew tap smartbartdev/tap
brew install smartbartdev/tap/ipb
ipb --help
```
