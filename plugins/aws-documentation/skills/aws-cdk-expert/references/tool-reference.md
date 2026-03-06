# AWS CDK MCP Server - Tool Reference

Complete documentation for all 7 tools provided by the `awslabs.cdk-mcp-server` MCP server.

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
