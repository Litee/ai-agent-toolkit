# Troubleshooting

Cache-cleanup operations are intentionally best-effort: the script continues on per-target failures and reports a summary at the end. Notable failure modes:

| Scenario | Cause | Handling |
|----------|-------|----------|
| `docker system prune` fails with `Cannot connect to the Docker daemon` | Docker Desktop is not running | The script logs a warning and skips the `docker` target. Start Docker Desktop (or accept that the target is skipped on headless machines) and re-run with `--apply --target docker` for just that stage. Do NOT auto-start Docker — it is a heavyweight app and the user may have stopped it intentionally. |
| `brew cleanup` fails with `Another active Homebrew update process is already in progress` | A concurrent `brew` invocation is holding the Homebrew lock | Do NOT `kill` the other process. Wait for it to complete (typically seconds to a minute) and re-run with `--target brew`. If the lock is stale (no active `brew` process), `rm /opt/homebrew/var/homebrew/locks/update` is safe. |
| `pip cache purge` or `npm cache clean` returns non-zero | Tool is not installed on the machine | The script logs and skips. Safe to ignore — the missing tool simply has no cache to clean. |
| Script interrupted mid-deletion (Ctrl-C, SIGTERM) | User-initiated or OS-level | **Re-running is safe.** All cache directories are regenerated on next tool invocation (`npm install`, `brew update`, etc.). A partially-deleted cache is functionally identical to an empty cache. Do NOT attempt to restore the interrupted state. |
| `Permission denied` on a cache path | Cache owned by a different user (common in shared CI runners) | Script logs and skips. Fix ownership with `sudo chown -R $USER <path>` if deliberate, or just accept the skip. |
| Disk full *during* cleanup | The scan itself allocates little; deletions free space | Unusual — if it happens, re-run: the first pass freed what it could before running out of inodes, and the second pass typically succeeds. Check `df -i` for inode exhaustion separately from byte-level `df -h`. |

**Escalation path:** if the summary reports `0 bytes freed` after `--apply` despite the dry-run showing reclaimable space, the most common cause is permission issues — inspect the per-target log lines. If the user is on a managed corporate machine (MDM), some cache paths may be locked by endpoint-security agents; escalate to the user rather than attempting to bypass.
