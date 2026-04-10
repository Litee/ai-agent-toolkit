# AWS Service Quotas — Best Practices

## Quota Request Status Lifecycle

Service Quota increase requests move through these statuses:

```
PENDING
  └─> CASE_OPENED       (AWS opened a support case to review the request)
        ├─> APPROVED     (request granted; quota is being increased)
        ├─> DENIED       (request rejected by AWS)
        ├─> NOT_APPROVED (request not approved — functionally similar to DENIED)
        └─> CASE_CLOSED  (the support case was closed — see note below)
```

**Terminal statuses** (no further changes expected):
`APPROVED`, `DENIED`, `NOT_APPROVED`, `CASE_CLOSED`

### `CASE_CLOSED` vs `DENIED` vs `NOT_APPROVED`

- **`CASE_CLOSED`**: The underlying support case was closed. This does not always mean
  the request was denied — AWS may close a case after approving it, or close it for
  administrative reasons. Check the quota value itself to confirm whether the increase
  was applied:
  ```bash
  aws service-quotas get-service-quota --service-code ec2 --quota-code L-1216C47A \
      --profile myprofile --region us-east-1
  ```
- **`DENIED`**: AWS explicitly rejected the request.
- **`NOT_APPROVED`**: Similar to DENIED; used for requests that do not meet approval criteria.

---

## Finding Request IDs

List all quota change requests in a region:

```bash
aws service-quotas list-requested-service-quota-changes \
    --profile myprofile --region us-east-1
```

Filter by service:

```bash
aws service-quotas list-requested-service-quota-changes-by-service \
    --service-code ec2 \
    --profile myprofile --region us-east-1
```

Filter by status (PENDING, CASE_OPENED, APPROVED, DENIED, NOT_APPROVED, CASE_CLOSED):

```bash
aws service-quotas list-requested-service-quota-changes \
    --status PENDING \
    --profile myprofile --region us-east-1
```

Get a specific request by ID:

```bash
aws service-quotas get-requested-service-quota-change \
    --request-id req-abc1234567890 \
    --profile myprofile --region us-east-1
```

---

## Finding Service and Quota Codes

List all services with quotas:

```bash
aws service-quotas list-services \
    --profile myprofile --region us-east-1
```

List all quotas for a service (e.g. EC2):

```bash
aws service-quotas list-service-quotas \
    --service-code ec2 \
    --profile myprofile --region us-east-1
```

List quotas that can be increased:

```bash
aws service-quotas list-service-quotas \
    --service-code ec2 --query 'Quotas[?Adjustable==`true`]' \
    --profile myprofile --region us-east-1
```

---

## Reading Current Quota Values

Get the current applied quota value (may differ from the AWS default if previously increased):

```bash
aws service-quotas get-service-quota \
    --service-code ec2 \
    --quota-code L-1216C47A \
    --profile myprofile --region us-east-1
```

Get the AWS default (unadjusted) value:

```bash
aws service-quotas get-aws-default-service-quota \
    --service-code ec2 \
    --quota-code L-1216C47A \
    --profile myprofile
```

---

## Requesting a Quota Increase

```bash
aws service-quotas request-service-quota-increase \
    --service-code ec2 \
    --quota-code L-1216C47A \
    --desired-value 256 \
    --profile myprofile --region us-east-1
```

The response includes the `RequestId` — save it to track with this watcher.

---

## Common Quota Codes

### Amazon EC2

| Quota Name | Quota Code |
|---|---|
| Running On-Demand Standard (A, C, D, H, I, M, R, T, Z) instances | `L-1216C47A` |
| Running On-Demand G and VT instances | `L-DB2E81BA` |
| Running On-Demand P instances | `L-417A185B` |
| EC2-VPC Elastic IPs | `L-0263D0A3` |
| vCPUs for Standard instance family | `L-1216C47A` |

### Elastic Load Balancing

| Quota Name | Quota Code |
|---|---|
| Application Load Balancers per Region | `L-53DA6B97` |
| Network Load Balancers per Region | `L-69A177A2` |
| Classic Load Balancers per Region | `L-E9E9831D` |

### Amazon VPC

| Quota Name | Quota Code |
|---|---|
| VPCs per Region | `L-F678F1CE` |
| Subnets per VPC | `L-407747CB` |
| Security groups per VPC | `L-E79EC624` |
| NAT gateways per Availability Zone | `L-FE5A380F` |

### AWS Lambda

| Quota Name | Quota Code |
|---|---|
| Concurrent executions | `L-B99A9384` |
| Function and layer storage | `L-2ACBD22F` |
| Elastic network interfaces per VPC | `L-9FEE3D26` |

---

## Regional Considerations

Service Quota requests are **region-specific**. A quota increase requested in `us-east-1`
does not affect `us-west-2`.

- Always pass `--region` when submitting or querying requests
- Use the watcher's `--region` flag to match the region where the request was submitted
- Global services (e.g. IAM) use `us-east-1` by convention; check the service documentation

To compare quotas across regions:

```bash
for region in us-east-1 us-west-2 eu-west-1; do
  echo "=== $region ==="
  aws service-quotas get-service-quota \
      --service-code ec2 --quota-code L-1216C47A \
      --profile myprofile --region "$region" \
      --query 'Quota.Value' --output text
done
```

---

## API Rate Limiting

The Service Quotas API uses standard AWS throttling. Key considerations:

- `list-requested-service-quota-changes`: moderate rate limit; paginate carefully
- `get-requested-service-quota-change`: low-frequency calls; fine for polling every 10 minutes
- The watcher doubles its poll interval on `ThrottlingException` (capped at 3600s)
- Restart the watcher to reset a throttle-expanded poll interval

If you are watching many requests simultaneously, consider increasing `--poll-interval-seconds`
to reduce API call frequency. Quota requests change slowly (hours to days), so a 600-second
(10-minute) default is more than sufficient.

---

## Useful Patterns

### Check if a quota was applied after APPROVED

After a request reaches `APPROVED`, verify the quota is in effect:

```bash
# Wait a few minutes after APPROVED, then:
aws service-quotas get-service-quota \
    --service-code ec2 \
    --quota-code L-1216C47A \
    --profile myprofile --region us-east-1 \
    --query 'Quota.Value'
```

### List all open requests across services

```bash
aws service-quotas list-requested-service-quota-changes \
    --status PENDING \
    --profile myprofile --region us-east-1 \
    --query 'RequestedQuotas[].{ID:Id,Service:ServiceName,Quota:QuotaName,Desired:DesiredValue,Status:Status}'
```

### Cancel a pending request

```bash
# Not available via AWS CLI directly; cancel via the AWS Console:
# Service Quotas > Quota request history > select request > Request cancellation
```

Note: Cancellation is only possible while the request is in `PENDING` status. Once
`CASE_OPENED`, contact AWS Support directly.
