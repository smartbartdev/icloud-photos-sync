# AGENTS Guide

This repository welcomes help from human contributors and AI coding agents.

Use this guide when you are working with an agent (or acting as one) to add features, fix bugs, and improve reliability safely.

## Project at a glance

- Project: `ipb` (iCloud Photo Backup CLI)
- Language: Python (`>=3.10`)
- Package: `icloud_photo_backup/`
- Tests: `pytest`
- Key docs:
  - `README.md`
  - `CONTRIBUTING.md`
  - `docs/operations.md`
  - `docs/release.md`

## Setup

Recommended:

```bash
./install.sh
source .venv/bin/activate
```

Manual alternative:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"
```

## Agent workflow (expected)

1. **Read context first**
   - Review `README.md` and `CONTRIBUTING.md`.
   - Inspect related code and tests before editing.
2. **Keep changes focused**
   - Do the smallest safe change for the requested outcome.
   - Avoid unrelated refactors.
3. **Preserve security expectations**
   - Never log or expose secrets (passwords, 2FA codes, tokens).
4. **Update tests for behavior changes**
   - Add or update tests in `tests/` when behavior changes.
5. **Verify locally**
   - Run targeted tests where possible, then broader tests if needed.

## Verification commands

Run the full suite:

```bash
python -m pytest -q
```

Or via Makefile:

```bash
make test
```

## Contribution quality bar

- Clear and minimal diff
- Tests passing for changed behavior
- No secret leakage in code, logs, docs, or tests
- Update user-facing docs when commands/behavior change

## Suggested task types for agents

- Feature implementation (small, scoped enhancements)
- Bug fixes with regression tests
- Test coverage improvements
- Documentation clarifications and examples
- CI and release-doc maintenance (where appropriate)

## PR handoff checklist

When an agent hands work to a human reviewer, include:

- What changed and why
- Files touched
- Tests run and results
- Any assumptions, tradeoffs, or follow-ups

If you are unsure about intent or safety, stop and ask for clarification before making broad changes.
