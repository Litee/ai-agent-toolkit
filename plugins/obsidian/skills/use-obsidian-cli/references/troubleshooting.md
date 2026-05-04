# Troubleshooting

| Error | Cause | Solution |
|-------|-------|---------|
| `obsidian: command not found` | CLI not on PATH | Check `~/.zprofile`, restart terminal, or re-register CLI in Obsidian settings |
| `Failed to connect` | Obsidian not running | Launch Obsidian app, wait a few seconds, retry |
| `File not found` | Wrong file name or path | Use `obsidian files` to list files; try `path=` instead of `file=` for exact paths |
| `Vault not found` | Wrong vault name | Use `obsidian vaults` to list vault names |
| `Template not found` | Wrong template name | Use `obsidian templates` to list available templates |
| `File already exists` | Attempting to create existing file | Add `overwrite` flag or choose a different name |

### Retry and Escalation

The table above covers what each error means. Below is what to *do* when you hit one:

- **`Failed to connect` retry policy.** Retry at most 3 times with 2-second sleeps between attempts. Do NOT tight-loop: Obsidian's local server takes a few seconds to come up, and spamming the CLI will not speed that up.
- **`Failed to connect` after 3 retries.** Stop retrying. Launch or restart Obsidian manually (`open -a Obsidian` on macOS), wait 5-10 seconds, then retry one more time. If it still fails, assume the Obsidian app is wedged and escalate to the user — do NOT kill/restart the user's Obsidian process automatically; they may have unsaved work.
- **`obsidian: command not found`.** Do NOT retry — no retry will make the CLI appear on PATH. Verify with `command -v obsidian` and ask the user to re-register the CLI from Obsidian → Settings → Community Plugins → Obsidian Web Clipper / obsidian-cli, or restart their shell if they just registered it.
- **Fallback to filesystem tools when Obsidian cannot start.** If Obsidian is truly unreachable and the task only needs read-only access to markdown content, fall back to `rg`, `find`, and direct `.md` reads against the vault directory. Warn the user that **internal links, tags, backlinks, and properties will not update** — filesystem tools bypass Obsidian's index. Do NOT perform writes through filesystem tools if the vault has Obsidian Sync or Git integration enabled.
- **Mid-operation failures.** The CLI is not transactional across multi-step operations (e.g. batch `rename` of 50 files). If the CLI fails partway through, do NOT auto-retry the whole batch — some files were already renamed. List current state first (`obsidian files`) and resume from the last-known-good position.
- **Escalate to the user when:** Obsidian process is suspected crashed; vault is reported not-found but the path is correct; CLI version appears older than the plugin expects (upgrade the CLI); or the same error recurs after a retry cycle.
