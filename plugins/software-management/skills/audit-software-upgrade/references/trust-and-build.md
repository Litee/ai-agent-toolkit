# Trust Model & Build-From-Source Verification

Each app spec declares a **trust policy**. This decides whether the human should install the provider's prebuilt artifact or build from the reviewed source. The human may override the policy at runtime.

## `TRUST_RELEASE_BINARY`

The provider's signed release artifact is trusted **once provenance is verified**. Before recommending the prebuilt binary, confirm:

### Same provenance as the audited tag

The artifact you'd install must come from the exact release tag whose commits you reviewed. Do not audit `v1.2.0` and install a binary from a different/re-cut release.

### Checksum verification

```bash
# Published checksums (often in the release assets or release notes)
gh release view <tag> --repo <owner>/<repo> --json assets --jq '.assets[].name'

# Compare a downloaded artifact against the published checksum
shasum -a 256 <downloaded-artifact>
# ...must equal the published SHA-256.
```

### Signature / notarization (when available)

- **macOS** `.app`/`.dmg`: `codesign --verify --deep --strict <app>` and `spctl -a -vv <app>` (notarization / Gatekeeper).
- **Sigstore / cosign**: `cosign verify-blob --signature <sig> <artifact>` if the project publishes signatures.
- **GPG**: `gpg --verify <artifact>.asc <artifact>` against the maintainer's known key.

### Homebrew casks

A brew **cask** installs the provider's prebuilt artifact and pins a checksum in the cask file:

```bash
brew cat --cask <app>     # shows url + sha256 the cask enforces
```

brew verifies that checksum on install. Confirm the cask's `url`/`version` line up with the release tag you audited.

If provenance can be fully verified → the binary dimension is **SAFE**. If it cannot (no checksum, unsigned, mismatched source) → **REVIEW** at best, **BLOCK** if it looks tampered.

## `BUILD_FROM_SOURCE`

Prebuilt binaries are **not** trusted for this app. After the audit passes, the human should build and install from the reviewed source tree at the target tag. This skill surfaces the documented build steps from the app spec but **does not run them**.

A typical (illustrative) sequence the human would run after approval:

```bash
git clone <repo-url> /tmp/<app>-build && cd /tmp/<app>-build
git checkout <target-tag>
git verify-tag <target-tag>     # if the tag is GPG-signed
# ...project-specific build, e.g.:
<build command from the app spec>
<install command from the app spec>
```

Key points to surface to the human:

- Check out and verify the **exact reviewed tag** — not `main`/`HEAD`.
- Build commands come from the **app spec's Build steps** section; if absent, derive them from the repo's README/CONTRIBUTING and confirm with the user.
- Building from source means the resulting artifact corresponds to code you reviewed — no need to trust the provider's release pipeline.

## No spec available

Present the evidence and recommend, but let the human choose:

- Is the artifact signed / notarized / checksummed? → leans `TRUST_RELEASE_BINARY`.
- Is the release pipeline auditable and unchanged? → leans `TRUST_RELEASE_BINARY`.
- High-sensitivity tool, opaque or changed pipeline, no signatures? → leans `BUILD_FROM_SOURCE`.
