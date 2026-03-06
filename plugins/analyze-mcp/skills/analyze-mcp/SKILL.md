---
name: analyze-mcp
description: This skill should be used when introspecting MCP servers and testing MCP tool calls via CLI. Use this skill to discover what tools/resources/prompts an MCP server provides or to make test calls to MCP servers.
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
mcptools tools builder-mcp
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
mcptools call InternalSearch --params '{"query":"Hello world"}' builder-mcp
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
mcptools tools builder-mcp
mcptools call <tool-name> --params '<json>' builder-mcp
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

### Example 1: Discover Tools on a Local Server

```bash
mcptools tools builder-mcp
```

### Example 2: Test Search Tool

```bash
mcptools call InternalSearch --params '{"query":"authentication best practices"}' builder-mcp
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

## Error Handling

### Common Errors

1. **mcptools not found**
   - Error: `command not found: mcptools`
   - Solution: mcptools is typically installed at `~/go/bin/mcptools`. Either:
     - Add `~/go/bin` to your PATH: `export PATH="$HOME/go/bin:$PATH"`
     - Use the full path: `~/go/bin/mcptools tools <server-name>`
     - If not installed, refer to https://github.com/f/mcptools for installation instructions

2. **Server not found**
   - Error: Server name not recognized
   - Solution: Verify the server name is correct and the server is properly configured

3. **Invalid JSON parameters**
   - Error: JSON parsing error
   - Solution: Ensure JSON is properly formatted with correct quotes and escaping

4. **Missing required parameters**
   - Error: Tool execution fails due to missing parameters
   - Solution: Review the tool's parameter requirements and include all required fields

5. **Tool not found**
   - Error: Tool name not recognized by the server
   - Solution: Use `mcptools tools <server-name>` to list available tools

6. **uvx server not accessible**
   - Error: Package not found or version not available
   - Solution: Verify the package name and version are correct

7. **npx server not accessible**
   - Error: Package not found or version not available
   - Solution: Verify the npm package name and version are correct

## JSON Parameter Formatting Guidelines

### Basic Format

Parameters must be valid JSON enclosed in single quotes:

```bash
--params '{"key":"value"}'
```

### Multiple Parameters

Separate parameters with commas:

```bash
--params '{"param1":"value1","param2":"value2","param3":123}'
```

### String Values

Use double quotes for string values:

```bash
--params '{"query":"search term","limit":10}'
```

### Numeric Values

Do not quote numeric values:

```bash
--params '{"max_length":5000,"start_index":0}'
```

### Boolean Values

Use lowercase true/false without quotes:

```bash
--params '{"include_metadata":true,"verbose":false}'
```

### Special Characters in Strings

Escape special characters within string values:

```bash
--params '{"query":"testing \"quoted\" text"}'
```

## Output Format Options

mcptools supports multiple output formats for different use cases:

### Available Formats

- **table** (default): Colorized, human-readable tabular format
- **json**: Compact JSON output for programmatic parsing
- **pretty**: Pretty-printed JSON with indentation for readability

### Usage

Add the `--format` flag to any command:

```bash
# List tools in JSON format
mcptools tools --format json builder-mcp

# List tools in pretty JSON format
mcptools tools --format pretty builder-mcp

# Call a tool and get JSON output
mcptools call search_documentation --params '{"search_phrase":"S3"}' --format json uvx awslabs.aws-documentation-mcp-server@latest
```

### When to Use Each Format

- **table**: Best for interactive terminal use and human readability
- **json**: Best for scripts and automation that need to parse output
- **pretty**: Best for debugging and understanding complex JSON structures

## Summary

- Use `mcptools tools <server-name>` to discover available tools
- Use `mcptools call <tool-name> --params '<json>' <server-name>` to test tools
- Ensure JSON parameters are properly formatted and enclosed in single quotes
- MCP servers can be local/named, uvx-based (Python packages), or npx-based (npm packages)
- Not all MCP servers support resources and prompts - verify capability first
- Review command output carefully to understand tool behavior
- If mcptools is not installed, refer to https://github.com/f/mcptools for installation instructions
