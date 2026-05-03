# Glue Worker Types

Reference table of AWS Glue worker types with their vCPU, memory, and typical use cases.

| Worker type | vCPU | Memory | Use case |
|-------------|------|--------|----------|
| G.025X | 2 | 4 GB | Micro/dev jobs |
| G.1X | 4 | 16 GB | Standard (default) |
| G.2X | 8 | 32 GB | Memory-intensive transforms |
| G.4X | 16 | 64 GB | Heavy aggregations/joins |
| G.8X | 32 | 128 GB | Large-scale ML/compute |

## Sizing guidance

- Start with G.1X and the minimum number of workers. Profile with CloudWatch metrics first.
- Scale up worker **type** before scaling out worker **count** — vertical scaling is cheaper per unit of work.
- Enable auto-scaling to avoid paying for idle executors:

```bash
aws glue create-job \
  --name "$JOB_NAME" \
  --number-of-workers 20 \
  --default-arguments '{"--enable-auto-scaling": "true"}' \
  ...
```

With auto-scaling, `NumberOfWorkers` becomes the maximum; Glue scales down workers that have been idle.
