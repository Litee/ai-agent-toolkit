---
name: analyze-mcp
description: Introspect MCP servers and test MCP tool calls via CLI. Use to discover what tools, resources, or prompts an MCP server provides, or to make test calls to verify MCP server behavior.
---

# MCP Introspection

## Purpose

This skill guides introspection of MCP (Model Context Protocol) servers and testing of MCP tool calls using the `mcptools` command-line interface. Use this skill to:

- Discover what tools, resources, or prompts an MCP server provides
- Inspect MCP server capabilities before using them
- Make test calls to MCP tools to understand their behavior
- Explore available MCP servers and their functionality

## Prerequisites

This skill requires the `mcptools` CLI to be installed.

**Install with Go:**

```bash
go install github.com/f/mcptools/cmd/mcptools@latest
```

The binary is placed at `~/go/bin/mcptools`. Ensure `~/go/bin` is on your `PATH`:

```bash
export PATH="$HOME/go/bin:$PATH"
```

See https://github.com/f/mcptools for more details.

## Core Operations

### 1. List Available Tools

To discover what tools an MCP server provides:

```bash
mcptools tools <server-name>
```

**Example with local MCP server:**
```bash
mcptools tools my-local-server
```

**Example with uvx-based MCP server:**
```bash
mcptools tools uvx awslabs.aws-documentation-mcp-server@latest
```

**Example with npx-based MCP server:**
```bash
mcptools tools npx -y @modelcontextprotocol/server-filesystem ~
```

This command returns a list of all available tools from the specified MCP server, including tool names and their descriptions.

### 2. Call MCP Tools

To make test calls to MCP tools:

```bash
mcptools call <tool-name> --params '<json-parameters>' <server-name>
```

**Important parameter formatting:**
- Parameters must be provided as a valid JSON string
- Use single quotes around the JSON string to avoid shell interpretation
- Ensure proper JSON escaping for nested quotes

**Example with simple parameters:**
```bash
mcptools call search --params '{"query":"Hello world"}' my-local-server
```

**Example with multiple parameters:**
```bash
mcptools call search_documentation --params '{"search_phrase":"aws data lake","limit":10}' uvx awslabs.aws-documentation-mcp-server@latest
```

**Example with optional parameters:**
```bash
mcptools call read_documentation --params '{"url":"https://docs.aws.amazon.com/lambda/latest/dg/lambda-invocation.html","max_length":5000,"start_index":0}' uvx awslabs.aws-documentation-mcp-server@latest
```

### 3. List and Read Resources (if supported)

Some MCP servers may provide resources. To list them:

```bash
mcptools resources <server-name>
```

To read a specific resource:

```bash
mcptools read-resource <resource-uri> <server-name>
```

**Note:** Not all MCP servers support resources. If the command fails or returns no results, the server may not implement this capability.

### 4. List and Get Prompts (if supported)

Some MCP servers may provide prompts. To list them:

```bash
mcptools prompts <server-name>
```

To get a specific prompt:

```bash
mcptools get-prompt <prompt-name> <server-name>
```

**Note:** Not all MCP servers support prompts. If the command fails or returns no results, the server may not implement this capability.

## MCP Server Specification Formats

MCP servers can be specified in different formats:

### Local/Named Servers

These are MCP servers configured locally or available by a simple name:

```bash
mcptools tools my-local-server
mcptools call <tool-name> --params '<json>' my-local-server
```

### uvx-Based Servers

These are MCP servers distributed via Python packages and invoked through uvx:

```bash
mcptools tools uvx <package-name>@<version>
mcptools call <tool-name> --params '<json>' uvx <package-name>@<version>
```

**Example:**
```bash
mcptools tools uvx awslabs.aws-documentation-mcp-server@latest
```

### npx-Based Servers

These are MCP servers distributed via npm packages and invoked through npx:

```bash
mcptools tools npx -y <package-name>@<version> <directory>
mcptools call <tool-name> --params '<json>' npx -y <package-name>@<version> <directory>
```

**Important flags:**
- `-y` - Skip npm confirmation prompts
- `<directory>` - Allowed directory for filesystem access (e.g., `~` for home directory)

**Example:**
```bash
mcptools tools npx -y @modelcontextprotocol/server-filesystem ~
```

## Workflow for Discovering and Testing MCP Tools

### Step 1: List Available Tools

Discover what tools the MCP server provides:

```bash
mcptools tools <server-name>
```

Review the output to identify:
- Tool names
- Tool descriptions
- Expected parameters (if provided)

### Step 2: Understand Tool Parameters

Based on the tool list output, identify the required and optional parameters for the tool to test. If parameter details are not clear from the list output, consult any available documentation for the MCP server.

### Step 3: Construct Test Call

Build the mcptools call command:

1. Start with: `mcptools call <tool-name>`
2. Add parameters: `--params '{"param1":"value1","param2":"value2"}'`
3. Specify server: `<server-name>`

### Step 4: Execute Test Call

Run the constructed command and observe the output:

```bash
mcptools call <tool-name> --params '<json-parameters>' <server-name>
```

### Step 5: Interpret Results

Analyze the output to understand:
- What data the tool returns
- The format of the response
- Whether the tool succeeded or returned an error
- How to use this tool in practice

## Common Examples

See `references/mcp-operations.md` for full examples. Quick reference:

```bash
# Local server
mcptools tools my-local-server
mcptools call search --params '{"query":"hello"}' my-local-server

# uvx-based server
mcptools tools uvx awslabs.aws-documentation-mcp-server@latest
mcptools call search_documentation --params '{"search_phrase":"S3","limit":5}' uvx awslabs.aws-documentation-mcp-server@latest

# npx-based server
mcptools tools npx -y @modelcontextprotocol/server-filesystem ~
```

## Reference Documentation

See `references/mcp-operations.md` for:
- Full worked examples for all server types
- JSON parameter formatting guide (strings, numbers, booleans, escaping)
- Output format options (`table`, `json`, `pretty`)
- Error handling reference table
