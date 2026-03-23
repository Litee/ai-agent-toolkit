## Agentic Instructions

- You MUST review `README.md` and `.claude-plugin/marketplace.json` files and keep them up to date whenever adding/removing/modifying a skill.
- You MUST bump up plugin version in `.claude-plugin/marketplace.json` after making changes in the skill. By default, bumpt patch part of the version, e.g. "1.0.0" -> "1.0.1".
- You MUST keep skills alphabetically sorted inside `README.md`.
- You MUST activate Python virtual environment at `.venv` to test Python scripts.
- You MUST use a git worktree for all changes. Create one with `git worktree add .worktrees/<branch-name> -b <branch-name>`, make all changes inside it, and keep the main repo clean.
