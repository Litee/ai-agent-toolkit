# Troubleshooting

All workflows in this skill are issued through the `obsidian` CLI. When CLI calls fail:

- **Common errors (vault not found, `Failed to connect`, `File already exists`, etc.)** are documented in the Error Handling section of the `obsidian:use-obsidian-cli` skill, along with the retry and escalation policy (max 3 retries at 2s intervals, fallback to filesystem tools for read-only tasks, when to escalate to the user). Read that section first — do not duplicate its guidance here.
- **PKM-specific fallback:** if the Obsidian app cannot be reached and the current task is read-only (gap analysis, orphan count, link suggestions), fall back to `rg` / `find` on the vault directory. Explicitly warn the user that the filesystem view does not reflect in-flight Obsidian state (unsaved edits, plugin-driven transforms).
- **Never write to the vault via filesystem tools as an unattended recovery.** Writes must go through the CLI so that Obsidian's link index, frontmatter parser, and Sync/Git integrations stay consistent. If the CLI cannot be reached for a write, escalate to the user and stop — do not invent a workaround.
- **Mid-workflow failures.** Workflows in this skill (card creation, daily-note capture, bulk-update) are multi-step. If a step fails, do NOT restart the workflow from scratch — list current state (`obsidian files`, `obsidian properties`) and resume from the last-known-good step.
