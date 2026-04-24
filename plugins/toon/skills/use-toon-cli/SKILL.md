---
name: use-toon-cli
description: Use when encoding JSON to TOON, decoding TOON to JSON, reducing LLM token usage by compacting data, measuring token savings with --stats, or working with .toon files. TOON (Token-Oriented Object Notation) is a compact human-readable format designed as a translation layer for LLM input.
---

# TOON CLI

TOON (Token-Oriented Object Notation) is a compact, human-readable text format that encodes the exact same data model as JSON with significantly fewer tokens. It is designed as a translation layer for LLM input — encode data as TOON for efficient LLM consumption, decode back to JSON when needed. Round-trips are lossless.

For the complete flag reference, read `${SKILL_DIR}/references/cli-reference.md`.
For the full format specification, read `${SKILL_DIR}/references/format-reference.md`.

---

## Prerequisites

Verify toon is installed:

```bash
which toon
toon --version
```

If not found, install it:

```bash
npm install -g @toon-format/cli
# or
pnpm add -g @toon-format/cli
```

Run without installing:

```bash
npx @toon-format/cli [options] [input]
```

---

## Quick Start

```bash
# Encode a JSON file to TOON (auto-detected from .json extension)
toon data.json

# Encode and save to file
toon data.json -o data.toon

# Decode a TOON file to JSON (auto-detected from .toon extension)
toon data.toon

# Encode from stdin (default for piped input)
echo '{"name": "Ada", "age": 30}' | toon

# Encode and show token savings
toon data.json --stats
```

---

## Encoding JSON to TOON

```bash
# From file (auto-detected)
toon input.json -o output.toon

# From stdin
cat data.json | toon
cat data.json | toon -o output.toon

# Pipe from curl
curl -s https://api.example.com/data | toon

# Force encode (override auto-detection)
toon --encode ambiguous-file -o output.toon
```

---

## Decoding TOON to JSON

```bash
# From file (auto-detected)
toon input.toon -o output.json

# From stdin (must specify --decode; stdin defaults to encode)
cat data.toon | toon --decode
cat data.toon | toon -d -o output.json

# Force decode
toon --decode ambiguous-file -o output.json
```

---

## Token Statistics

The `--stats` flag prints token count estimates and savings to stderr during encoding:

```bash
toon data.json --stats
# Stderr: Saved ~6,400 tokens (-42.3%)

toon data.json --stats -o output.toon
```

`--stats` is encode-only and **disables streaming** — the full output is kept in memory for counting. For very large files, omit `--stats` to preserve streaming behavior.

---

## Delimiter Selection

The default delimiter is comma. Use `--delimiter` to switch:

```bash
# Tab-delimited (often better for human readability)
toon data.json --delimiter $'\t' -o output.toon

# Pipe-delimited (when data fields contain commas)
toon data.json --delimiter '|' -o output.toon
```

| Delimiter | Flag value | Best for |
|-----------|-----------|---------|
| Comma (default) | `,` | Most cases; most compact |
| Tab | `$'\t'` | Tabular data for human reading |
| Pipe | `\|` | Data with embedded commas |

The delimiter declared in the TOON header must match all rows in that array scope. Delimiter selection does not inherit from parent arrays.

---

## Key Folding and Path Expansion

**Key folding** (encode): Collapses chains of single-key nested objects into dotted paths — reduces indentation overhead for deeply nested data.

```bash
# Input: {"a": {"b": {"c": 1}}}
toon input.json --keyFolding safe
# Output: a.b.c: 1

# Limit folding depth
toon input.json --keyFolding safe --flattenDepth 2
```

**Path expansion** (decode): Reverses folding — splits dotted keys back into nested objects using deep-merge.

```bash
cat compressed.toon | toon --decode --expandPaths safe
```

`--expandPaths safe` **disables streaming** on decode.

**Round-trip with folding:**

```bash
toon input.json --keyFolding safe -o compressed.toon
toon compressed.toon --expandPaths safe -o output.json
```

Without `--expandPaths safe`, `a.b.c: 1` decodes to `{"a.b.c": 1}` (literal dotted key), not nested objects.

---

## Indentation and Strict Mode

```bash
# Custom indentation (default is 2 spaces)
toon data.json --indent 4 -o output.toon

# Lenient decoding (accepts count mismatches, indentation errors)
cat data.toon | toon --decode --no-strict
```

Strict mode is on by default. It enforces exact element counts, correct indentation, no blank lines inside arrays, and valid escape sequences. Use `--no-strict` only when decoding TOON from an external source of unknown quality.

---

## Streaming and Memory

By default, encoding streams lines and decoding streams JSON tokens. Peak memory scales with data **depth**, not total size — suitable for large files.

Two flags disable streaming:

| Flag | Why streaming is disabled |
|------|--------------------------|
| `--stats` | Full output buffered for token counting |
| `--expandPaths safe` | Full structure needed for deep-merge |

For large files (e.g., millions of records), avoid these two flags:

```bash
# Large-file encode (streaming)
cat large.json | toon > large.toon

# Large-file decode (streaming)
cat large.toon | toon --decode > large.json
```

---

## Integration Patterns

```bash
# Filter with jq then encode
jq '.results' data.json | toon

# API response directly to TOON
curl -s https://api.example.com/users | toon --stats

# Batch convert all JSON files in a directory
for f in *.json; do toon "$f" -o "${f%.json}.toon"; done

# Encode for LLM context: pipe into clipboard or file
jq '.items' response.json | toon | pbcopy

# Chain encode + decode (round-trip verification)
cat data.json | toon | toon --decode
```

---

## Format Quick Reference

Objects use YAML-like `key: value` syntax with indentation for nesting:

```toon
name: Ada
address:
  city: Boulder
  state: CO
```

Primitive arrays: `key[N]: v1,v2,...`

Tabular arrays (uniform objects — the sweet spot):
```toon
users[2]{id,name,role}:
  1,Alice,admin
  2,Bob,user
```

Mixed arrays (non-uniform):
```toon
items[2]:
  - id: 1
    name: First
  - id: 2
    name: Second
```

**String quoting** — required if: empty, leading/trailing whitespace, boolean-like (`true`/`false`/`null`), numeric-looking, or contains `:`, `"`, `\`, brackets, the active delimiter, or control characters.

**Escapes** — only 5: `\\`, `\"`, `\n`, `\r`, `\t`. No `\uXXXX`.

**No comments. No trailing newline.**

---

## When to Use This Skill

**Use when:**
- Encoding JSON data to reduce token count before feeding to an LLM
- Decoding TOON files back to JSON for programmatic processing
- Measuring token savings with `--stats` to decide if TOON is worth it for a dataset
- Data consists of uniform arrays of objects (same fields, primitive values) — the highest-savings case
- Piping API responses through `toon` as part of an LLM context assembly pipeline

**Do NOT use when:**
- The consuming tool expects JSON — decode first
- Data is deeply nested and non-uniform (JSON compact may be smaller; TOON adds overhead for irregular shapes)
- Binary or non-JSON input
- The round-trip fidelity matters and numbers like `1e6` or `-0` need to be preserved exactly (TOON canonicalizes these)

---

## CLI Reference

For the complete flag reference with all options and defaults, read `${SKILL_DIR}/references/cli-reference.md`.

For the full TOON format specification including quoting rules, escape sequences, delimiter semantics, and benchmarks, read `${SKILL_DIR}/references/format-reference.md`.
