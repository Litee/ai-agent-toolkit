# Callouts Reference

Callouts are styled blockquotes for visually highlighting information. They extend standard Markdown blockquotes with a type identifier.

## Basic Syntax

```
> [!type]
> Callout content goes here.
```

- `type` — one of the built-in types below (case-insensitive)
- Content follows normal Markdown: bold, italic, links, lists, code blocks, nested callouts

## Optional Features

**Custom title** — overrides the default label:
```
> [!tip] My Custom Title
> Content here.
```

**No title** — empty string hides the title bar:
```
> [!tip]
> Content with no visible title.
```

**Collapsible — collapsed by default** (trailing `-`):
```
> [!warning]- Collapsed Section
> This content is hidden until the user clicks to expand.
```

**Collapsible — expanded by default** (trailing `+`):
```
> [!info]+
> Expanded by default but can be collapsed.
```

## Built-in Types

| Type | Aliases | Colour |
|------|---------|--------|
| `note` | — | Blue |
| `abstract` | `summary`, `tldr` | Blue-green |
| `info` | — | Blue |
| `todo` | — | Blue |
| `tip` | `hint`, `important` | Green |
| `success` | `check`, `done` | Green |
| `question` | `help`, `faq` | Yellow |
| `warning` | `caution`, `attention` | Orange |
| `failure` | `fail`, `missing` | Red |
| `danger` | `error` | Red |
| `bug` | — | Red |
| `example` | — | Purple |
| `quote` | `cite` | Grey |

Aliases are interchangeable with the primary type name:
```
> [!faq]
> This renders identically to > [!question]
```

## Examples

```
> [!note]
> A basic informational callout.

> [!tip] Pro Tip
> Use wikilinks liberally — they update automatically when notes are renamed.

> [!warning]- Destructive Operation
> This command will permanently delete the file and cannot be undone.

> [!danger]
> Never store credentials in plain text.

> [!success] Done
> All tests passed successfully.

> [!abstract] TL;DR
> Three sentences summarising the note.

> [!question] Open Question
> What is the optimal cache invalidation strategy for this use case?

> [!bug]
> Known issue: the sort order is reversed when the list exceeds 100 items.

> [!example]
> ```python
> result = sorted(items, key=lambda x: x.score, reverse=True)
> ```

> [!quote]
> "Premature optimisation is the root of all evil." — Donald Knuth
```

## Nesting

Callouts can be nested by indenting the inner blockquote:

```
> [!info] Outer Callout
> This is the outer content.
>
> > [!tip] Inner Callout
> > This is the inner content.
>
> Back to outer content.
```

## Custom Callout Types

Custom types can be defined via CSS snippets using `data-callout` attributes. The callout will render with a default style if the type is unrecognised:

```css
.callout[data-callout="my-type"] {
  --callout-color: 0, 150, 200;
  --callout-icon: lucide-star;
}
```
