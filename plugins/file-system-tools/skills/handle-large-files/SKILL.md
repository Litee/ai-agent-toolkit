---
name: handle-large-files
description: "Use when reading, analyzing, or processing a file that may exceed the context window. Triggers on 'large file', 'too many lines', 'file is too big', 'analyze this log', 'parse this JSON', 'extract from CSV', 'token estimate', or any situation where the agent encounters a file too large to read whole. For disk space cleanup use file-system-tools:free-disk-space."
---

# handle-large-files

Techniques for safely analyzing and extracting from large files without exceeding the context window. Never read a large file whole — target exactly what you need.

---

## The Size Check

Before reading any file, assess its size. This determines everything else.

```bash
# Lines (fastest)
wc -l file.txt

# Size in bytes/KB/MB
stat -f "%z bytes / %k KB" file.txt        # macOS
stat -c "%s bytes" file.txt                # Linux

# Rough token estimate (size_bytes / 4)
python3 -c "import os; s=os.path.getsize('file.txt'); print(f'~{s//4:,} tokens ({s/1024:.1f} KB)')"
```

**Decision thresholds:**

| Lines | Action |
|-------|--------|
| < 300 | Safe to read directly |
| 300–1000 | Selective reading — use offsets or targeted extraction |
| > 1000 | Never read whole — use targeted extraction only |
| Unknown | Always check first with `wc -l` |

**If a previous read was truncated:** do not re-read. Switch immediately to targeted extraction commands — re-reading produces the same truncation.

---

## Strategy Selection

Choose the technique based on what you are trying to accomplish:

| Goal | Technique |
|------|-----------|
| Understand structure | Read first/last 20-50 lines; extract headers or keys |
| Find specific content | `grep` with context lines; `sed` for line ranges |
| Count or quantify | `grep -c`; pattern counting one-liners |
| Extract specific data | JSON field extraction; CSV column extraction; regex |
| Analyze code structure | AST analysis; function/class listing |
| Estimate cost of reading | Token estimation before deciding whether to read |

**Language preference:**
- **Bash** first — for simple extraction (`head`, `tail`, `grep`, `sed`, `wc`). Zero startup cost.
- **Python** for structured data (JSON, CSV, XML, AST) or complex patterns.
- **Node.js** when working in a JS/TS codebase and the runtime is confirmed available.
- **PowerShell** only on Windows without a Unix shell.

---

## Quick Reference

### Peek at File Content

```bash
# First/last N lines
head -n 20 file.txt
tail -n 20 file.txt

# Specific line range
sed -n '100,120p' file.txt
```

```python
# First N lines with line numbers
python3 -c "with open('file.txt') as f: [print(f'{i+1}: {l.strip()}') for i,l in enumerate(f) if i<50]"
```

### Count and Search

```bash
# Count matching lines
grep -c "ERROR" log.txt

# Lines matching pattern, with context
grep -A 3 -B 2 "Exception" log.txt

# Count lines total
wc -l file.txt
```

```python
# Count pattern occurrences
python3 -c "import re; print(len(re.findall(r'ERROR', open('log.txt').read())))"

# Find duplicate lines (top 5)
python3 -c "from collections import Counter; print(Counter(open('file.txt').read().splitlines()).most_common(5))"
```

### Structured Data Extraction

```bash
# CSV: count fields
csv_fields() { head -1 "$1" | tr ',' '\n' | wc -l; }
```

```python
# JSON: extract specific field without loading whole file
python3 -c "import json; print(json.load(open('large.json'))['key']['subkey'])"

# Extract email addresses
python3 -c "import re; print(set(re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', open('contacts.txt').read())))"
```

```javascript
// Node.js: extract JSON property
node -e "const fs=require('fs');const data=JSON.parse(fs.readFileSync('config.json'));console.log(data.property)"
```

### Code Structure Analysis

```python
# List all classes and functions in a Python file
python3 -c "
import ast
with open('module.py') as f: tree = ast.parse(f.read())
classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
print('Classes:', classes); print('Functions:', funcs[:20])
"

# Find methods on a suspected god class
python3 -c "import re; methods=re.findall(r'def\s+([^\(]+)\(self', open('module.py').read()); print(f'{len(methods)} methods:', methods[:10])"
```

```bash
# Extract Markdown headers (structure overview)
grep -E "^#{1,6} " README.md

# Find largest files in a directory tree
find . -type f -exec stat -f "%z %N" {} \; | sort -nr | head -10   # macOS
find . -type f -exec stat -c "%s %n" {} \; | sort -nr | head -10   # Linux
```

### File Metadata

```python
# Token estimate
python3 -c "import os; s=os.path.getsize('file.txt'); sample=open('file.txt','r',errors='ignore').read(50000); print({'tokens_approx': int(len(sample)//4 * (s/max(len(sample),1))), 'size_mb': round(s/1048576,2)})"
```

---

## Multi-Step Analysis Patterns

