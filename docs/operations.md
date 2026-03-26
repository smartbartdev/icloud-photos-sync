# Operations Runbook

This runbook covers release automation for `ipb` and fallback procedures.

## Required GitHub secret

In `smartbartdev/icloud-photos-sync`, configure:

- `HOMEBREW_TAP_TOKEN`

Token scope should allow writing to `smartbartdev/homebrew-tap` and opening PRs.

## Automated flow

On release publish (`v*`):

1. Workflow `.github/workflows/homebrew-bump.yml` runs.
2. It computes the release source tarball SHA256.
3. It updates `Formula/ipb.rb` in the tap repo.
4. It opens (or reuses) a bump PR in `homebrew-tap`.

## Manual fallback

If automation fails:

1. Clone tap repo and bump formula manually:

```bash
git clone git@github.com:smartbartdev/homebrew-tap.git
cd homebrew-tap
./scripts/bump_ipb_formula.py --version 0.1.1 --sha256 <sha256>
```

2. Validate locally:

```bash
brew untap smartbartdev/tap
brew tap smartbartdev/tap
brew reinstall --build-from-source smartbartdev/tap/ipb
brew test smartbartdev/tap/ipb
```

3. Commit, push, and open PR in `homebrew-tap`.

## Rollback

If a formula bump is bad:

1. Revert the bad formula commit in `homebrew-tap`.
2. Push revert commit to `master`.
3. Retest install:

```bash
brew update
brew reinstall smartbartdev/tap/ipb
```
