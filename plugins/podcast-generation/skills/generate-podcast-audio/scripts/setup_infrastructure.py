#!/usr/bin/env python3
"""
Podcast infrastructure setup script.

Run this once per AWS account/region before generating podcast audio.
Creates all persistent AWS resources needed by generate_podcast_audio.py:

  - S3 bucket for file transfers (with 24-hour lifecycle policy)
  - IAM role for Lambda functions
  - IAM role for Step Functions state machine
  - IAM role and instance profile for EC2 instances
  - Step Functions state machine

Resources are named deterministically from (account_id, region), so this script
is safe to re-run — it will verify existing resources and update policies/state
machine definition without duplicating anything.

Usage:
  python3 setup_infrastructure.py --profile YOUR_PROFILE --region us-west-2
"""

import argparse
import sys
import json
import time
import subprocess
from _podcast_shared import (
    log_progress,
    get_aws_account_id,
    get_bucket_name,
    get_lambda_role_name,
    get_sf_role_name,
    get_ec2_role_name,
    get_ec2_instance_profile_name,
    get_state_machine_name,
)


def ensure_s3_bucket(*, profile: str, region: str, bucket_name: str) -> None:
    """Create S3 bucket if it doesn't exist and configure lifecycle policy."""
    log_progress(f"Checking S3 bucket: {bucket_name}")

    result = subprocess.run([
        "aws", "s3api", "head-bucket",
        "--profile", profile,
        "--bucket", bucket_name
    ], capture_output=True, text=True, timeout=30)

    if result.returncode == 0:
        log_progress(f"S3 bucket already exists: {bucket_name}")
    else:
        log_progress(f"Creating S3 bucket: {bucket_name}")

        create_cmd = [
            "aws", "s3api", "create-bucket",
            "--profile", profile,
            "--bucket", bucket_name,
            "--region", region
        ]

        if region != "us-east-1":
            create_cmd.extend([
                "--create-bucket-configuration",
                f"LocationConstraint={region}"
            ])

        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            raise Exception(f"Failed to create S3 bucket: {result.stderr}")

        log_progress(f"S3 bucket created: {bucket_name}")

    configure_s3_lifecycle_policy(profile=profile, bucket_name=bucket_name)


