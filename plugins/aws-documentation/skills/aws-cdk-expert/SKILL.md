---
name: aws-cdk-expert
description: This skill should be used when working with AWS CDK infrastructure, including getting CDK guidance, finding architecture patterns, discovering GenAI constructs, generating Bedrock agent schemas, Lambda layer documentation, and CDK Nag security rules. Use when building CDK applications, validating CDK Nag suppressions, or seeking AWS Solutions Constructs patterns.
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

The awslabs CDK MCP server provides seven specialized tools for AWS CDK development:

1. **CDKGeneralGuidance** - Get prescriptive advice for building AWS applications with CDK
2. **GetAwsSolutionsConstructPattern** - Find vetted architecture patterns combining AWS services
3. **SearchGenAICDKConstructs** - Discover GenAI CDK constructs by name or features
4. **GenerateBedrockAgentSchema** - Create OpenAPI schemas for Bedrock Agent action groups
5. **LambdaLayerDocumentationProvider** - Access documentation for Lambda layers implementation
6. **ExplainCDKNagRule** - Get detailed guidance on CDK Nag security rules
7. **CheckCDKNagSuppressions** - Validate CDK Nag suppressions in code

---

## Tool 1: CDKGeneralGuidance

Get comprehensive prescriptive advice for building AWS applications with CDK, incorporating security automation and best practices guidance. Returns detailed documentation covering CDK development workflow, architecture patterns, security best practices, and tool selection guidance.

### Usage

```bash
mcptools call CDKGeneralGuidance --params '{}' uvx awslabs.cdk-mcp-server@latest
```

### Parameters

No parameters required - returns comprehensive CDK guidance covering:
- Getting started with CDK
- Development workflow (cdk synth, cdk deploy, cdk diff)
- AWS Solutions Constructs for common patterns
- GenAI CDK Constructs for AI/ML workloads
- Security with CDK Nag
- Lambda Powertools integration
- Tool selection guide

### Example

**Get comprehensive CDK guidance**
```bash
mcptools call CDKGeneralGuidance --params '{}' uvx awslabs.cdk-mcp-server@latest
```

---

## Tool 2: GetAwsSolutionsConstructPattern

Find vetted architecture patterns combining AWS services from the AWS Solutions Constructs library. AWS Solutions Constructs are pre-built, well-architected patterns that combine multiple AWS services.

### Usage

```bash
mcptools call GetAwsSolutionsConstructPattern --params '{"pattern":"pattern-name"}' uvx awslabs.cdk-mcp-server@latest
```

### Parameters

- **pattern** (optional, string): The specific Solutions Construct pattern name to retrieve
- If no pattern is specified, returns a list of available patterns

### Examples

**Example 1: List available patterns**
```bash
mcptools call GetAwsSolutionsConstructPattern --params '{}' uvx awslabs.cdk-mcp-server@latest
```

**Example 2: Get serverless API pattern**
```bash
mcptools call GetAwsSolutionsConstructPattern --params '{"pattern":"aws-apigateway-lambda"}' uvx awslabs.cdk-mcp-server@latest
```

**Example 3: Get S3-Lambda pattern**
```bash
mcptools call GetAwsSolutionsConstructPattern --params '{"pattern":"aws-s3-lambda"}' uvx awslabs.cdk-mcp-server@latest
```

**Example 4: Get event-driven pattern**
```bash
mcptools call GetAwsSolutionsConstructPattern --params '{"pattern":"aws-eventbridge-lambda"}' uvx awslabs.cdk-mcp-server@latest
```

---

## Tool 3: SearchGenAICDKConstructs

Discover GenAI CDK constructs by name or features. Locates specialized constructs designed for AI/ML workloads, providing implementation guidance for generative AI applications.

### Usage

```bash
mcptools call SearchGenAICDKConstructs --params '{"query":"search terms"}' uvx awslabs.cdk-mcp-server@latest
```

### Parameters

- **query** (required, string): Search terms to find GenAI constructs (e.g., "bedrock", "sagemaker", "agent")

### Examples

**Example 1: Find Bedrock constructs**
```bash
mcptools call SearchGenAICDKConstructs --params '{"query":"bedrock"}' uvx awslabs.cdk-mcp-server@latest
```

**Example 2: Find agent constructs**
```bash
mcptools call SearchGenAICDKConstructs --params '{"query":"agent"}' uvx awslabs.cdk-mcp-server@latest
```

**Example 3: Find RAG constructs**
```bash
mcptools call SearchGenAICDKConstructs --params '{"query":"rag"}' uvx awslabs.cdk-mcp-server@latest
```

**Example 4: Find SageMaker constructs**
```bash
mcptools call SearchGenAICDKConstructs --params '{"query":"sagemaker"}' uvx awslabs.cdk-mcp-server@latest
```

---

## Tool 4: GenerateBedrockAgentSchema

Create OpenAPI schemas for Bedrock Agent action groups from Lambda function code. Converts Lambda function files into OpenAPI specifications compatible with Bedrock Agents. Requires Lambda functions using `BedrockAgentResolver` from AWS Lambda Powertools.

### Usage

```bash
mcptools call GenerateBedrockAgentSchema --params '{"lambdaCode":"lambda function code"}' uvx awslabs.cdk-mcp-server@latest
```

### Parameters

- **lambdaCode** (required, string): The complete Lambda function code that uses BedrockAgentResolver

### Examples

