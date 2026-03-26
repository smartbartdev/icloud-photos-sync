# Contributing

Thanks for your interest in contributing to `ipb`.

## Development setup

```bash
./install.sh
source .venv/bin/activate
```

Or manually:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"
```

## Run tests

```bash
python -m pytest -q
```

## Coding expectations

- Keep changes focused and minimal.
- Add or update tests for behavior changes.
- Avoid unrelated refactors in feature or bugfix PRs.
- Do not log secrets (passwords, 2FA codes, tokens).

## Pull requests

1. Create a feature branch from `main`.
2. Make your changes with tests.
3. Ensure tests pass locally.
4. Open a PR with a clear summary and verification steps.
