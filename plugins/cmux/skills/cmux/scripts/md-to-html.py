#!/usr/bin/env python3
"""Convert a Markdown file to a styled HTML file in /tmp/.

Usage:
    python3 ${SKILL_DIR}/scripts/md-to-html.py /path/to/file.md [--dark]

Outputs the HTML file to /tmp/<basename>.html and prints the filename.
Strips YAML frontmatter. Supports headings, lists, code blocks, inline code,
bold, links, horizontal rules, and tables. No external dependencies.
"""

import re
import sys
import os
import html as html_mod

src = sys.argv[1]
out_name = os.path.basename(src).rsplit('.', 1)[0] + '.html'
out_path = '/tmp/' + out_name

with open(src) as f:
    content = f.read()

# Strip YAML frontmatter
if content.startswith('---'):
    end = content.index('---', 3)
    content = content[end+3:].strip()

DARK = '''
  body { font-family: -apple-system, system-ui, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; line-height: 1.6; color: #c9d1d9; background: #0d1117; }
  h1 { border-bottom: 2px solid #30363d; padding-bottom: 8px; color: #e6edf3; }
  h2 { border-bottom: 1px solid #30363d; padding-bottom: 4px; margin-top: 32px; color: #e6edf3; }
  h3 { margin-top: 24px; color: #e6edf3; }
  code { background: #161b22; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; color: #f0883e; }
  pre { background: #161b22; padding: 16px; border-radius: 6px; overflow-x: auto; color: #c9d1d9; }
  pre code { background: none; padding: 0; color: #c9d1d9; }
  ul { padding-left: 24px; margin: 8px 0; }
  ol { padding-left: 24px; margin: 8px 0; }
  li { margin-bottom: 6px; }
  a { color: #58a6ff; }
  p { margin: 4px 0; }
  strong { color: #e6edf3; }
  hr { border: none; border-top: 1px solid #30363d; margin: 32px 0; }
  table { border-collapse: collapse; width: 100%; margin: 16px 0; }
  th { background: #161b22; padding: 8px 12px; border: 1px solid #30363d; text-align: left; color: #e6edf3; font-weight: 600; }
  td { padding: 8px 12px; border: 1px solid #30363d; }
  tr:nth-child(even) td { background: rgba(22,27,34,0.5); }
'''

LIGHT = '''
  body { font-family: -apple-system, system-ui, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; line-height: 1.6; color: #1a1a1a; background: #fff; }
  h1 { border-bottom: 2px solid #e1e4e8; padding-bottom: 8px; }
  h2 { border-bottom: 1px solid #e1e4e8; padding-bottom: 4px; margin-top: 32px; }
  h3 { margin-top: 24px; }
  code { background: #f0f0f0; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }
  pre { background: #f6f8fa; padding: 16px; border-radius: 6px; overflow-x: auto; }
  pre code { background: none; padding: 0; }
  ul { padding-left: 24px; margin: 8px 0; }
  ol { padding-left: 24px; margin: 8px 0; }
  li { margin-bottom: 6px; }
  a { color: #0366d6; }
  p { margin: 4px 0; }
  hr { border: none; border-top: 1px solid #e1e4e8; margin: 32px 0; }
  table { border-collapse: collapse; width: 100%; margin: 16px 0; }
  th { background: #f6f8fa; padding: 8px 12px; border: 1px solid #e1e4e8; text-align: left; font-weight: 600; }
  td { padding: 8px 12px; border: 1px solid #e1e4e8; }
  tr:nth-child(even) td { background: #f9f9f9; }
'''

theme = DARK if '--dark' in sys.argv else LIGHT

def inline(t):
    t = re.sub(r'\x60([^\x60]+)\x60', r'<code>\1</code>', t)
    t = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'(?<![\"=])https?://[^\s<>)]+', lambda m: f'<a href="{m.group()}">{m.group()}</a>', t)
    return t

def flush_tbl(rows, sep):
    out = ['<table>']
    started_body = False
    for i, row in enumerate(rows):
        if i == sep: continue
        cells = [c.strip() for c in row.strip().strip('|').split('|')]
        if sep >= 0 and i < sep:
            out.append('<thead><tr>' + ''.join(f'<th>{inline(c)}</th>' for c in cells) + '</tr></thead>')
        else:
            if not started_body: out.append('<tbody>'); started_body = True
            out.append('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in cells) + '</tr>')
    if started_body: out.append('</tbody>')
    out.append('</table>')
    return out

lines = content.split('\n')
h, in_ul, in_ol, in_code, code_buf, in_tbl, tbl_rows, tbl_sep = [], False, False, False, [], False, [], -1
for line in lines:
    s = line.strip()
    if s.startswith('\x60\x60\x60'):
        if in_code:
            h.append('<pre><code>' + '\n'.join(code_buf) + '</code></pre>')
            code_buf = []; in_code = False
        else:
            if in_ul: h.append('</ul>'); in_ul = False
            if in_ol: h.append('</ol>'); in_ol = False
            in_code = True
        continue
    if in_code:
        code_buf.append(html_mod.escape(line)); continue
    if s.startswith('|') and '|' in s[1:]:
        if in_ul: h.append('</ul>'); in_ul = False
        if in_ol: h.append('</ol>'); in_ol = False
        if not in_tbl: in_tbl = True; tbl_rows = []; tbl_sep = -1
        if all(re.match(r'^[-:]+$', c.strip()) for c in s.strip().strip('|').split('|') if c.strip()):
            tbl_sep = len(tbl_rows)
        tbl_rows.append(s)
        continue
    if in_tbl:
        h.extend(flush_tbl(tbl_rows, tbl_sep)); in_tbl = False
    if not s:
        if in_ul: h.append('</ul>'); in_ul = False
        if in_ol: h.append('</ol>'); in_ol = False
        h.append('<br>'); continue
    if s == '---':
        if in_ul: h.append('</ul>'); in_ul = False
        if in_ol: h.append('</ol>'); in_ol = False
        h.append('<hr>'); continue
    m = re.match(r'^(#{1,4})\s+(.*)', s)
    if m:
        if in_ul: h.append('</ul>'); in_ul = False
        if in_ol: h.append('</ol>'); in_ol = False
        n = len(m.group(1))
        h.append(f'<h{n}>{inline(m.group(2))}</h{n}>'); continue
    m = re.match(r'^(\d+)\.\s+(.*)', s)
    if m:
        if in_ul: h.append('</ul>'); in_ul = False
        if not in_ol: h.append('<ol>'); in_ol = True
        h.append(f'<li>{inline(m.group(2))}</li>'); continue
    m = re.match(r'^[-*]\s+(.*)', s)
    if m:
        if in_ol: h.append('</ol>'); in_ol = False
        if not in_ul: h.append('<ul>'); in_ul = True
        h.append(f'<li>{inline(m.group(1))}</li>'); continue
    if in_ul: h.append('</ul>'); in_ul = False
    if in_ol: h.append('</ol>'); in_ol = False
    h.append(f'<p>{inline(s)}</p>')
if in_ul: h.append('</ul>')
if in_ol: h.append('</ol>')
if in_tbl: h.extend(flush_tbl(tbl_rows, tbl_sep))

page = f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{theme}</style></head><body>{chr(10).join(h)}</body></html>'
with open(out_path, 'w') as f:
    f.write(page)
print(f'OK {out_name}')
