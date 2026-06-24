# App spec: cmux

cmux is a terminal multiplexer with vertical tabs and notifications for AI coding agents. It is a **native macOS app built in Swift/Xcode**, managing its third-party dependencies via **Swift Package Manager** (`Package.swift` / `Package.resolved`) — *not* npm. It embeds Ghostty for terminal rendering.

## Repository

- **GitHub repo:** `manaflow-ai/cmux`
- **Homepage:** `https://cmux.dev` / `https://cmux.com`

## Version detection

1. **Homebrew (cask):**
   ```bash
   brew list --cask --versions cmux     # "cmux <version>"
   brew info --cask cmux                 # version, install path, source
   brew cat --cask cmux                  # url + sha256 the cask pins
   ```
   cmux is distributed as a **brew cask** — a prebuilt, notarized macOS app (`cmux-macos.dmg`) downloaded from GitHub releases. It is *not* a formula, so there is no `--build-from-source` via brew.
2. **From the app:**
   ```bash
   cmux --version     # e.g. "cmux 0.64.16 (96) [<commit>]"
   ```
3. Fall back to asking the user.

- **Version ↔ tag mapping:** version `<x.y.z>` → git tag `v<x.y.z>` (e.g. `0.64.16` → `v0.64.16`). The cask `url` is
  `https://github.com/manaflow-ai/cmux/releases/download/v#{version}/cmux-macos.dmg`.

## Trust policy

**`BUILD_FROM_SOURCE`**

Reasoning: cmux runs as the user's terminal and orchestrates AI coding agents — it has broad access to the shell, filesystem, and a local control socket. For a tool with this much reach, prefer building from the reviewed source tree at the audited tag rather than trusting the prebuilt DMG, so the installed artifact provably corresponds to code that was reviewed. (The human may override to `TRUST_RELEASE_BINARY` after verifying the cask's pinned `sha256` and the app's notarization, if they accept that trade-off.)

## Build steps

After the audit passes, a human builds and installs from source. **Confirm the current build commands against the repo's README/CONTRIBUTING at the target tag** — these are illustrative and may change between versions:

```bash
git clone https://github.com/manaflow-ai/cmux /tmp/cmux-build && cd /tmp/cmux-build
git checkout v<target-version>
git verify-tag v<target-version>      # if the tag is signed
# Build per the repo's documented instructions at this tag, then install the produced app.
```

> If the repo does not document a from-source build for the desktop app (Ghostty-based apps can be non-trivial to build), surface that to the user: either follow the documented build path, or consciously fall back to `TRUST_RELEASE_BINARY` with full provenance verification of the DMG.

## Provenance verification (if the human overrides to TRUST_RELEASE_BINARY)

- Compare the DMG's SHA-256 against the `sha256` pinned in the brew cask (`brew cat --cask cmux`) and/or the checksum in the GitHub release assets.
- macOS notarization / signature:
  ```bash
  codesign --verify --deep --strict /Applications/cmux.app
  spctl -a -vv /Applications/cmux.app
  ```
- Confirm the release tag of the DMG matches the tag whose commits were audited.

## Custom checks

cmux's reach makes these worth extra scrutiny in the commit diff:

- **Dependencies are Swift Package Manager, not npm** — audit `Package.swift` / `Package.resolved`, not `package.json` (which does not exist for the app). SPM deps are GitHub repos pinned by tag/revision; for advisory and freshness checks, resolve each dependency's GitHub repo + version tag (see `dependency-audit.md` §1 Swift/SPM row and §3 Swift/SPM freshness recipe).
- **Control socket** — cmux exposes a local unix socket (`CMUX_SOCKET_PATH`, default `/tmp/cmux.sock`) that accepts commands (`set_status`, `set-progress`, browser/markdown panels, etc.). Review any change to socket creation, permissions, peer PID/UID checks, or command parsing for injection or privilege issues.
- **Hooks** — cmux runs hooks that shell out (sidebar/status updates, CR/task detection, browser auth cookie injection). Scrutinise changes under hook/integration paths for shell injection or unexpected command execution.
- **Browser panels & auth** — the integration injects SSO/auth cookies into browser panels. Review any change touching cookie handling, auth, or outbound network calls.
- **Auto-update** — the cask is marked `auto_updates`. Review changes to the in-app updater: where it fetches updates from, and whether it verifies signatures/checksums before applying.
- **Embedded Ghostty / native components** — watch for new committed binaries or native blobs.

## Notes

- Release notes: GitHub releases on `manaflow-ai/cmux`.
- Because the cask `auto_updates`, the installed version may move on its own — confirm the actual running version with `cmux --version` rather than assuming the brew-recorded version.
