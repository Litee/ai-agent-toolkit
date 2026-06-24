# General Rules

- You MUST use `/tmp` directory for all discardable files you create. You MUST NOT pollute the current workspace with temporary files.
- You SHOULD use non-interactive flags (e.g. `--yes`, `--no-input`, `-y`) to prevent commands from hanging on prompts.
- You SHOULD use sub-agents for independent tasks that involve multiple steps or significant context. Do not spawn sub-agents for trivial single-step operations.
- When redirecting output to files with `>`, you MUST use `>|` instead to handle zsh noclobber. If you get `(eval):1: file exists` errors, this is the fix.
- Answer only what was asked and only what you actually know. Do NOT volunteer recommendations or conclusions that exceed your knowledge of the situation. Knowing one facet (e.g. your own processes, your own access, your own changes) does not qualify you to advise on the whole.
- You MUST NOT kill processes by OS mechanisms unless you are 100% confident that you won't impact some other parallel session that might be using same tools.