def configure_s3_lifecycle_policy(*, profile: str, bucket_name: str) -> None:
    """Configure S3 lifecycle policy to delete objects after 24 hours."""
    log_progress(f"Configuring lifecycle policy for bucket: {bucket_name}")

    lifecycle_config = {
        "Rules": [
            {
                "Id": "DeleteGeneratedFilesAfter24Hours",
                "Status": "Enabled",
                "Filter": {},
                "Expiration": {
                    "Days": 1
                }
            }
        ]
    }

    config_file = f"/tmp/s3-lifecycle-{bucket_name}.json"
    try:
        with open(config_file, 'w') as f:
            json.dump(lifecycle_config, f)

        result = subprocess.run([
            "aws", "s3api", "put-bucket-lifecycle-configuration",
            "--profile", profile,
            "--bucket", bucket_name,
            "--lifecycle-configuration", f"file://{config_file}"
        ], capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            log_progress(f"Warning: Failed to configure lifecycle policy: {result.stderr}", "WARNING")
        else:
            log_progress("Lifecycle policy configured: objects expire after 1 day")

    except Exception as e:
        log_progress(f"Warning: Failed to configure lifecycle policy: {e}", "WARNING")

    finally:
        try:
            import os
            if os.path.exists(config_file):
                os.remove(config_file)
        except Exception:
            pass


def create_lambda_execution_role(*, profile: str, region: str, account_id: str) -> str:
    """Create IAM role for Lambda functions used in Step Functions. Returns role ARN."""
    role_name = get_lambda_role_name(account_id, region)
    log_progress(f"Checking Lambda execution role: {role_name}")

    result = subprocess.run([
        "aws", "iam", "get-role",
        "--profile", profile,
        "--role-name", role_name
    ], capture_output=True, text=True, timeout=30)

    role_already_existed = result.returncode == 0

    if role_already_existed:
        role_arn = json.loads(result.stdout)['Role']['Arn']
        log_progress(f"Lambda role already exists: {role_arn}")
    else:
        log_progress(f"Creating Lambda execution role: {role_name}")

        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }

        trust_policy_file = f"/tmp/lambda-trust-policy-{account_id}.json"
        with open(trust_policy_file, 'w') as f:
            json.dump(trust_policy, f)

        result = subprocess.run([
            "aws", "iam", "create-role",
            "--profile", profile,
            "--role-name", role_name,
            "--assume-role-policy-document", f"file://{trust_policy_file}"
        ], capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            raise Exception(f"Failed to create Lambda role: {result.stderr}")

        role_arn = json.loads(result.stdout)['Role']['Arn']

    subprocess.run([
        "aws", "iam", "attach-role-policy",
        "--profile", profile,
        "--role-name", role_name,
        "--policy-arn", "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
    ], capture_output=True, text=True, timeout=30)

    inline_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "ec2:*", "s3:*", "ssm:*",
                    "iam:GetRole", "iam:CreateRole", "iam:AttachRolePolicy",
                    "iam:PutRolePolicy", "iam:GetInstanceProfile",
                    "iam:CreateInstanceProfile", "iam:AddRoleToInstanceProfile",
                    "sts:GetCallerIdentity"
                ],
                "Resource": "*"
            }
        ]
    }

    policy_file = f"/tmp/lambda-inline-policy-{account_id}.json"
    with open(policy_file, 'w') as f:
        json.dump(inline_policy, f)

    subprocess.run([
        "aws", "iam", "put-role-policy",
        "--profile", profile,
        "--role-name", role_name,
        "--policy-name", "PodcastGenerationAccess",
        "--policy-document", f"file://{policy_file}"
    ], capture_output=True, text=True, timeout=30)

    if role_already_existed:
        log_progress(f"Lambda role policies ensured: {role_arn}")
    else:
        log_progress(f"Lambda role created: {role_arn}")
        log_progress("Waiting for IAM role to propagate...")
        time.sleep(10)

    return role_arn


def create_step_functions_role(*, profile: str, region: str, account_id: str) -> str:
    """Create IAM role for Step Functions state machine. Returns role ARN."""
    role_name = get_sf_role_name(account_id, region)
    log_progress(f"Checking Step Functions role: {role_name}")

    result = subprocess.run([
        "aws", "iam", "get-role",
        "--profile", profile,
        "--role-name", role_name
    ], capture_output=True, text=True, timeout=30)

    role_already_existed = result.returncode == 0

    if role_already_existed:
        role_arn = json.loads(result.stdout)['Role']['Arn']
        log_progress(f"Step Functions role already exists: {role_arn}")
    else:
        log_progress(f"Creating Step Functions role: {role_name}")

        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "states.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }

        trust_policy_file = f"/tmp/sf-trust-policy-{account_id}.json"
        with open(trust_policy_file, 'w') as f:
            json.dump(trust_policy, f)

        result = subprocess.run([
            "aws", "iam", "create-role",
            "--profile", profile,
            "--role-name", role_name,
            "--assume-role-policy-document", f"file://{trust_policy_file}"
        ], capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            raise Exception(f"Failed to create Step Functions role: {result.stderr}")

        role_arn = json.loads(result.stdout)['Role']['Arn']

    inline_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "lambda:InvokeFunction", "ec2:*", "ssm:*",
                    "s3:*", "iam:PassRole", "logs:*"
                ],
                "Resource": "*"
            }
        ]
    }

    policy_file = f"/tmp/sf-inline-policy-{account_id}.json"
    with open(policy_file, 'w') as f:
        json.dump(inline_policy, f)

    subprocess.run([
        "aws", "iam", "put-role-policy",
        "--profile", profile,
        "--role-name", role_name,
        "--policy-name", "StepFunctionsExecution",
        "--policy-document", f"file://{policy_file}"
    ], capture_output=True, text=True, timeout=30)

    if role_already_existed:
        log_progress(f"Step Functions role policies ensured: {role_arn}")
    else:
        log_progress(f"Step Functions role created: {role_arn}")
        log_progress("Waiting for IAM role to propagate...")
        time.sleep(10)

    return role_arn


