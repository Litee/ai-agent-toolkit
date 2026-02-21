---
name: search-aws-documentation
description: This skill should be used when searching for or reading official AWS documentation. Use when looking up AWS service documentation, API references, user guides, best practices, tutorials, or any public AWS documentation from docs.aws.amazon.com. Also provides AWS architecture guidance and solution recommendations.
---

# Search AWS Documentation

## Purpose

This skill provides access to official AWS documentation using two MCP servers that enable searching, reading, and getting recommendations from AWS docs, as well as receiving AWS architecture guidance. Use this skill when working with AWS services to find accurate, up-to-date information from official AWS documentation.

## Prerequisites

- mcptools CLI (typically installed at `~/go/bin/mcptools`)
- awslabs.aws-documentation-mcp-server MCP server configured
- awslabs.core-mcp-server MCP server configured (optional, for architecture guidance)

## Available MCP Tools

The skill utilizes tools from two AWS MCP servers for comprehensive documentation access.

### Recommended Tool Order

When building AWS solutions, follow this recommended order:

1. **prompt_understanding** (awslabs.core-mcp-server) - **START HERE** to get AWS service recommendations
2. **search_documentation** (awslabs.aws-documentation-mcp-server) - Search for documentation on recommended services
3. **read_documentation** (awslabs.aws-documentation-mcp-server) - Read specific documentation pages
4. **recommend** (awslabs.aws-documentation-mcp-server) - Discover related documentation
5. **get_available_services** (awslabs.aws-documentation-mcp-server) - Check China region availability (if needed)

---

## Tool 1: prompt_understanding

**⚠️ IMPORTANT: Call this tool FIRST when starting any AWS solution design to get service recommendations before searching documentation.**

Provides guidance and planning support when building AWS solutions, translating prompts into actionable AWS service recommendations and architectural planning. This tool provides a starting point for using AWS MCP servers.

**MCP Server:** awslabs.core-mcp-server

### Parameters

- **prompt** (required, string): Description of the AWS solution or architecture question

### Usage

```bash
mcptools call prompt_understanding --params '{"prompt":"your architecture question or requirement"}' awslabs.core-mcp-server
```

### Examples

**Example 1: Get guidance for serverless API design**
```bash
mcptools call prompt_understanding --params '{"prompt":"design a serverless API with authentication"}' awslabs.core-mcp-server
```

**Example 2: Get recommendations for data processing pipeline**
```bash
mcptools call prompt_understanding --params '{"prompt":"build a real-time data processing pipeline"}' awslabs.core-mcp-server
```

**Example 3: Get architecture guidance for web application**
```bash
mcptools call prompt_understanding --params '{"prompt":"deploy a highly available web application"}' awslabs.core-mcp-server
```

**Example 4: Get recommendations for storage solution**
```bash
mcptools call prompt_understanding --params '{"prompt":"choose storage solution for large media files"}' awslabs.core-mcp-server
```

**Example 5: Get guidance for microservices architecture**
```bash
mcptools call prompt_understanding --params '{"prompt":"implement microservices with container orchestration"}' awslabs.core-mcp-server
```

### Important Notes

- **START HERE** when building any AWS solution or architecture
- Provides AWS service recommendations based on requirements
- Offers architectural guidance and best practices
- Helps translate high-level requirements into specific AWS services
- Use this tool BEFORE searching documentation to understand what services you need

---

## Tool 2: search_documentation

Search AWS documentation using the official AWS Documentation Search API.

**MCP Server:** awslabs.aws-documentation-mcp-server

### Parameters

- **search_phrase** (required, string): The search query terms
- **limit** (required, integer): Maximum number of results to return

### Availability

Global AWS partition only. Not available for China regions (aws-cn partition).

### Usage

```bash
mcptools call search_documentation --params '{"search_phrase":"your search terms","limit":10}' awslabs.aws-documentation-mcp-server
```

### Examples

**Example 1: Search for S3 bucket policies**
```bash
mcptools call search_documentation --params '{"search_phrase":"S3 bucket policies","limit":10}' awslabs.aws-documentation-mcp-server
```

**Example 2: Find Lambda function configuration**
```bash
mcptools call search_documentation --params '{"search_phrase":"Lambda function configuration","limit":15}' awslabs.aws-documentation-mcp-server
```

**Example 3: Search for EC2 instance types**
```bash
mcptools call search_documentation --params '{"search_phrase":"EC2 instance types comparison","limit":20}' awslabs.aws-documentation-mcp-server
```

**Example 4: Find DynamoDB best practices**
```bash
mcptools call search_documentation --params '{"search_phrase":"DynamoDB best practices performance","limit":10}' awslabs.aws-documentation-mcp-server
```

**Example 5: Search for VPC networking**
```bash
mcptools call search_documentation --params '{"search_phrase":"VPC subnet routing","limit":10}' awslabs.aws-documentation-mcp-server
```

### Important Notes

- Returns search results with titles, URLs, and snippets from AWS documentation
- Results are from docs.aws.amazon.com and official AWS documentation sites
- Search is performed across all AWS services and documentation types
- Higher limit values return more results but may take longer to process

