# Skill Ideas

## AWS Watcher Skills

Existing watchers: `watch-aws-glue-job`, `watch-aws-glue-workflow`, `watch-aws-support-cases`, `watch-aws-quota-requests`.

### Strong Candidates

- **watch-cloudformation-stack** — CloudFormation / CDK stack deployments. `CREATE_IN_PROGRESS` → `UPDATE_COMPLETE` / `ROLLBACK_COMPLETE`, 10–60+ min. Poll `DescribeStackEvents`, surface per-resource events and rollback reasons early. Catches silent mid-deploy rollbacks the console hides.
- **watch-emr-job** — EMR steps / EMR Serverless jobs. Same shape as Glue watcher. Poll `DescribeStep` / `GetJobRun`, surface step failures and logs. States: `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`.
- **watch-sagemaker-job** — SageMaker training / processing / batch transform. Hours to days of runtime. Poll `DescribeTrainingJob` / `DescribeProcessingJob` / `DescribeTransformJob`. Surface training metrics. States: `InProgress`, `Completed`, `Failed`, `Stopped`.
- **watch-step-functions-execution** — Step Functions executions. Tail execution history via `GetExecutionHistory` + `DescribeExecution`; flag first `TaskFailed`. States: `RUNNING`, `SUCCEEDED`, `FAILED`, `TIMED_OUT`, `ABORTED`.
- **watch-athena-query** — Athena query executions. Pairs with existing `query-aws-athena`. Poll `GetQueryExecution`; surface data scanned and cost estimate. States: `QUEUED`, `RUNNING`, `SUCCEEDED`, `FAILED`, `CANCELLED`.
- **watch-codebuild** / **watch-codepipeline** — Long builds with phase-by-phase status. Poll `BatchGetBuilds` / `GetPipelineExecution`; surface phase failures and CloudWatch logs. States (CodeBuild): `IN_PROGRESS`, `SUCCEEDED`, `FAILED`, `TIMED_OUT`, `STOPPED`.

### Decent Candidates

- **watch-rds-operation** — RDS / Aurora snapshot creation, restore, major-version upgrade, Blue/Green switchover. Poll `DescribeDBInstances` / `DescribeDBClusters` status.
- **watch-dms-task** — DMS migration tasks. Full-load + CDC phases, replication lag, error thresholds. `DescribeReplicationTasks` + `DescribeReplicationTaskAssessmentResults`.
- **watch-ecs-deployment** — ECS service deployments / rollouts. Deployment circuit breaker, task count convergence, stalled rollouts. Poll `DescribeServices` deployment list.
- **watch-bedrock-job** — Bedrock batch inference / model customization. Relevant given `dev-ai` profile usage. Poll `GetModelCustomizationJob` / `GetModelInvocationJob`. States: `InProgress`, `Completed`, `Failed`, `Stopping`, `Stopped`.
- **watch-s3-batch-job** — S3 Batch Operations jobs. Hours of runtime over billions of objects. Poll `DescribeJob`; surface `progressSummary` and completion report location.
- **watch-datasync-task** — DataSync task executions. Long transfers with phase transitions. `DescribeTaskExecution` polling.
