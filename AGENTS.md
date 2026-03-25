## Agentic Instructions

### Skill Maintenance

- You MUST review `README.md` and `.claude-plugin/marketplace.json` files and keep them up to date whenever adding/removing/modifying a skill.
- You MUST bump up plugin version in `.claude-plugin/marketplace.json` after making changes in the skill. By default, bump the patch part of the version, e.g. "1.0.0" -> "1.0.1".
- You MUST keep skills alphabetically sorted inside `README.md`.
- You MUST activate Python virtual environment at `.venv` to test Python scripts.

### Issue Fixing Workflow

When fixing skill issues from the issue tracker:

- **Each issue gets its own worktree**, named after the issue (e.g. `fix-use-cmux-0008`). Exception: closely related issues that touch the same file(s) and would produce a coherent single commit may share one worktree.
- **Use sub-agents** to fix issues in parallel. Dispatch one sub-agent per worktree so the main session stays uncluttered and independent issues are worked on concurrently.
- **Mark an issue `done` only after its fix is merged into `main`.** Do NOT set status to `done` when a fix is committed to a worktree branch — only after the branch is successfully merged.

### Git Workflow

All changes follow this sequence — do not skip or reorder steps:

1. **Create a worktree**: `git worktree add .claude/worktrees/<branch-name> -b <branch-name>`. Make all changes inside it; keep the main repo clean.
2. **Implement and test** changes inside the worktree.
3. **Present changes** to the user for review. Do NOT commit yet.
4. **Commit only after** the user has reviewed the worktree diff and explicitly confirmed it is OK. Do not commit speculatively or "to save progress" — the user's explicit confirmation is required.
5. **Rebase onto `main`**: from inside the worktree, run `git rebase origin/main` to keep history linear.
6. **Merge with fast-forward only**: from the main repo, run `git merge --ff-only`. Never create merge commits.
7. **Ask for explicit confirmation** before merging any worktree branch into `main`.
