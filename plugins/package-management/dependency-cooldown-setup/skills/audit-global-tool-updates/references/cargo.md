# Cargo (Rust)

**Status:** Registry-side infrastructure stabilized in Cargo 1.94 (May 2026). Client-side implementation still pending.

**Config:** No global cooldown config yet — client-side implementation pending.

**Approach:** Opt-in per-package via `cargo update foo --precise 1.5.10`, which records the choice in the lockfile.

**Third-party tool:** [cargo-cooldown](https://github.com/) — wrapper that enforces a configurable cooldown window on developer machines (proof-of-concept).

**Global tool detection:**

```bash
# List all installed crates with versions
cargo install --list

# Check latest version of a specific crate
cargo search <crate>

# Get crate info for version comparison
cargo search <crate> --limit 1
```

**Update a global tool:**

```bash
cargo install <crate> --force
```
