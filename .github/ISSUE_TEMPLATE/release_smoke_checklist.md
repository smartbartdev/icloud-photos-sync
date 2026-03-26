---
name: Release smoke checklist
about: Track manual release-day validation
title: "[Release Smoke] vX.Y.Z"
labels: roadmap
assignees: ""
---

## Release metadata

- Tag:
- GitHub release URL:
- Homebrew bump workflow run URL:

## Checklist

- [ ] `python -m pytest -q` passed on `main`
- [ ] GitHub release published
- [ ] Homebrew bump workflow succeeded
- [ ] Homebrew tap PR opened (or already up-to-date)
- [ ] Homebrew tap PR merged
- [ ] `brew update && brew install smartbartdev/tap/ipb` works
- [ ] `ipb --help` works
- [ ] README release dashboard links are current

## Notes

Add any follow-up actions or anomalies.
