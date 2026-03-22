# Properties (Frontmatter) Reference

Properties are YAML metadata defined at the top of a note between `---` delimiters. They appear before any note content.

## Syntax

```yaml
---
property-name: value
another-property: another value
---
```

The opening `---` must be the very first line of the file. All standard YAML syntax is supported.

## Property Types

Obsidian recognises six data types. The type is inferred from the value but can be set explicitly in the Properties panel.

### Text

Simple string value:
```yaml
title: My Note Title
status: draft
source: https://example.com
```

### Number

Integer or decimal:
```yaml
rating: 4.5
priority: 1
word-count: 1234
```

### Checkbox

Boolean (true/false):
```yaml
done: false
featured: true
reviewed: false
```

### Date

ISO 8601 date format (`YYYY-MM-DD`):
```yaml
date: 2024-01-15
created: 2024-03-22
due: 2024-04-01
```

### Date & Time

ISO 8601 with time component (`YYYY-MM-DDTHH:MM:SS`):
```yaml
due: 2024-01-15T14:30:00
scheduled: 2024-03-22T09:00:00
```

### List

Array of values — inline or YAML block format:
```yaml
# Inline
tags: [one, two, three]

# Block
tags:
  - programming/python
  - status/draft
  - type/concept
```

### Links

References to other notes using wikilink bracket notation:
```yaml
related:
  - "[[Another Note]]"
  - "[[Yet Another Note]]"
```

## Built-in Properties

Three properties receive special treatment in Obsidian:

### `tags`

Enables searching by tag; tags also appear in the Tags pane and graph view.

```yaml
tags:
  - programming/python
  - status/draft
```

Tag rules: letters (any language), numbers (not as first character), underscores, hyphens. Forward slashes create nested tags.

### `aliases`

Alternative names for the note. Obsidian suggests these when typing wikilinks.

```yaml
aliases:
  - Alternative Name
  - Abbreviated Form
  - Common Misspelling
```

### `cssclasses`

CSS class names applied to the note container in Reading and Editing modes. Used by themes and CSS snippets for custom styling.

```yaml
cssclasses:
  - wide-page
  - no-inline-title
```

## Complete Example

```yaml
---
title: Redis Cache Invalidation Strategies
tags:
  - programming/databases
  - status/draft
  - type/concept
aliases:
  - Cache Invalidation
  - Redis Eviction
status: draft
type: concept
source: https://redis.io/docs/manual/eviction
rating: 4
date: 2024-01-15
reviewed: false
related:
  - "[[Cache Patterns]]"
  - "[[Redis Configuration]]"
cssclasses:
  - wide-page
---
```

## Notes

- Property names are case-sensitive: `Tags` and `tags` are different properties
- The `tags` property is special — Obsidian always treats it as the tag list regardless of type
- Unrecognised property names are treated as `text` by default
- Properties set via the CLI with `obsidian property:set` use `type=` to specify the data type
