---
name: skill-creator-extra-tips
description: Extra guidance for creating skills that work portably across machines and users. Trigger on "portable skill", "distribute skill", "package skill", "skill naming conventions", "hardcoded paths in skill", "validate skill structure", "skill for other users", "skill best practices", "skill guidelines", "skill quality", "what makes a good skill", "SKILL_DIR", "skill portability", "skill self-contained", "skill context management", "three-level loading", or when the skill-creator skill is active and the user mentions distribution, packaging, or portability.
---

# Skill Creator Extra Tips

Supplementary guidance for the `skill-creator` skill. Covers portability, naming conventions, context management, and automated tooling for distributable skills.

Invoke `skill-creator` first for core skill anatomy, the creation process, and progressive disclosure fundamentals. This skill adds guidance for skills that need to run reliably on any machine or for any user.

## Context Management

Skills use a three-level loading system to manage Claude's context efficiently:

1. **Level 1 - Metadata** (~100 words): Always loaded — name and description from YAML frontmatter
2. **Level 2 - SKILL.md body** (<5k words): Loaded when skill triggers — core instructions and workflow
3. **Level 3 - Bundled resources** (unlimited*): Loaded on-demand — detailed docs, examples, scripts

*Scripts can be executed without reading into context window, making them effectively "free" in terms of tokens.

**Design principle**: Keep frequently-needed instructions in SKILL.md; move reference material, detailed examples, and edge cases to bundled resources.

## File Naming Conventions

When creating skills, follow these naming conventions:

- **Skill directory names**: lowercase-with-hyphens (e.g., `ml-system-design-interviewer`, `podcast-script-generator`)
- **Reference files**: lowercase-with-hyphens, topic-based (e.g., `interviewer-guide.md`, `scoring-rubric.md`, `api-documentation.md`)
- **Script files**: snake_case for Python (e.g., `init_skill.py`, `rotate_pdf.py`), kebab-case for Bash
- **Asset files**: Use descriptive names matching their purpose (e.g., `logo.png`, `template.pptx`, `boilerplate.html`)

Clear, consistent naming makes resources discoverable and ensures Claude can reference them correctly.

## Best Practices for Skill Creation

- **Keep SKILL.md lean** — Focus on meta-instructions, links, and invocation guidance; move detailed references out of the file
- **Test progressive loading** — Verify that Claude pulls reference files only when the situation demands, preventing context overload
- **Use clear file naming** — Follow naming conventions above for consistency and discoverability
- **Avoid duplication** — Information should live in either SKILL.md or reference files, not both
- **Progressive disclosure hierarchy**: Metadata (~100 words) → SKILL.md (<5k words) → Bundled resources (unlimited)
- **Write for AI consumption** — Use imperative/infinitive form throughout; avoid second person
- **Reference contextually** — Include explicit instructions in SKILL.md about when Claude should load each reference file
- **Keep skills self-contained** — Never import code from another skill's `scripts/` directory. Each skill must bundle all code it needs. If two skills share logic, duplicate it or extract it into an independent library. Cross-skill imports create fragile coupling that breaks when either skill is updated, moved, or installed independently.

## The `${SKILL_DIR}` Placeholder

`${SKILL_DIR}` is a built-in variable that the Claude Code harness resolves at runtime to the absolute path of the skill's root directory. It is the **standard mechanism** for referencing a skill's own scripts, references, and assets from within SKILL.md.

**Rules:**
- All script invocations in SKILL.md **must** use `${SKILL_DIR}/scripts/<script_name>`:
  ```bash
  python3 ${SKILL_DIR}/scripts/init_skill.py <skill-name>
  ```
- All reference file paths in SKILL.md **must** use `${SKILL_DIR}/references/<filename>`:
  ```
  ${SKILL_DIR}/references/my-reference.md
  ```
- Never use `find`, relative paths (`./scripts/`), or hardcoded absolute paths to locate skill resources from SKILL.md.

**Scope:** `${SKILL_DIR}` is for SKILL.md only. Inside Python/Bash scripts, use runtime path discovery (`Path(__file__).parent`, `$(dirname "$0")`) as described in the Portability section below.

## Portability Best Practices

Skills are distributed to different users and executed on different machines. To ensure skills work reliably across environments, follow these guidelines when creating scripts and terminal commands:

### Never Hardcode User-Specific or Machine-Specific Paths

