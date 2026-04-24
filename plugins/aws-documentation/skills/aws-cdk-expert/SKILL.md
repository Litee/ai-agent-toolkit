---
name: aws-cdk-expert
description: Use when building AWS CDK infrastructure, finding Solutions Construct patterns, discovering GenAI constructs, generating Bedrock agent schemas, or validating CDK Nag security rules and suppressions.
---

# AWS CDK Expert

## Purpose

This skill provides expert guidance for AWS Cloud Development Kit (CDK) development using the awslabs CDK MCP server. Use this skill to get prescriptive advice for building AWS applications, discover vetted architecture patterns, find GenAI constructs, generate Bedrock agent schemas, access Lambda layer documentation, and understand CDK Nag security rules.

## Prerequisites

- mcptools CLI (typically installed at `~/go/bin/mcptools`)
- uvx (Python package runner, installed via `pip install uv`)
- Python 3.10+
- Network access to download `awslabs.cdk-mcp-server` from PyPI

## Available MCP Tools

The awslabs CDK MCP server provides seven specialized tools for AWS CDK development.

For complete tool documentation and examples, see `references/tool-reference.md`.

| # | Tool | Description | Primary Use Case |
|---|------|-------------|-----------------|
| 1 | **CDKGeneralGuidance** | Get prescriptive advice for building AWS applications with CDK | Starting a new CDK project; understanding workflow, patterns, and security |
| 2 | **GetAwsSolutionsConstructPattern** | Find vetted architecture patterns combining AWS services | Discovering pre-built patterns before building from scratch |
| 3 | **SearchGenAICDKConstructs** | Discover GenAI CDK constructs by name or features | Finding Bedrock, SageMaker, or RAG constructs for AI/ML workloads |
| 4 | **GenerateBedrockAgentSchema** | Create OpenAPI schemas for Bedrock Agent action groups from Lambda code | Generating action group schemas for Bedrock Agents |
| 5 | **LambdaLayerDocumentationProvider** | Access documentation for Lambda layers implementation | Getting directory structure guidance and runtime-specific layer setup |
| 6 | **ExplainCDKNagRule** | Get detailed guidance on CDK Nag security rules | Understanding why a specific Nag rule exists before suppressing it |
| 7 | **CheckCDKNagSuppressions** | Validate CDK Nag suppressions in code | Reviewing suppression justifications for compliance |

---

## Common Workflows

### Workflow 1: Building a New CDK Application

1. **Get comprehensive CDK guidance**
   ```bash
   mcptools call CDKGeneralGuidance --params '{}' uvx awslabs.cdk-mcp-server@latest
   ```

2. **Find relevant AWS Solutions Construct patterns**
   ```bash
   mcptools call GetAwsSolutionsConstructPattern --params '{}' uvx awslabs.cdk-mcp-server@latest
   ```

3. **Get specific pattern implementation**
   ```bash
   mcptools call GetAwsSolutionsConstructPattern --params '{"pattern":"aws-apigateway-lambda"}' uvx awslabs.cdk-mcp-server@latest
   ```

### Workflow 2: Implementing GenAI Features

1. **Search for GenAI constructs**
   ```bash
   mcptools call SearchGenAICDKConstructs --params '{"query":"bedrock agent"}' uvx awslabs.cdk-mcp-server@latest
   ```

2. **Generate Bedrock Agent schema from Lambda code**
   ```bash
   mcptools call GenerateBedrockAgentSchema --params '{"lambdaCode":"<lambda-code>"}' uvx awslabs.cdk-mcp-server@latest
   ```

### Workflow 3: Working with Lambda Layers

1. **Get Lambda layer documentation**
   ```bash
   mcptools call LambdaLayerDocumentationProvider --params '{"topic":"python"}' uvx awslabs.cdk-mcp-server@latest
   ```

### Workflow 4: Security Compliance with CDK Nag