def create_ec2_role(*, profile: str, region: str, account_id: str) -> tuple[str, str]:
    """Create IAM role and instance profile for EC2. Returns (role_arn, instance_profile_name)."""
    role_name = get_ec2_role_name(account_id, region)
    instance_profile_name = get_ec2_instance_profile_name(account_id, region)
    log_progress(f"Checking EC2 role: {role_name}")

    result = subprocess.run([
        "aws", "iam", "get-role",
        "--profile", profile,
        "--role-name", role_name
    ], capture_output=True, text=True, timeout=30)

    role_already_existed = result.returncode == 0

    if role_already_existed:
        role_arn = json.loads(result.stdout)['Role']['Arn']
        log_progress(f"EC2 role already exists: {role_arn}")
    else:
        log_progress(f"Creating EC2 role: {role_name}")

        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "ec2.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }

        trust_policy_file = f"/tmp/ec2-trust-policy-{account_id}.json"
        with open(trust_policy_file, 'w') as f:
            json.dump(trust_policy, f)

        result = subprocess.run([
            "aws", "iam", "create-role",
            "--profile", profile,
            "--role-name", role_name,
            "--assume-role-policy-document", f"file://{trust_policy_file}"
        ], capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            raise Exception(f"Failed to create EC2 role: {result.stderr}")

        role_arn = json.loads(result.stdout)['Role']['Arn']

    subprocess.run([
        "aws", "iam", "attach-role-policy",
        "--profile", profile,
        "--role-name", role_name,
        "--policy-arn", "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
    ], capture_output=True, text=True, timeout=30)

    inline_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "cloudwatch:PutMetricData",
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": "*"
            }
        ]
    }

    policy_file = f"/tmp/ec2-inline-policy-{account_id}.json"
    with open(policy_file, 'w') as f:
        json.dump(inline_policy, f)

    subprocess.run([
        "aws", "iam", "put-role-policy",
        "--profile", profile,
        "--role-name", role_name,
        "--policy-name", "PodcastAccessPolicy",
        "--policy-document", f"file://{policy_file}"
    ], capture_output=True, text=True, timeout=30)

    result = subprocess.run([
        "aws", "iam", "get-instance-profile",
        "--profile", profile,
        "--instance-profile-name", instance_profile_name
    ], capture_output=True, text=True, timeout=30)

    instance_profile_already_existed = result.returncode == 0

    if instance_profile_already_existed:
        log_progress(f"EC2 instance profile already exists: {instance_profile_name}")
    else:
        log_progress(f"Creating EC2 instance profile: {instance_profile_name}")

        result = subprocess.run([
            "aws", "iam", "create-instance-profile",
            "--profile", profile,
            "--instance-profile-name", instance_profile_name
        ], capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            raise Exception(f"Failed to create instance profile: {result.stderr}")

        result = subprocess.run([
            "aws", "iam", "add-role-to-instance-profile",
            "--profile", profile,
            "--instance-profile-name", instance_profile_name,
            "--role-name", role_name
        ], capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            raise Exception(f"Failed to add role to instance profile: {result.stderr}")

    created_new = not role_already_existed or not instance_profile_already_existed

    if role_already_existed and instance_profile_already_existed:
        log_progress(f"EC2 role and instance profile policies ensured: {role_arn}")
    elif created_new:
        log_progress(f"EC2 role and instance profile ready: {role_arn}")
        log_progress("Waiting for IAM role to propagate...")
        time.sleep(30)

    return role_arn, instance_profile_name


def get_state_machine_definition() -> dict:
    """Generate Step Functions state machine ASL definition."""
    return {
        "Comment": "Podcast Audio Generation Workflow with Automatic Cleanup",
        "StartAt": "ValidateAndSetup",
        "States": {
            "ValidateAndSetup": {
                "Type": "Pass",
                "Comment": "Initial validation and setup",
                "Result": {
                    "Timestamp": "$.timestamp",
                    "SetupComplete": True
                },
                "ResultPath": "$.setup",
                "Next": "CreateS3Bucket"
            },

            "CreateS3Bucket": {
                "Type": "Task",
                "Comment": "Create or verify S3 bucket for file transfers",
                "Resource": "arn:aws:states:::aws-sdk:s3:headBucket",
                "Parameters": {
                    "Bucket.$": "$.bucketName"
                },
                "ResultPath": "$.s3BucketCheck",
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "ResultPath": "$.error",
                        "Next": "CreateBucketIfNotExists"
                    }
                ],
                "Next": "EnsureIAMRole"
            },

            "CreateBucketIfNotExists": {
                "Type": "Task",
                "Comment": "Create S3 bucket if it doesn't exist",
                "Resource": "arn:aws:states:::aws-sdk:s3:createBucket",
                "Parameters": {
                    "Bucket.$": "$.bucketName",
                    "CreateBucketConfiguration": {
                        "LocationConstraint.$": "$.region"
                    }
                },
                "ResultPath": "$.bucketCreated",
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "ResultPath": "$.error",
                        "Next": "CleanupOnError"
                    }
                ],
                "Next": "EnsureIAMRole"
            },

            "EnsureIAMRole": {
                "Type": "Pass",
                "Comment": "IAM role is created as permanent infrastructure outside workflow",
                "Result": {
                    "Message": "Using pre-created IAM role"
                },
                "ResultPath": "$.iamCheck",
                "Next": "CreateSecurityGroup"
            },

            "CreateSecurityGroup": {
                "Type": "Task",
                "Comment": "Create security group for EC2 instance",
                "Resource": "arn:aws:states:::aws-sdk:ec2:createSecurityGroup",
                "Parameters": {
                    "GroupName.$": "States.Format('podcast-sg-{}', $.timestamp)",
                    "Description": "Temporary security group for podcast generation"
                },
                "ResultPath": "$.securityGroup",
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "ResultPath": "$.error",
                        "Next": "CleanupOnError"
                    }
                ],
                "Next": "LaunchEC2Instance"
            },

            "LaunchEC2Instance": {
                "Type": "Task",
                "Comment": "Launch EC2 instance for podcast generation",
                "Resource": "arn:aws:states:::aws-sdk:ec2:runInstances",
                "Parameters": {
                    "ImageId.$": "$.amiId",
                    "InstanceType.$": "$.instanceType",
                    "MaxCount": 1,
                    "MinCount": 1,
                    "IamInstanceProfile": {
                        "Name.$": "$.iamInstanceProfile"
                    },
                    "SecurityGroupIds.$": "States.Array($.securityGroup.GroupId)",
                    "BlockDeviceMappings": [
                        {
                            "DeviceName": "/dev/sda1",
                            "Ebs": {
                                "VolumeSize": 150,
                                "VolumeType": "gp3"
                            }
                        }
                    ],
                    "TagSpecifications": [
                        {
                            "ResourceType": "instance",
                            "Tags": [
                                {
                                    "Key": "Name",
                                    "Value.$": "States.Format('podcast-generation-{}', $.timestamp)"
                                },
                                {
                                    "Key": "Purpose",
                                    "Value": "podcast-generation"
                                },
                                {
                                    "Key": "ManagedBy",
                                    "Value": "StepFunctions"
                                }
                            ]
                        }
                    ]
                },
                "ResultPath": "$.instance",
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "ResultPath": "$.error",
                        "Next": "CleanupSecurityGroup"
                    }
                ],
                "Next": "WaitForInstance"
            },

            "WaitForInstance": {
                "Type": "Wait",
                "Comment": "Wait for instance to initialize",
                "Seconds": 30,
                "Next": "CheckSSMStatus"
            },

            "CheckSSMStatus": {
                "Type": "Task",
                "Comment": "Check if SSM agent is online",
                "Resource": "arn:aws:states:::aws-sdk:ssm:describeInstanceInformation",
                "Parameters": {
                    "Filters": [
                        {
                            "Key": "InstanceIds",
                            "Values.$": "States.Array($.instance.Instances[0].InstanceId)"
                        }
                    ]
                },
                "ResultPath": "$.ssmStatus",
                "Next": "IsSSMReady"
            },

            "IsSSMReady": {
                "Type": "Choice",
                "Comment": "Check if SSM is ready",
                "Choices": [
                    {
                        "And": [
                            {
                                "Variable": "$.ssmStatus.InstanceInformationList[0]",
                                "IsPresent": True
                            },
                            {
                                "Variable": "$.ssmStatus.InstanceInformationList[0].PingStatus",
                                "StringEquals": "Online"
                            }
                        ],
                        "Next": "InstallDependencies"
                    }
                ],
                "Default": "WaitForSSM"
            },

            "WaitForSSM": {
                "Type": "Wait",
                "Seconds": 10,
                "Next": "CheckSSMStatus"
            },

            "InstallDependencies": {
                "Type": "Task",
                "Comment": "Install VibeVoice and dependencies",
                "Resource": "arn:aws:states:::aws-sdk:ssm:sendCommand",
                "Parameters": {
                    "DocumentName": "AWS-RunShellScript",
                    "InstanceIds.$": "States.Array($.instance.Instances[0].InstanceId)",
                    "Parameters": {
                        "commands": [
                            "sudo apt-get update",
                            "git clone https://github.com/vibevoice-community/VibeVoice.git",
                            "pip install --prefer-binary torch transformers accelerate",
                            "cd VibeVoice && pip install -e ."
                        ]
                    }
                },
                "ResultPath": "$.installCommand",
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "ResultPath": "$.error",
                        "Next": "CleanupInstance"
                    }
                ],
                "Next": "WaitForInstallation"
            },

            "WaitForInstallation": {
                "Type": "Wait",
                "Comment": "Wait for installation to complete",
                "Seconds": 300,
                "Next": "DownloadFilesFromS3"
            },

            "DownloadFilesFromS3": {
                "Type": "Task",
                "Comment": "Download voices and script from S3 to EC2",
                "Resource": "arn:aws:states:::aws-sdk:ssm:sendCommand",
                "Parameters": {
                    "DocumentName": "AWS-RunShellScript",
                    "InstanceIds.$": "States.Array($.instance.Instances[0].InstanceId)",
                    "Parameters": {
                        "commands.$": "$.downloadCommands"
                    }
                },
                "ResultPath": "$.downloadCommand",
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "ResultPath": "$.error",
                        "Next": "CleanupInstance"
                    }
                ],
                "Next": "WaitForDownload"
            },

            "WaitForDownload": {
                "Type": "Wait",
                "Seconds": 10,
                "Next": "StartAudioGeneration"
            },

            "StartAudioGeneration": {
                "Type": "Task",
                "Comment": "Start audio generation process",
                "Resource": "arn:aws:states:::aws-sdk:ssm:sendCommand",
                "Parameters": {
                    "DocumentName": "AWS-RunShellScript",
                    "InstanceIds.$": "States.Array($.instance.Instances[0].InstanceId)",
                    "Parameters": {
                        "commands.$": "States.Array($.generationCommand)"
                    }
                },
                "ResultPath": "$.generationCommand",
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "ResultPath": "$.error",
                        "Next": "CleanupInstance"
                    }
                ],
                "Next": "InitializeMonitoringCounter"
            },

            "InitializeMonitoringCounter": {
                "Type": "Pass",
                "Comment": "Initialize monitoring counter for timeout (240 iterations = 4 hours)",
                "Result": 0,
                "ResultPath": "$.monitoringIterations",
                "Next": "MonitorGeneration"
            },

            "MonitorGeneration": {
                "Type": "Wait",
                "Comment": "Wait while generation is in progress (60s per iteration, max 240 iterations = 4 hours)",
                "Seconds": 60,
                "Next": "IncrementMonitoringCounter"
            },

            "IncrementMonitoringCounter": {
                "Type": "Pass",
                "Comment": "Increment monitoring counter and preserve all critical fields",
                "Parameters": {
                    "monitoringIterations.$": "States.MathAdd($.monitoringIterations, 1)",
                    "instance.$": "$.instance",
                    "timestamp.$": "$.timestamp",
                    "bucketName.$": "$.bucketName",
                    "uploadCommand.$": "$.uploadCommand",
                    "securityGroup.$": "$.securityGroup",
                    "region.$": "$.region",
                    "amiId.$": "$.amiId",
                    "instanceType.$": "$.instanceType",
                    "iamInstanceProfile.$": "$.iamInstanceProfile"
                },
                "Next": "CheckMonitoringTimeout"
            },

            "CheckMonitoringTimeout": {
                "Type": "Choice",
                "Comment": "Check if monitoring has exceeded 4-hour timeout (240 iterations)",
                "Choices": [
                    {
                        "Variable": "$.monitoringIterations",
                        "NumericGreaterThan": 240,
                        "Next": "RecordGenerationTimeout"
                    }
                ],
                "Default": "CheckGenerationStatus"
            },

            "RecordGenerationTimeout": {
                "Type": "Pass",
                "Comment": "Record that generation timed out, then proceed to cleanup",
                "Result": {
                    "Error": "GenerationTimeout",
                    "Message": "Audio generation did not complete within 4 hours"
                },
                "ResultPath": "$.timeoutError",
                "Next": "CleanupInstance"
            },

            "CheckGenerationStatus": {
                "Type": "Task",
                "Comment": "Send command to check if audio generation is complete",
                "Resource": "arn:aws:states:::aws-sdk:ssm:sendCommand",
                "Parameters": {
                    "DocumentName": "AWS-RunShellScript",
                    "InstanceIds.$": "States.Array($.instance.Instances[0].InstanceId)",
                    "Parameters": {
                        "commands": [
                            "ls -lh VibeVoice/outputs/*.wav 2>/dev/null || echo 'RUNNING'"
                        ]
                    }
                },
                "ResultPath": "$.statusCheck",
                "Next": "WaitForStatusCheck"
            },

            "WaitForStatusCheck": {
                "Type": "Wait",
                "Comment": "Wait for status check command to complete",
                "Seconds": 5,
                "Next": "GetStatusCheckResult"
            },

            "GetStatusCheckResult": {
                "Type": "Task",
                "Comment": "Retrieve the command output to check if file exists",
                "Resource": "arn:aws:states:::aws-sdk:ssm:getCommandInvocation",
                "Parameters": {
                    "CommandId.$": "$.statusCheck.Command.CommandId",
                    "InstanceId.$": "$.instance.Instances[0].InstanceId"
                },
                "ResultPath": "$.commandResult",
                "Retry": [
                    {
                        "ErrorEquals": ["Ssm.InvocationDoesNotExist"],
                        "IntervalSeconds": 2,
                        "MaxAttempts": 3,
                        "BackoffRate": 2.0
                    }
                ],
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "ResultPath": "$.error",
                        "Next": "MonitorGeneration"
                    }
                ],
                "Next": "IsGenerationComplete"
            },

            "IsGenerationComplete": {
                "Type": "Choice",
                "Comment": "Check if generation is complete by examining command output",
                "Choices": [
                    {
                        "And": [
                            {
                                "Variable": "$.commandResult.Status",
                                "StringEquals": "Success"
                            },
                            {
                                "Variable": "$.commandResult.StandardOutputContent",
                                "IsPresent": True
                            },
                            {
                                "Not": {
                                    "Variable": "$.commandResult.StandardOutputContent",
                                    "StringMatches": "*RUNNING*"
                                }
                            }
                        ],
                        "Next": "UploadAudioToS3"
                    }
                ],
                "Default": "MonitorGeneration"
            },

            "UploadAudioToS3": {
                "Type": "Task",
                "Comment": "Upload generated audio from EC2 to S3",
                "Resource": "arn:aws:states:::aws-sdk:ssm:sendCommand",
                "Parameters": {
                    "DocumentName": "AWS-RunShellScript",
                    "InstanceIds.$": "States.Array($.instance.Instances[0].InstanceId)",
                    "Parameters": {
                        "commands.$": "$.uploadCommand"
                    }
                },
                "ResultPath": "$.uploadResult",
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "ResultPath": "$.error",
                        "Next": "CleanupInstance"
                    }
                ],
                "Next": "WaitForUpload"
            },

            "WaitForUpload": {
                "Type": "Wait",
                "Seconds": 30,
                "Next": "CleanupInstance"
            },

            "CleanupInstance": {
                "Type": "Task",
                "Comment": "Terminate EC2 instance",
                "Resource": "arn:aws:states:::aws-sdk:ec2:terminateInstances",
                "Parameters": {
                    "InstanceIds.$": "States.Array($.instance.Instances[0].InstanceId)"
                },
                "ResultPath": "$.instanceTermination",
                "Next": "WaitForTermination",
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "ResultPath": "$.cleanupError",
                        "Next": "CleanupSecurityGroup"
                    }
                ]
            },

            "WaitForTermination": {
                "Type": "Wait",
                "Seconds": 300,
                "Next": "CleanupSecurityGroup"
            },

            "CleanupSecurityGroup": {
                "Type": "Task",
                "Comment": "Delete security group",
                "Resource": "arn:aws:states:::aws-sdk:ec2:deleteSecurityGroup",
                "Parameters": {
                    "GroupId.$": "$.securityGroup.GroupId"
                },
                "ResultPath": "$.sgDeletion",
                "Next": "CleanupS3Files",
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "ResultPath": "$.cleanupError",
                        "Next": "CleanupS3Files"
                    }
                ]
            },

            "CleanupS3Files": {
                "Type": "Pass",
                "Comment": "S3 files automatically deleted after 24 hours via bucket lifecycle policy",
                "Result": {
                    "Message": "S3 cleanup handled by lifecycle policy (24-hour retention)"
                },
                "ResultPath": "$.s3Cleanup",
                "Next": "WorkflowComplete"
            },

            "WorkflowComplete": {
                "Type": "Succeed",
                "Comment": "Workflow completed successfully"
            },

            "CleanupOnError": {
                "Type": "Pass",
                "Comment": "Cleanup path for early failures",
                "Result": {
                    "Message": "Error occurred, cleanup initiated"
                },
                "ResultPath": "$.errorCleanup",
                "Next": "WorkflowFailed"
            },

            "WorkflowFailed": {
                "Type": "Fail",
                "Comment": "Workflow failed",
                "Error": "WorkflowExecutionFailed",
                "Cause": "An error occurred during podcast generation"
            }
        }
    }