**AVOID:**
- Absolute paths with usernames: `/Users/johndoe/workspace/`, `/home/johndoe/projects/`
- Machine-specific paths: `/Volumes/MyDrive/`, `C:\Users\SpecificUser\`
- Hardcoded home directory paths: `/Users/johndoe/.aws/credentials`

**INSTEAD USE:**
- Home directory variables: `~/.aws/credentials`, `$HOME/.aws/credentials`, `os.path.expanduser("~")`
- Relative paths for skill-internal resources within scripts: `./references/schema.md`, `../assets/template.html` (in SKILL.md, always use `${SKILL_DIR}` instead)
- Environment variables: `$WORKSPACE_ROOT`, `$PROJECT_DIR`
- Runtime path discovery: Use `__file__` or `os.path.dirname()` to locate skill resources relative to the script

### Examples of Good vs Bad Path Handling

**BAD — Hardcoded user paths:**
```python
# Don't do this - breaks on other machines
config_file = "/Users/johndoe/.config/app/settings.json"
script_dir = "/home/johndoe/skills/my-skill/scripts/"
```

**GOOD — Portable paths:**
```python
import os
from pathlib import Path

# Use home directory expansion
config_file = os.path.expanduser("~/.config/app/settings.json")

# Or use pathlib
config_file = Path.home() / ".config" / "app" / "settings.json"

# Discover skill location relative to script
script_dir = Path(__file__).parent
skill_root = script_dir.parent
references_dir = skill_root / "references"
```

**BAD — Hardcoded workspace paths:**
```bash
# Don't do this - assumes specific directory structure
cd /Users/johndoe/workspace/myproject
aws s3 ls s3://bucket/
```

**GOOD — Use current working directory or relative paths:**
```bash
# Work from current directory or use relative paths
cd "$(dirname "$0")/.." || exit
aws s3 ls s3://bucket/
```

### Credential Management

When skills interact with cloud services (AWS, GCP, Azure) or APIs:

**AVOID:**
- Hardcoded credential paths: `--profile /Users/johndoe/.aws/credentials`
- Embedded credentials in scripts
- Assuming specific credential locations

**INSTEAD USE:**
- Default credential chains: Let boto3, AWS CLI, or cloud SDKs use their standard credential discovery
- Environment variables: `AWS_PROFILE`, `AWS_REGION`, `GOOGLE_APPLICATION_CREDENTIALS`
- Named profiles without paths: `aws s3 ls --profile myprofile` (not `--profile /path/to/credentials`)

### Cross-Platform Considerations

When skills may run on different operating systems:

- Use `os.path.join()` or `pathlib.Path` instead of hardcoded path separators (`/` or `\`)
- Check for required tools before using them: `which aws || echo "AWS CLI not found"`
- Use platform-agnostic commands when possible
- Document platform-specific requirements in SKILL.md dependencies

### Runtime Skill Resource Discovery

To reliably locate skill resources (scripts, references, assets) at runtime:

**Python example:**
```python
from pathlib import Path

# Get the skill root directory from any script in scripts/
skill_root = Path(__file__).parent.parent
references_dir = skill_root / "references"
assets_dir = skill_root / "assets"

# Read a reference file
schema_file = references_dir / "schema.md"
with open(schema_file, 'r') as f:
    schema_content = f.read()
```

**Bash example:**
```bash
#!/bin/bash
# Get skill root directory from script location
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REFERENCES_DIR="$SKILL_ROOT/references"

# Read a reference file
cat "$REFERENCES_DIR/schema.md"
```

Following these portability practices ensures skills work correctly regardless of who uses them or where they're installed.

## Automated Tooling

The primary `skill-creator` skill includes Python scripts for initializing and packaging distributable skills. These are orchestration-level tools, not shared library code — invoking another skill's scripts via the CLI is not a violation of the self-containment rule (which prohibits Python-level imports between skills).

To use them: invoke `skill-creator` first to load it. Once `skill-creator` is the active skill, its `${SKILL_DIR}` resolves to that skill's own root, making its scripts accessible:

- **`init_skill.py`** — Scaffolds a new skill directory from template with SKILL.md, scripts/, references/, and assets/
- **`package_skill.py`** — Validates and packages a skill into a distributable ZIP file
- **`quick_validate.py`** — Validates SKILL.md frontmatter, naming conventions, and checks for hardcoded paths

Do not use `find` to locate skill scripts — rely on `${SKILL_DIR}` resolution within the active skill's context.

## Gotchas

- Always invoke `skill-creator` first for core skill anatomy before using this skill for portability and packaging guidance.
- Hardcoded paths (e.g., `/Users/yourname/`) make skills non-portable — use `${SKILL_DIR}` in SKILL.md and runtime path discovery (`__file__`, `$(dirname "$0")`) in scripts.