1. **Explain specific CDK Nag rules** before suppressing
   ```bash
   mcptools call ExplainCDKNagRule --params '{"rule_id":"AwsSolutions-IAM4"}' uvx awslabs.cdk-mcp-server@latest
   ```

2. **Validate suppressions in code**
   ```bash
   mcptools call CheckCDKNagSuppressions --params '{"code":"<cdk-code-with-suppressions>"}' uvx awslabs.cdk-mcp-server@latest
   ```

---

## Best Practices

### Using CDK Guidance Effectively

> **Version pinning**: Examples use `@latest`. For reproducible builds, pin to a specific version (e.g., `uvx awslabs.cdk-mcp-server@0.1.2`) once you confirm it works.

1. **Read comprehensive guidance** - Use CDKGeneralGuidance to get complete documentation on CDK best practices, workflow, patterns, and security
2. **Start with patterns** - Use GetAwsSolutionsConstructPattern to find vetted patterns before building from scratch
3. **Leverage GenAI constructs** - Search for existing GenAI constructs before implementing custom solutions
4. **Document suppressions** - Always provide clear justification for CDK Nag suppressions

### CDK Nag Compliance

1. **Understand rules before suppressing** - Use ExplainCDKNagRule to understand why a rule exists
2. **Review suppressions regularly** - Use CheckCDKNagSuppressions to validate existing suppressions
3. **Follow Well-Architected principles** - Align CDK implementations with AWS Well-Architected Framework

### Lambda Layer Management

1. **Check documentation first** - Use LambdaLayerDocumentationProvider before implementing custom layers
2. **Follow directory structure guidelines** - Proper structure ensures compatibility across runtimes

---

## Troubleshooting

### The MCP server times out or fails to initialize

**Possible causes:**
- Slow network connection downloading Python package
- uvx not installed or not in PATH
- Python 3.10+ not installed

**Solutions:**
1. Verify uvx is installed: `uvx --version` (install with `pip install uv` if missing)
2. Verify Python 3.10+: `python3 --version`
3. Increase timeout if needed
4. Try running the server directly first: `uvx awslabs.cdk-mcp-server@latest`

### Tool returns no results or empty response

**Possible causes:**
- Invalid parameter values
- Pattern or rule name doesn't exist
- Missing required parameters

**Solutions:**
1. Verify parameter names and values are correct
2. For GetAwsSolutionsConstructPattern, call with empty params first to list available patterns
3. For ExplainCDKNagRule, verify the rule ID format (e.g., "AwsSolutions-IAM4")
4. Check JSON formatting in parameters

### GenerateBedrockAgentSchema fails

**Possible causes:**
- Lambda code doesn't use BedrockAgentResolver
- Invalid Python syntax in lambda code
- Missing imports or dependencies

**Solutions:**
1. Ensure Lambda function imports and uses BedrockAgentResolver from AWS Lambda Powertools
2. Validate Python syntax before submitting
3. If the tool returns a fallback script, the dependencies may be missing

### mcptools not found

**Possible causes:**
- mcptools not installed
- mcptools not in PATH

**Solutions:**
1. Check if mcptools exists: `ls ~/go/bin/mcptools`
2. Use full path: `~/go/bin/mcptools call <tool-name> ...`
3. Add to PATH: `export PATH="$HOME/go/bin:$PATH"`

---

## When to Use This Skill

Use this skill when:
- Building AWS infrastructure with CDK
- Seeking best practices for CDK application architecture
- Finding pre-built Solutions Constructs patterns
- Implementing GenAI features with Bedrock or SageMaker
- Generating OpenAPI schemas for Bedrock Agents
- Setting up Lambda layers
- Understanding or fixing CDK Nag security rule violations
- Validating CDK Nag suppression justifications
- Learning CDK patterns and best practices

Do NOT use this skill for:
- AWS CloudFormation (not CDK) - use AWS documentation instead
- Terraform or other IaC tools - CDK-specific guidance only
- Runtime application code - this is for infrastructure code
- Non-AWS cloud providers