def create_or_update_state_machine(*, profile: str, region: str, sf_role_arn: str) -> str:
    """Create or update Step Functions state machine. Returns state machine ARN."""
    state_machine_name = get_state_machine_name(region)
    log_progress(f"Creating/updating state machine: {state_machine_name}")

    definition = get_state_machine_definition()
    definition_str = json.dumps(definition)

    result = subprocess.run([
        "aws", "stepfunctions", "list-state-machines",
        "--profile", profile,
        "--region", region,
        "--output", "json"
    ], capture_output=True, text=True, timeout=30)

    if result.returncode == 0:
        data = json.loads(result.stdout)
        existing = [sm for sm in data.get('stateMachines', [])
                    if sm['name'] == state_machine_name]

        if existing:
            state_machine_arn = existing[0]['stateMachineArn']
            log_progress(f"Updating existing state machine: {state_machine_arn}")

            result = subprocess.run([
                "aws", "stepfunctions", "update-state-machine",
                "--profile", profile,
                "--region", region,
                "--state-machine-arn", state_machine_arn,
                "--definition", definition_str,
                "--role-arn", sf_role_arn
            ], capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                raise Exception(f"Failed to update state machine: {result.stderr}")

            log_progress("State machine updated successfully")
            return state_machine_arn

    log_progress("Creating new state machine")

    result = subprocess.run([
        "aws", "stepfunctions", "create-state-machine",
        "--profile", profile,
        "--region", region,
        "--name", state_machine_name,
        "--definition", definition_str,
        "--role-arn", sf_role_arn
    ], capture_output=True, text=True, timeout=30)

    if result.returncode != 0:
        raise Exception(f"Failed to create state machine: {result.stderr}")

    state_machine_arn = json.loads(result.stdout)['stateMachineArn']
    log_progress(f"State machine created: {state_machine_arn}")
    return state_machine_arn


def main():
    parser = argparse.ArgumentParser(
        description='Set up persistent AWS infrastructure for podcast audio generation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Run this once per AWS account/region before using generate_podcast_audio.py.
Safe to re-run: all operations are idempotent.

Resources created:
  - S3 bucket:             podcast-temp-{account_id}-{region}
  - Lambda IAM role:       podcast-lambda-role-{account_id}-{region}
  - Step Functions role:   podcast-stepfunctions-role-{account_id}-{region}
  - EC2 IAM role:          podcast-ec2-role-{account_id}-{region}
  - EC2 instance profile:  podcast-ec2-role-{account_id}-{region}
  - Step Functions SM:     podcast-generation-{region}

Example:
  %(prog)s --profile my-aws-profile --region us-west-2
        """
    )
    parser.add_argument('--profile', required=True, help='AWS CLI profile')
    parser.add_argument('--region', required=True, help='AWS region')

    args = parser.parse_args()

    separator = "=" * 80
    log_progress(separator)
    log_progress("PODCAST INFRASTRUCTURE SETUP")
    log_progress(separator)

    try:
        account_id = get_aws_account_id(profile=args.profile)
        log_progress(f"Account ID: {account_id}")
        log_progress(f"Region: {args.region}")

        bucket_name = get_bucket_name(account_id, args.region)

        log_progress("")
        log_progress("=== S3 Bucket ===")
        ensure_s3_bucket(profile=args.profile, region=args.region, bucket_name=bucket_name)

        log_progress("")
        log_progress("=== IAM Roles ===")
        lambda_role_arn = create_lambda_execution_role(
            profile=args.profile, region=args.region, account_id=account_id
        )
        sf_role_arn = create_step_functions_role(
            profile=args.profile, region=args.region, account_id=account_id
        )
        _ec2_role_arn, _ec2_instance_profile = create_ec2_role(
            profile=args.profile, region=args.region, account_id=account_id
        )

        log_progress("")
        log_progress("=== Step Functions State Machine ===")
        state_machine_arn = create_or_update_state_machine(
            profile=args.profile,
            region=args.region,
            sf_role_arn=sf_role_arn,
        )

        log_progress("")
        log_progress(separator)
        log_progress("INFRASTRUCTURE SETUP COMPLETE")
        log_progress(separator)
        log_progress(f"S3 Bucket:       {bucket_name}")
        log_progress(f"Lambda Role:     {lambda_role_arn}")
        log_progress(f"SF Role:         {sf_role_arn}")
        log_progress(f"State Machine:   {state_machine_arn}")
        log_progress(separator)
        log_progress("You can now run generate_podcast_audio.py to generate podcasts.")
        log_progress(separator)

    except Exception as e:
        log_progress(f"ERROR: {str(e)}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
