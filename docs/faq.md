# FAQ

## 1) `ipb sync` says the destination is unmounted. What do I do?

If your destination starts with `/Volumes/...`, make sure the external drive is mounted in Finder.

Then rerun sync:

```bash
ipb sync "/Volumes/MyExternalDrive/iCloud-backup"
```

## 2) `ipb` keeps asking for 2FA. Is this normal?

Yes, this can happen depending on iCloud session state.

Tips:

- Complete `ipb init` and store credentials correctly.
- Ensure your system clock/timezone are correct.
- Run `ipb login` again if credentials changed.
- If no 2FA push appears, try logging into https://appleid.apple.com in your web browser first to establish a trusted session, then retry `ipb sync`.
- If using a VPN (like Tailscale), temporarily disconnect it during authentication—Apple may block 2FA for VPN connections for security reasons.
- If you don't receive 2FA push notifications on your devices, check:
  - All devices are connected to Wi-Fi or cellular (not just using the Mac)
  - iCloud notifications are enabled in device settings
  - Your Apple ID hasn't been restricted (check https://appleid.apple.com)

## 3) My incremental sync still scans too much. How can I speed it up?

Rebuild the incremental cursor from your existing DB:

```bash
ipb cursor rebuild "/Volumes/MyExternalDrive/iCloud-backup"
```

Then check:

```bash
ipb status "/Volumes/MyExternalDrive/iCloud-backup"
```

Look for `Last downloaded created_at`.

## 4) Why do I see `unknown_date/` folders?

Some assets do not expose a usable `created_at` value via iCloud metadata.

`ipb` places those files under `unknown_date/` by design so downloads remain safe and complete.

## 5) Why do filenames get `_1`, `_2`, etc.?

That is collision protection.

`ipb` deduplicates by iCloud asset ID, not filename. If two files would map to the same local name, it appends suffixes to avoid overwriting existing files.

## 6) Homebrew install shows a cryptography linkage warning. Is it broken?

Current behavior: install can complete and `ipb --help` works, while Homebrew may still report a linkage warning related to `cryptography` on some systems.

Track status in:

- https://github.com/smartbartdev/icloud-photos-sync/issues/7

## 7) How do I do a safe test before a full sync?

Use dry-run + limit + verbose:

```bash
ipb sync "/Volumes/MyExternalDrive/iCloud-backup" --dry-run --limit 20 --verbose
```

If output looks right, run full sync without `--dry-run`.

## 8) I got a new Mac. Can I reuse my existing backup folder?

Yes. Point `ipb restore` at your existing destination:

```bash
ipb restore "/Volumes/MyExternalDrive/iCloud-backup"
```

This restores local initialization against that folder so you can continue with `ipb sync`.

## 9) `ipb doctor` reports `pyicloud installed` as FAIL after Homebrew install

Try reinstalling the formula to repair the embedded virtualenv:

```bash
brew reinstall smartbartdev/tap/ipb
```

Then rerun:

```bash
ipb doctor
```
