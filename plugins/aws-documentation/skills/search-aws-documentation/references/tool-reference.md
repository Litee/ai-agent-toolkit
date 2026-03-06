# AWS Documentation MCP Tools - Full Reference

This file contains the complete documentation for Tools 2-5 of the search-aws-documentation skill. For the primary tool (`prompt_understanding`) and workflow guidance, see `SKILL.md`.

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

### Supported URL Patterns

The tool works with documentation URLs from:
- `https://docs.aws.amazon.com/` - Primary AWS documentation
- Service-specific documentation subdomains
- API reference pages
- User guides and tutorials

### Usage

```bash
mcptools call read_documentation --params '{"url":"https://docs.aws.amazon.com/path/to/page.html"}' awslabs.aws-documentation-mcp-server
```

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