---

## Tool 3: read_documentation

Retrieves an AWS documentation page and transforms it into markdown format for easier processing.

**MCP Server:** awslabs.aws-documentation-mcp-server

### Parameters

- **url** (required, string): The full URL of the AWS documentation page to fetch

### Usage

```bash
mcptools call read_documentation --params '{"url":"https://docs.aws.amazon.com/path/to/page.html"}' awslabs.aws-documentation-mcp-server
```

### Supported URL Patterns

The tool works with documentation URLs from:
- `https://docs.aws.amazon.com/` - Primary AWS documentation
- Service-specific documentation subdomains
- API reference pages
- User guides and tutorials

### Examples

**Example 1: Read S3 bucket policies documentation**
```bash
mcptools call read_documentation --params '{"url":"https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucket-policies.html"}' awslabs.aws-documentation-mcp-server
```

**Example 2: Read Lambda function configuration guide**
```bash
mcptools call read_documentation --params '{"url":"https://docs.aws.amazon.com/lambda/latest/dg/configuration-function-common.html"}' awslabs.aws-documentation-mcp-server
```

**Example 3: Read DynamoDB best practices**
```bash
mcptools call read_documentation --params '{"url":"https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html"}' awslabs.aws-documentation-mcp-server
```

**Example 4: Read EC2 instance types documentation**
```bash
mcptools call read_documentation --params '{"url":"https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-types.html"}' awslabs.aws-documentation-mcp-server
```

**Example 5: Read VPC networking guide**
```bash
mcptools call read_documentation --params '{"url":"https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html"}' awslabs.aws-documentation-mcp-server
```

### Important Notes

- Converts HTML documentation to clean markdown format
- Preserves code blocks, links, and formatting
- Removes navigation elements and page chrome
- Returns the main content area of the documentation page
- Use this after finding relevant pages via search_documentation

---

## Tool 4: recommend

Retrieves suggested content recommendations associated with a specific AWS documentation page.

**MCP Server:** awslabs.aws-documentation-mcp-server

### Parameters

- **url** (required, string): The AWS documentation page URL for which to get recommendations

### Availability

Global AWS partition only. Not available for China regions (aws-cn partition).

### Usage

```bash
mcptools call recommend --params '{"url":"https://docs.aws.amazon.com/path/to/page.html"}' awslabs.aws-documentation-mcp-server
```

### Examples

**Example 1: Get recommendations for S3 bucket policies page**
```bash
mcptools call recommend --params '{"url":"https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucket-policies.html"}' awslabs.aws-documentation-mcp-server
```

**Example 2: Get related Lambda documentation**
```bash
mcptools call recommend --params '{"url":"https://docs.aws.amazon.com/lambda/latest/dg/configuration-function-common.html"}' awslabs.aws-documentation-mcp-server
```

**Example 3: Get related DynamoDB content**
```bash
mcptools call recommend --params '{"url":"https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html"}' awslabs.aws-documentation-mcp-server
```

### Important Notes

- Returns related documentation pages that users often view together
- Helps discover additional relevant documentation
- Recommendations are based on AWS's content relationships
- Use after reading a documentation page to find related content

---

## Tool 5: get_available_services

Retrieves a comprehensive list of AWS services accessible within China regions.

**MCP Server:** awslabs.aws-documentation-mcp-server

### Parameters

None

### Availability

China AWS partition (aws-cn) only. Not available for global AWS partition.

### Usage

```bash
mcptools call get_available_services --params '{}' awslabs.aws-documentation-mcp-server
```

### Examples

**Example 1: List all services available in China regions**
```bash
mcptools call get_available_services --params '{}' awslabs.aws-documentation-mcp-server
```

### Important Notes

- Only works when configured for China AWS partition
- Returns service names and availability information
- Useful for understanding service limitations in China regions

---

## Common Workflows

### Workflow 1: Architecture Planning → Documentation Lookup (Recommended)

**Use this workflow when building new AWS solutions.** Start with architecture guidance, then look up documentation on recommended services.

1. **Get AWS service recommendations** (START HERE)
   ```bash
   mcptools call prompt_understanding --params '{"prompt":"build a serverless API with authentication and database"}' awslabs.core-mcp-server
   ```

2. **Search for documentation** on recommended services
   ```bash
   mcptools call search_documentation --params '{"search_phrase":"API Gateway Lambda authentication","limit":10}' awslabs.aws-documentation-mcp-server
   ```

3. **Read detailed documentation** for implementation
   ```bash
   mcptools call read_documentation --params '{"url":"<relevant-url-from-search>"}' awslabs.aws-documentation-mcp-server
   ```

### Workflow 2: Search → Read → Recommend

Use when you already know which AWS service you need and want to explore its documentation.

1. **Search for relevant documentation**
   ```bash
   mcptools call search_documentation --params '{"search_phrase":"Lambda environment variables","limit":10}' awslabs.aws-documentation-mcp-server
   ```

