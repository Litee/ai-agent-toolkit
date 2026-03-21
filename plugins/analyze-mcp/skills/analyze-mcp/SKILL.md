---
name: analyze-mcp
description: Introspect MCP servers and test MCP tool calls via CLI. Use to discover what tools, resources, or prompts an MCP server provides, or to make test calls to verify MCP server behavior. Trigger when the user asks to "debug MCP", "list MCP tools", "what tools does my MCP server have", "explore MCP", "test an MCP tool call", or needs to understand what a specific MCP server exposes.
---

# MCP Introspection

Use the `mcptools` CLI to discover MCP server capabilities and test tool calls.

## Prerequisites

Install `mcptools` via Go:

```bash
go install github.com/f/mcptools/cmd/mcptools@latest
export PATH="$HOME/go/bin:$PATH"
```

See https://github.com/f/mcptools for more details.

## Core Commands

### List tools
```bash
mcptools tools <server>
```

### Call a tool
```bash
mcptools call <tool-name> --params '{"key":"value"}' <server>
```

### List/read resources (if supported)
```bash
mcptools resources <server>
mcptools read-resource <resource-uri> <server>
```

### List/get prompts (if supported)
```bash
mcptools prompts <server>
mcptools get-prompt <prompt-name> <server>
```

## Server Specification Formats

| Type | Format | Example |
|------|--------|---------|
| Local/named | `<name>` | `my-local-server` |
| Python (uvx) | `uvx <package>@<version>` | `uvx awslabs.aws-documentation-mcp-server@latest` |
| Node (npx) | `npx -y <package> <dir>` | `npx -y @modelcontextprotocol/server-filesystem ~` |

## Examples

```bash
# List tools on a uvx server
mcptools tools uvx awslabs.aws-documentation-mcp-server@latest

# Call a tool
mcptools call search_documentation \
  --params '{"search_phrase":"S3 lifecycle","limit":5}' \
  uvx awslabs.aws-documentation-mcp-server@latest

# List tools on an npx server
mcptools tools npx -y @modelcontextprotocol/server-filesystem ~

# Call a local named server
mcptools call search --params '{"query":"hello"}' my-local-server
```

## Workflow

1. `mcptools tools <server>` — discover available tools, names, and descriptions
2. Identify required/optional parameters from the tool descriptions
3. `mcptools call <tool> --params '<json>' <server>` — test the call
4. Analyze the response to understand output format and behavior

For full worked examples, JSON formatting tips, output format options (`table`, `json`, `pretty`), and error handling, see `references/mcp-operations.md`.
