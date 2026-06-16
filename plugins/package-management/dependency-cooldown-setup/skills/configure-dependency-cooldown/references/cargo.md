# Cargo (Rust)

**Status:** Registry-side infrastructure stabilized in Cargo 1.94 (May 2026). Client-side implementation still pending.

**Approach:** Opt-in per-package via `cargo update foo --precise 1.5.10`, which records the choice in the lockfile. No exclude list needed — you explicitly opt into newer versions.

**Third-party tool:** [cargo-cooldown](https://github.com/) — a wrapper that enforces a configurable cooldown window on developer machines (proof-of-concept).

**Notes:**
- Cargo's approach sidesteps the exemption list problem entirely.
- No global config available yet — client-side implementation is still pending.
