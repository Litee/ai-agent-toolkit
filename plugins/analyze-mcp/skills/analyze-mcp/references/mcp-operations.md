# MCP Operations Reference

## Common Examples

### Example 1: Discover Tools on a Local Server

```bash
mcptools tools my-local-server
```

### Example 2: Test Search Tool

```bash
mcptools call search --params '{"query":"authentication best practices"}' my-local-server
```

### Example 3: Discover Tools on uvx-Based Server

```bash
mcptools tools uvx awslabs.aws-documentation-mcp-server@latest
```

### Example 4: Test Documentation Search

```bash
mcptools call search_documentation --params '{"search_phrase":"S3 bucket policies","limit":5}' uvx awslabs.aws-documentation-mcp-server@latest
```

### Example 5: Test Documentation Read with Optional Parameters

```bash
mcptools call read_documentation --params '{"url":"https://docs.aws.amazon.com/s3/index.html","max_length":10000}' uvx awslabs.aws-documentation-mcp-server@latest
```

### Example 6: Test Tool with Single Parameter

```bash
mcptools call recommend --params '{"url":"https://docs.aws.amazon.com/lambda/latest/dg/welcome.html"}' uvx awslabs.aws-documentation-mcp-server@latest
```

### Example 7: Discover Tools on npx-Based Server

```bash
mcptools tools npx -y @modelcontextprotocol/server-filesystem ~
```

### Example 8: Test npx-Based Server Tool

```bash
mcptools call read_file --params '{"path":"~/Documents/file.txt"}' npx -y @modelcontextprotocol/server-filesystem ~
```

---

## JSON Parameter Formatting

Parameters must be valid JSON enclosed in single quotes:

```bash
--params '{"key":"value"}'
```

| Value type | Format | Example |
|------------|--------|---------|
| String | Double-quoted | `{"query":"search term"}` |
| Number | Unquoted | `{"limit":10,"start_index":0}` |
| Boolean | Lowercase unquoted | `{"include_metadata":true}` |
| Special chars | Backslash-escape | `{"query":"testing \"quoted\" text"}` |

---

## Output Format Options

Add `--format` to any command:

```bash
mcptools tools --format json my-local-server
mcptools tools --format pretty my-local-server
mcptools call search_documentation --params '{"search_phrase":"S3"}' --format json uvx awslabs.aws-documentation-mcp-server@latest
```

| Format | Use case |
|--------|----------|
| `table` (default) | Interactive terminal, human readability |
| `json` | Scripts and automation that need to parse output |
| `pretty` | Debugging complex JSON structures |

---

## Error Handling

| Error | Cause | Solution |
|-------|-------|---------|
| `command not found: mcptools` | Not installed or not in PATH | Add `~/go/bin` to PATH or use full path `~/go/bin/mcptools` |
| Server not found | Wrong server name | Verify server name is correct and configured |
| JSON parsing error | Malformed `--params` JSON | Check quotes, escaping, and JSON structure |
| Missing required parameters | Tool execution failed | Review tool list output for required fields |
| Tool name not recognized | Wrong tool name | Run `mcptools tools <server>` to list available tools |
| uvx/npx package not found | Wrong package name or version | Verify package name and version string |
