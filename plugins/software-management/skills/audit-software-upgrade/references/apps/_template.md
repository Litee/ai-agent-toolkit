# App spec: <app-name>

> Copy this file to `<app-name>.md` in the same directory and fill in every section.
> The agent reads and reasons over this spec when auditing an upgrade for `<app-name>`.

## Repository

- **GitHub repo:** `<owner>/<repo>`
- **Homepage:** `<url>`

## Version detection

How to determine the installed version, in precedence order:

1. Homebrew: `brew list --versions <app>` / `brew info --cask <app>`  (state formula vs cask, and whether it's prebuilt)
2. From the app: `<app> --version`
3. Fall back to asking the user.

- **Version ↔ tag mapping:** e.g. version `1.2.3` → git tag `v1.2.3`.

## Trust policy

Pick one:

- `TRUST_RELEASE_BINARY` — trust the provider's signed release artifact after verifying provenance (checksum/signature/notarization, same tag as audited).
- `BUILD_FROM_SOURCE` — do not trust prebuilt binaries; build and install from the reviewed source.

State the chosen policy and the reasoning.

## Build steps  (required if BUILD_FROM_SOURCE)

The exact commands a human runs after the audit passes (this skill does not run them):

```bash
git clone <repo-url> /tmp/<app>-build && cd /tmp/<app>-build
git checkout <target-tag>
<build command>
<install command>
```

## Provenance verification  (required if TRUST_RELEASE_BINARY)

- Where published checksums live (release assets / notes / brew cask `sha256`).
- Signature/notarization to check (`codesign`, `cosign`, `gpg`, …).

## Custom checks

App-specific things the security review must pay extra attention to. Examples:
- Sensitive directories or files unique to this app (hooks, plugins, sockets, credential stores).
- Known high-risk subsystems.
- Third-party dependencies that warrant closer scrutiny.

## Notes

Anything else useful: typical release cadence, where release notes live, known gotchas.
