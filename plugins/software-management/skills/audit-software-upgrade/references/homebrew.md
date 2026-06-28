# Homebrew: version detection & trust signal

Commands to detect an installed application's version via Homebrew and understand the trust implications.

## Detection commands

```bash
# Is it managed by brew at all?
brew list --versions <app>          # formula: prints "<app> <version>"
brew list --cask --versions <app>   # cask: prints "<app> <version>"

# Rich metadata — source URL, homepage, whether prebuilt (cask) or buildable (formula)
brew info <app>
brew info --cask <app>

# The cask/formula source reveals the upstream GitHub repo and artifact URL
brew cat --cask <app>     # e.g. url "https://github.com/<owner>/<repo>/releases/download/v#{version}/..."
brew cat <app>
```

## Cask vs. formula trust signal

- A **cask** ships a prebuilt artifact (`.app` / `.dmg` / binary) → trust model is usually `TRUST_RELEASE_BINARY`.
- A **formula** can build from source (`brew install --build-from-source`) → `BUILD_FROM_SOURCE` is viable.

## Discovering the upstream repo

`brew info` and `brew cat` reveal the upstream GitHub repo and the exact artifact URL (e.g. `url "https://github.com/<owner>/<repo>/releases/download/v#{version}/..."`). Use these to confirm the correct GitHub repo and to understand what artifact gets installed.

## `auto_updates` caveat

A cask marked `auto_updates` may move the installed version on its own; confirm the actual running version with the app's own `--version` flag rather than relying on the brew-recorded version.
