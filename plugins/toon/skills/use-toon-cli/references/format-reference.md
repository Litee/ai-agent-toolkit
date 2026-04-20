# TOON Format Reference

TOON (Token-Oriented Object Notation), spec version 3.0 (2025-11-24). Author: Johann Schopplich. License: MIT.

- **File extension:** `.toon`
- **Media type:** `text/toon` (provisional)
- **Encoding:** UTF-8, LF line endings

---

## Data Model

TOON encodes the exact same data model as JSON — lossless round-trips in both directions:

| Type | JSON example | TOON example |
|------|-------------|-------------|
| String | `"Ada"` | `Ada` (unquoted if safe) |
| Number | `42` | `42` |
| Boolean | `true` / `false` | `true` / `false` |
| Null | `null` | `null` |
| Object | `{"k": "v"}` | `k: v` |
| Array | `[1, 2]` | Inline or block form |

---

## Object Syntax

Primitive fields: `key: value` (single space after colon).

Nested objects: `key:` on its own line with children indented one level deeper.

```toon
id: 123
name: Ada
active: true
address:
  city: Boulder
  state: CO
```

---

## Primitive Arrays (Inline)

`key[N]: v1,v2,...` — `N` is the exact element count.

```toon
tags[3]: admin,ops,dev
empty[0]:
```

---

## Tabular Arrays (Sweet Spot)

When all array elements are objects with **the same keys** and **all primitive values**, use tabular form. Field names are declared once; rows follow indented.

```toon
users[2]{id,name,role}:
  1,Alice,admin
  2,Bob,user
```

Equivalent JSON:
```json
{"users": [{"id": 1, "name": "Alice", "role": "admin"}, {"id": 2, "name": "Bob", "role": "user"}]}
```

Tabular eligibility is all-or-nothing per array: a single element with a nested structure, missing key, or extra key forces the entire array into expanded list form.

---

## Mixed / Non-Uniform Arrays (Expanded List)

When tabular requirements are not met, each element is a list item with `- ` prefix.

```toon
items[3]:
  - 1
  - a: 1
  - text
```

Object list items: first field on the hyphen line, remaining fields indented:

```toon
items[2]:
  - id: 1
    name: First
  - id: 2
    name: Second
```

---

## Arrays of Arrays

```toon
pairs[2]:
  - [2]: 1,2
  - [2]: 3,4
```

---

## Delimiter Variants

Three supported delimiters, declared inside the bracket segment of the header:

| Delimiter | Header syntax | Row example |
|-----------|--------------|-------------|
| Comma (default) | `[N]` or `[N]{fields}` | `1,Alice,admin` |
| Tab | `[N\t]` or `[N\t]{fields}` | `1\tAlice\tadmin` |
| Pipe | `[N\|]` or `[N\|]{fields}` | `1\|Alice\|admin` |

The delimiter declared in the bracket **must** match all rows within that array scope. Delimiter selection does **not** inherit from parent arrays — absence of a delimiter symbol always means comma.

---

## String Quoting Rules

Strings **must** be double-quoted if any of the following applies:

- Empty string (`""`)
- Leading or trailing whitespace
- Value equals `true`, `false`, or `null`
- Looks numeric (matches standard number patterns, or has leading zeros like `05`)
- Contains `:`, `"`, `\`, `[`, `]`, `{`, `}`
- Contains the active delimiter character
- Contains control characters (newline, carriage return, tab)
- Equals `"-"` or starts with a hyphen (`-`)

Otherwise, strings are emitted **unquoted**. Unicode, emoji, and internal spaces are safe unquoted.

---

## Escape Sequences

Only five escape sequences are valid inside double-quoted strings:

| Sequence | Meaning |
|----------|---------|
| `\\` | Backslash |
| `\"` | Double quote |
| `\n` | Newline |
| `\r` | Carriage return |
| `\t` | Tab |

Any other `\x` sequence is a hard error — rejected in strict mode and malformed.

No `\uXXXX` unicode escapes.

---

## Key Encoding

Object keys may be **unquoted** only if they match `^[A-Za-z_][A-Za-z0-9_.]*$`. Otherwise they must be double-quoted:

```toon
"my-key": value
"x-items"[2]{id,name}:
  1,Ada
  2,Bob
```

---

## Number Canonicalization

Encoders must emit numbers in canonical decimal form:

- No exponent notation (`1e6` → `1000000`)
- No leading zeros (`05` is invalid)
- No trailing fractional zeros (`1.5000` → `1.5`)
- Zero fractional part emits as integer (`1.0` → `1`)
- `-0` normalizes to `0`
- `NaN`, `Infinity`, `-Infinity` normalize to `null`

---

## Key Folding and Path Expansion

**Key folding** (encode, `--keyFolding safe`): Collapses chains of single-key nested objects into dotted paths.

```
{"a": {"b": {"c": 1}}}  →  a.b.c: 1
```

`--flattenDepth <n>` caps the number of dotted segments. Folding is skipped if it would produce a key that collides with an existing sibling literal key.

**Path expansion** (decode, `--expandPaths safe`): Splits dotted keys into nested objects using deep-merge semantics. By default, `a.b.c: 1` decodes to `{"a.b.c": 1}` (literal key).

---

## Indentation

- Default: 2 spaces per level (configurable with `--indent`)
- Tabs are **never** allowed for indentation
- No trailing spaces on any line
- No trailing newline at end of document

---

## Strict Mode

Strict mode is **on by default**. Disable with `--no-strict`.

In strict mode, the following cause hard errors:

- Array element count does not match declared `[N]`
- Tabular row field count does not match declared field list
- Indentation is not an exact multiple of the indent size
- Tabs used for indentation
- Blank lines inside arrays
- Invalid escape sequences
- Unterminated strings
- Missing colon after a key
- Path expansion conflicts (when `--expandPaths safe` is enabled)

---

## Other Constraints

- **No comments** — TOON has no comment syntax (unlike YAML or JSON5)
- **No trailing newline** — encoders must not emit a trailing newline; decoders accept one tolerantly
- **Blank lines outside arrays** — ignored by decoders
- **Blank lines inside arrays** — error in strict mode

---

## Benchmarks

Across 209 retrieval questions on 4 LLMs (Claude Haiku 4.5, Gemini 3 Flash, GPT-5 Nano, Grok 4.1 Fast):

| Format | Accuracy | Tokens (relative) | Efficiency (acc%/1K tokens) |
|--------|----------|-----------------|---------------------------|
| TOON | 76.4% | −39.9% vs JSON | 27.7 |
| JSON compact | 75.0% | baseline | 23.7 |
| YAML | ~74% | +~10% vs JSON | 19.9 |
| JSON | ~74% | +~50% vs JSON compact | 16.4 |
| XML | ~73% | +~100% vs JSON compact | 13.8 |

TOON achieves best results for uniform arrays of objects. For deeply nested or non-uniform data, JSON compact may be smaller.