2. **Read the most relevant page** from search results
   ```bash
   mcptools call read_documentation --params '{"url":"https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html"}' awslabs.aws-documentation-mcp-server
   ```

3. **Get recommendations** for related content
   ```bash
   mcptools call recommend --params '{"url":"https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html"}' awslabs.aws-documentation-mcp-server
   ```

4. **Read recommended pages** if needed
   ```bash
   mcptools call read_documentation --params '{"url":"<recommended-url>"}' awslabs.aws-documentation-mcp-server
   ```

### Workflow 3: Deep Dive Research

When researching a specific AWS service or feature in depth.

1. **Start with broad search**
   ```bash
   mcptools call search_documentation --params '{"search_phrase":"DynamoDB","limit":20}' awslabs.aws-documentation-mcp-server
   ```

2. **Read overview documentation**
   ```bash
   mcptools call read_documentation --params '{"url":"<overview-url>"}' awslabs.aws-documentation-mcp-server
   ```

3. **Get recommendations** for related topics
   ```bash
   mcptools call recommend --params '{"url":"<overview-url>"}' awslabs.aws-documentation-mcp-server
   ```

4. **Search for specific features** discovered in recommendations
   ```bash
   mcptools call search_documentation --params '{"search_phrase":"DynamoDB Global Tables","limit":10}' awslabs.aws-documentation-mcp-server
   ```

5. **Read detailed documentation** on specific features
   ```bash
   mcptools call read_documentation --params '{"url":"<feature-url>"}' awslabs.aws-documentation-mcp-server
   ```

---

## Best Practices

### Search Strategy

1. **Be specific with search terms** - Include service names and specific features (e.g., "Lambda environment variables" instead of just "environment variables")

2. **Use appropriate limit values** - Start with 10-15 results for initial searches; increase for comprehensive research

3. **Iterate search terms** - If results aren't relevant, try different terminology or more specific queries

4. **Include use case keywords** - Add words like "best practices," "tutorial," "example," or "troubleshooting" to find specific content types

### Reading Documentation

1. **Read search results first** - Review search result snippets before reading full pages to identify most relevant content

2. **Follow recommendations** - Use the recommend tool to discover related documentation you might have missed

3. **Read in logical order** - Start with overview/introduction pages before diving into detailed API references

4. **Bookmark important URLs** - Save URLs of frequently accessed documentation pages

### Using Architecture Guidance

1. **Start with high-level requirements** - Provide clear, concise descriptions of what you want to build

2. **Include constraints** - Mention requirements like "serverless," "low cost," "high availability," etc.

3. **Follow up with documentation** - After getting service recommendations, search for documentation on those services

4. **Iterate on guidance** - Ask follow-up questions to refine service recommendations

### Regional Considerations

1. **Check region availability** - Not all services are available in all regions; verify in documentation

2. **Use get_available_services for China** - When working with China regions, check service availability explicitly

3. **Note partition differences** - Some tools (search, recommend) only work with global partition

---

## Error Handling

### Common Issues

**1. Search returns no results**
- Try broader search terms
- Check spelling of service names
- Remove overly specific filters

**2. Documentation URL cannot be read**
- Verify the URL is from docs.aws.amazon.com
- Check if the page exists (may have been moved or deprecated)
- Ensure URL is complete and properly formatted

**3. Tool not available**
- Verify MCP server is configured correctly
- Check that mcptools is installed: `~/go/bin/mcptools --version`
- Test MCP server connection: `mcptools tools awslabs.aws-documentation-mcp-server`

**4. China partition tools don't work**
- Verify server is configured for correct partition
- Use get_available_services only with China partition
- Use search_documentation and recommend only with global partition

### Troubleshooting Steps

1. **Test MCP server availability**
   ```bash
   mcptools tools awslabs.aws-documentation-mcp-server
   mcptools tools awslabs.core-mcp-server
   ```

2. **Verify mcptools installation**
   ```bash
   ~/go/bin/mcptools --version
   ```

3. **Check MCP server configuration** in settings file

4. **Try simple test call**
   ```bash
   mcptools call search_documentation --params '{"search_phrase":"S3","limit":5}' awslabs.aws-documentation-mcp-server
   ```

---

## When to Use This Skill

Use this skill when:
- Looking up AWS service documentation, user guides, or tutorials
- Finding API references for AWS services
- Searching for AWS best practices and optimization guides
- Researching AWS service features and capabilities
- Getting AWS architecture recommendations and service suggestions
- Finding code examples and configuration guides from AWS
- Exploring AWS service limits, quotas, and restrictions
- Discovering related AWS services and integration patterns
- Verifying AWS service availability in specific regions
- Learning about new AWS services or features

## When NOT to Use This Skill

Do NOT use this skill for:
- Internal Amazon documentation (use read-internal-amazon-documents skill instead)
- Non-AWS documentation or third-party services
- Searching general web content (use WebFetch or WebSearch instead)
- Local file operations
- Private or custom documentation not hosted by AWS
- Community forums, blogs, or unofficial AWS content
- AWS service console access (this is for documentation only)
