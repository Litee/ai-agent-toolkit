---
name: enrich-obsidian-notes-with-best-practices
description: "Use when asked to 'add best practices to notes', 'enrich notes with best practices and anti-patterns', 'find notes missing BP/AP sections', or 'improve knowledge notes with practical guidance'. Adds Best Practices and Anti-Patterns sections to knowledge base notes using parallel sub-agents and research. Do NOT use for concept/theory notes, biographical notes, comparison notes, or index/hub notes."
---

# enrich-obsidian-notes-with-best-practices

## Overview

This skill guides the process of adding `## Best Practices` and `## Anti-Patterns` sections to Obsidian knowledge base notes. It uses parallel sub-agents for research and enforces quality filters to ensure the resulting content is actionable, specific, and non-obvious.

---

## Note Selection Criteria

### Notes that SHOULD receive Best Practices and Anti-Patterns sections

- **Technology/tool notes**: PyTorch, Kafka, DynamoDB, Kubernetes, Redis, Elasticsearch, etc.
- **Framework notes**: FastAPI, React, Spark, Django, Spring Boot, etc.
- **Service notes**: AWS Lambda, S3, CloudFront, RDS, SQS, etc.
- **System design pattern notes**: Caching, Load Balancing, Message Queues, Circuit Breaker, etc.

### Notes that should NOT receive BP/AP sections

- **Concept/theory notes**: Attention Mechanism, Gradient Descent — these are definitions, not guidance
- **Biographical notes**: people, companies, organizations
- **Comparison notes**: "DDB vs Cassandra" — these have their own format
- **Index/hub notes**: notes that are primarily links with no substantive content
- **Already-enriched notes**: check for existing `## Best Practices` or `## Anti-Patterns` headings before adding

---

## Research Workflow

### Phase 1: Select Notes

1. List candidate notes from the vault (use `obsidian:use-obsidian-cli` to list notes, or inspect the vault directory)
2. Filter to technology/tool/service/pattern notes
3. Exclude already-enriched notes by checking for existing `## Best Practices` heading
4. Present the candidate list to the user and confirm scope if it is large (>20 notes)

### Phase 2: Dispatch Parallel Research Sub-Agents

Dispatch 5–6 sub-agents in parallel, assigning 5 notes each.

Each sub-agent:
1. Reads the note to understand the topic and its existing structure
2. Searches the internet for:
   - `[topic] best practices anti-patterns production`
   - `[topic] common mistakes gotchas`
3. Extracts actionable items that pass the quality filter (see Phase 3)
4. Returns structured output: topic, best practices list, anti-patterns list

### Phase 3: Quality Filter Before Writing

Every item must pass all three criteria before inclusion:

**Actionable**: names a concrete technique or action
- Pass: "Avoid N+1 queries by using eager loading"
- Fail: "Write good code"

**Specific**: names the technique, parameter, threshold, or tool involved
- Pass: "Set pool size = (CPU cores × 2) + 1 as a starting point for connection pooling"
- Fail: "Configure your connection pool appropriately"

**Non-obvious**: not already implied by "read the docs" or "test your code"
- Pass: "Lambda cold starts can be mitigated by provisioned concurrency for latency-sensitive paths"
- Fail: "Test your Lambda functions before deploying"

**Quantity limits**: 3–7 items per section. Quality over quantity — do not include items just to reach a minimum.

---

## Output Format

Use these Obsidian conventions exactly:

```markdown
## Best Practices

- **Use connection pooling**: Re-use connections to avoid per-request overhead; set pool size = (CPU cores × 2) + 1 as a starting point.
- **Paginate large result sets**: Never fetch unbounded result sets; use cursor-based or keyset pagination to avoid memory exhaustion.
- **Enable compression for large payloads**: Gzip or Snappy compression reduces network transfer time for payloads > 1 KB with negligible CPU overhead.

## Anti-Patterns

- **Storing secrets in environment variables unencrypted**: Environment variables are visible in process listings and logs. Use a secrets manager (Vault, AWS Secrets Manager) instead.
- **Using synchronous calls in hot paths**: Blocking I/O in request handlers serialises concurrent requests and caps throughput. Use async or thread pools for all I/O.
```

Each anti-pattern entry must include:
1. What the bad pattern is (the bold label)
2. Why it is bad (the consequence)
3. What to do instead

---

## Wikilinks

After writing the sections, scan the new content for concepts that have existing vault notes. If a term in the new content matches (or closely matches) an existing note filename, link it as `[[Note Name]]`.

Example: if the best practices mention "connection pooling" and `Connection Pooling.md` exists in the vault, write `[[Connection Pooling]]`.

Use `obsidian:use-obsidian-cli` to check for existing notes before creating links.

---

## Placement in the Note

Append the two sections at the end of the note, after all existing content. Do not insert them in the middle of existing sections.

If the note already has a `## See Also` or `## Related` section at the bottom, insert Best Practices and Anti-Patterns before those sections.

---

## Gotchas

- **Research without quality filters produces noise**: Sub-agents will surface 20+ generic items unless the quality filter is enforced at collection time, not just at review time. Always instruct sub-agents to apply the 3-criterion filter before returning results.
- **Version-specific practices**: If a best practice applies only to a specific version (e.g., "Kafka 3.0+"), note the version in the item. Do not present version-specific guidance as universally applicable.
- **No pricing-based recommendations**: Practices like "use Reserved Instances to save cost" change as pricing models evolve and do not belong in a knowledge base. Skip them.
- **Intentionally brief notes**: Some notes are deliberately short by design. Check the existing note structure before adding large sections — if the note is a pointer or stub, consider whether enrichment fits.
- **Don't conflate best practices with configuration examples**: Configuration snippets belong in a `## Configuration` or `## Usage` section. Best practices are principles, not copy-paste blocks.

---

## Related Skills

- `obsidian:manage-personal-knowledge-in-obsidian` — general Obsidian vault management
- `obsidian:use-obsidian-cli` — list notes, read note content, write notes