**Example 1: Generate schema from Lambda code**
```bash
mcptools call GenerateBedrockAgentSchema --params '{"lambdaCode":"from aws_lambda_powertools.event_handler import BedrockAgentResolver\napp = BedrockAgentResolver()\n@app.get(\"/hello\")\ndef hello():\n    return {\"message\": \"Hello World\"}"}' uvx awslabs.cdk-mcp-server@latest
```

### Important Notes

- The Lambda function must use `BedrockAgentResolver` from AWS Lambda Powertools
- If import errors occur, the tool generates a fallback script
- Use this tool to streamline schema creation for Bedrock Agents with Action Groups

---

## Tool 5: LambdaLayerDocumentationProvider

Access comprehensive documentation for Lambda layers implementation, including code examples and directory structures.

### Usage

```bash
mcptools call LambdaLayerDocumentationProvider --params '{"topic":"topic name"}' uvx awslabs.cdk-mcp-server@latest
```

### Parameters

- **topic** (optional, string): Specific topic for Lambda layers documentation (e.g., "python", "structure", "deployment")
- If no topic is specified, returns general Lambda layer documentation

### Examples

**Example 1: General Lambda layer documentation**
```bash
mcptools call LambdaLayerDocumentationProvider --params '{}' uvx awslabs.cdk-mcp-server@latest
```

**Example 2: Python-specific Lambda layer guidance**
```bash
mcptools call LambdaLayerDocumentationProvider --params '{"topic":"python"}' uvx awslabs.cdk-mcp-server@latest
```

**Example 3: Lambda layer directory structure**
```bash
mcptools call LambdaLayerDocumentationProvider --params '{"topic":"structure"}' uvx awslabs.cdk-mcp-server@latest
```

---

## Tool 6: ExplainCDKNagRule

Get detailed guidance on specific CDK Nag security rules, connecting security warnings to AWS Well-Architected Framework principles.

### Usage

```bash
mcptools call ExplainCDKNagRule --params '{"rule_id":"rule-id"}' uvx awslabs.cdk-mcp-server@latest
```

### Parameters

- **rule_id** (required, string): The CDK Nag rule ID (e.g., "AwsSolutions-IAM4", "AwsSolutions-S1")

### Examples

**Example 1: Explain IAM managed policy rule**
```bash
mcptools call ExplainCDKNagRule --params '{"rule_id":"AwsSolutions-IAM4"}' uvx awslabs.cdk-mcp-server@latest
```

**Example 2: Explain S3 bucket encryption rule**
```bash
mcptools call ExplainCDKNagRule --params '{"rule_id":"AwsSolutions-S1"}' uvx awslabs.cdk-mcp-server@latest
```

**Example 3: Explain CloudWatch logging rule**
```bash
mcptools call ExplainCDKNagRule --params '{"rule_id":"AwsSolutions-L1"}' uvx awslabs.cdk-mcp-server@latest
```

### Common CDK Nag Rules

- **AwsSolutions-IAM4** - IAM user, role, or group uses AWS managed policies
- **AwsSolutions-IAM5** - IAM entity contains wildcard permissions
- **AwsSolutions-S1** - S3 bucket does not have server access logs enabled
- **AwsSolutions-L1** - Lambda function not using latest runtime version
- **AwsSolutions-EC23** - Security group allows ingress from 0.0.0.0/0

---

## Tool 7: CheckCDKNagSuppressions

Validate CDK Nag suppressions in code to ensure compliance standards are maintained. Scans CDK code to identify suppressions requiring human review.

### Usage

```bash
mcptools call CheckCDKNagSuppressions --params '{"code":"cdk code with suppressions"}' uvx awslabs.cdk-mcp-server@latest
```

### Parameters

- **code** (required, string): The CDK code containing Nag suppressions to validate

### Examples

**Example 1: Check suppressions in CDK code**
```bash
mcptools call CheckCDKNagSuppressions --params '{"code":"import * as cdk from '\''aws-cdk-lib'\'';\nimport { NagSuppressions } from '\''cdk-nag'\'';\nNagSuppressions.addResourceSuppressions(bucket, [{id: '\''AwsSolutions-S1'\'', reason: '\''Demo bucket'\''}]);"}' uvx awslabs.cdk-mcp-server@latest
```

### Important Notes

- This tool reviews suppression justifications for compliance
- Helps identify suppressions that may need better justification or removal
- Ensures security standards are not bypassed without proper reasoning

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

3. **Get CDK guidance on best practices**
   ```bash
   mcptools call CDKGeneralGuidance --params '{}' uvx awslabs.cdk-mcp-server@latest
   ```

### Workflow 3: Working with Lambda Layers

1. **Get Lambda layer documentation**
   ```bash
   mcptools call LambdaLayerDocumentationProvider --params '{"topic":"python"}' uvx awslabs.cdk-mcp-server@latest
   ```

2. **Get CDK guidance on best practices**
   ```bash
   mcptools call CDKGeneralGuidance --params '{}' uvx awslabs.cdk-mcp-server@latest
   ```

### Workflow 4: Security Compliance with CDK Nag

1. **Explain specific CDK Nag rules**
   ```bash
   mcptools call ExplainCDKNagRule --params '{"rule_id":"AwsSolutions-IAM4"}' uvx awslabs.cdk-mcp-server@latest
   ```

2. **Check suppressions in code**
   ```bash
   mcptools call CheckCDKNagSuppressions --params '{"code":"<cdk-code-with-suppressions>"}' uvx awslabs.cdk-mcp-server@latest
   ```

3. **Get CDK guidance including suppression best practices**
   ```bash
   mcptools call CDKGeneralGuidance --params '{}' uvx awslabs.cdk-mcp-server@latest
   ```

---

## Best Practices

### Using CDK Guidance Effectively

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