Use these when a single one-liner is not enough.

### JSON Structure Probe

**When:** You have a large JSON file and need to understand its shape before extracting fields.

```python
def analyze_json(path):
    import json, os
    with open(path, 'rb') as f:
        sample = f.read(1000).decode('utf-8', 'replace')
    structure = 'object' if sample.strip().startswith('{') else 'array' if sample.strip().startswith('[') else 'unknown'
    keys = set(k for k in sample.split('"') if ':' in sample.split(k)[1][:5]) if structure == 'object' else []
    return {'size_mb': round(os.path.getsize(path)/1048576, 2), 'structure': structure, 'top_keys': list(keys)[:10]}

print(analyze_json('data.json'))
```

### Log Triage

**When:** You need to assess severity distribution in a log file before digging in.

```python
def triage_log(path):
    import os
    sample = open(path, 'r', errors='ignore').read(10000)
    counts = {level: sample.count(level) for level in ['ERROR', 'WARN', 'INFO', 'DEBUG']}
    size_mb = round(os.path.getsize(path)/1048576, 2)
    return {'counts': counts, 'size_mb': size_mb, 'lines_sampled': sample.count('\n')}

print(triage_log('app.log'))
```

Use the output to decide whether to run `grep -A 3 "ERROR"` for error context next.

### CSV Profile

**When:** You need to understand column structure and data types before extracting.

```python
def profile_csv(path):
    import csv
    with open(path, 'r') as f:
        reader = csv.reader(f)
        headers = next(reader)
        rows = [row for _, row in zip(range(100), reader)]
    types = ['numeric' if all(c.replace('.','',1).isdigit() for c in [r[i] for r in rows if i < len(r) and r[i]]) else 'text' for i in range(len(headers))]
    samples = [[r[i] for r in rows if i < len(r) and r[i]][:3] for i in range(len(headers))]
    return {'headers': headers, 'types': dict(zip(headers, types)), 'samples': dict(zip(headers, samples)), 'rows_sampled': len(rows)}

print(profile_csv('data.csv'))
```

### Codebase Reconnaissance

**When:** Exploring an unfamiliar codebase before deciding what to read.

```bash
# Count lines per file type, sorted
find . -type f | grep -E '\.(py|js|ts|java|go)$' | xargs wc -l 2>/dev/null | sort -nr | head -20

# Extract all Markdown headers across the project
find . -name "*.md" -type f | while read f; do echo "=== $f ==="; grep -E "^#{1,6} " "$f"; done
```

```python
# Find largest Python files and their class/function counts
import os, ast
results = []
for root, _, files in os.walk('.'):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            try:
                tree = ast.parse(open(path).read())
                classes = sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
                funcs = sum(1 for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
                results.append((os.path.getsize(path), path, classes, funcs))
            except: pass
for size, path, c, f in sorted(results, reverse=True)[:10]:
    print(f"{size//1024}KB  {c} classes  {f} funcs  {path}")
```

### Duplicate Detection

**When:** Investigating repeated content in logs or data files.

```python
python3 -c "from collections import Counter; c=Counter(open('file.txt').read().splitlines()); print([line for line, count in c.most_common(10) if count > 1])"
```

---

## Rules

1. **Never read a file over 500 lines in its entirety.** Check size first; extract what you need.
2. **Always check size before reading.** `wc -l` takes milliseconds; a blown context window does not recover.
3. **When truncated, do not re-read.** Write a targeted extraction command instead.
4. **Use only standard library packages.** Never `pip install` or `npm install` for file analysis tasks.
5. **Return structured results, not raw content.** Summaries, counts, and key fields — not file dumps.
6. **Keep one-liners to 10 lines maximum.** If you need more, write a temporary script to `/tmp/`.
7. **Process line-by-line or in chunks** when the file is large and you need more than a sample.
8. **Handle encoding errors gracefully.** Use `errors='replace'` or `errors='ignore'` for binary-safe reads.

---

## Anti-Patterns

| Anti-Pattern | What Happens | Fix |
|---|---|---|
| **Context Hog** | Reading an entire large file into context, consuming the window | Check size first; use targeted extraction |
| **Blind Read** | Opening a file without checking its size | Always run `wc -l` or `stat` before reading |
| **The Retry** | File was truncated; re-reading it hoping for different results | Switch to extraction commands after first truncation |
| **Dependency Installer** | `pip install pandas` or `npm install` just to analyze a file | Use standard library only |
| **Verbose Dumper** | Printing every line of a file during analysis | Return aggregate results and summaries |
| **Memory Bomb** | Loading the entire file into a variable before processing | Stream or chunk-process; read only what is needed |
| **Wrong Tool** | Using Python to do what `head -20` does | Use the simplest tool; Bash for simple extraction |

---

## Related Skills

- **`file-system-tools:free-disk-space`** — Reclaim disk space by cleaning package-manager and IDE caches when a large-file workflow is blocked by a full disk.
