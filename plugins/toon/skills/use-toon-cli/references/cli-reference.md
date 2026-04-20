# TOON CLI Reference

Complete command and flag reference for `toon` (v2.1.0). Requires Node.js.

## General Syntax

```
toon [options] [input]
```

- Omit `input` or pass `-` to read from stdin
- Output goes to stdout unless `-o` is specified

## Auto-Detection Logic

| Input source | Extension | Default mode |
|---|---|---|
| File argument | `.json` | Encode (JSON → TOON) |
| File argument | `.toon` | Decode (TOON → JSON) |
| Stdin | — | Encode (JSON → TOON) |
| Stdin | — | Decode with `--decode` |

Use `-e`/`--encode` or `-d`/`--decode` to override auto-detection.

---

## All Flags

| Flag | Default | Description |
|------|---------|-------------|
| `-o, --output <file>` | stdout | Write output to file instead of stdout |
| `-e, --encode` | auto | Force encode mode (JSON → TOON) |
| `-d, --decode` | auto | Force decode mode (TOON → JSON) |
| `--delimiter <char>` | `,` | Array delimiter: `,` (comma), `\t` (tab), `\|` (pipe) |
| `--indent <number>` | `2` | Indentation size (spaces) |
| `--stats` | off | Print token count estimates and savings to stderr (encode only; disables streaming) |
| `--no-strict` | off | Disable strict validation when decoding |
| `--keyFolding <mode>` | `off` | Key folding: `off` or `safe` (collapses single-key chains into dotted paths) |
| `--flattenDepth <number>` | Infinity | Max dotted-path segment count when `--keyFolding safe` is set |
| `--expandPaths <mode>` | `off` | Path expansion on decode: `off` or `safe` (splits dotted keys into nested objects; disables streaming) |
| `--version` | | Print version and exit |
| `--help` | | Print help and exit |

---

## Streaming Behavior

| Mode | Streams? | Notes |
|------|----------|-------|
| Encode (default) | Yes | Lines streamed as they are produced |
| Decode (default) | Yes | JSON tokens streamed as they are parsed |
| Encode `--stats` | No | Full output buffered for token counting |
| Decode `--expandPaths safe` | No | Full structure needed for deep-merge |

For large files, prefer the default streaming behavior and avoid `--stats` and `--expandPaths safe`.

---

## Delimiter Details

| Value | Flag | Header syntax | Use case |
|-------|------|---------------|----------|
| Comma | `--delimiter ','` (default) | `[N]` | Most compact, default |
| Tab | `--delimiter $'\t'` | `[N\t]` | Human-readable tabular data |
| Pipe | `--delimiter '\|'` | `[N\|]` | Data fields that may contain commas |

The delimiter declared in the array header must match the delimiter used in all rows within that array scope. Delimiter selection does **not** inherit from parent arrays.

---

## Key Folding / Path Expansion

**Key folding** (`--keyFolding safe`): Collapses chains of single-key nested objects into dotted paths during encode.

```
Input:  {"a": {"b": {"c": 1}}}
Output: a.b.c: 1
```

`--flattenDepth <n>` caps the number of segments folded. For example, `--flattenDepth 2` folds `a.b` but not `a.b.c`.

**Path expansion** (`--expandPaths safe`): Reverses folding on decode — splits dotted keys into nested objects using deep-merge semantics. Disables streaming.

**Round-trip example:**
```bash
toon input.json --keyFolding safe -o compressed.toon
toon compressed.toon --expandPaths safe -o output.json
```

Folding is skipped silently if the resulting dotted key would collide with an existing sibling literal key at the same depth.

---

## npm Packages

| Package | Purpose |
|---------|---------|
| `@toon-format/cli` | CLI tool (`toon` binary) |
| `@toon-format/toon` | TypeScript/JavaScript library (encode/decode API) |

Install CLI globally:
```bash
npm install -g @toon-format/cli
# or
pnpm add -g @toon-format/cli
```

Run without installing:
```bash
npx @toon-format/cli [options] [input]
```
