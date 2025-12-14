#!/usr/bin/env python3
"""
AWS Athena Query Script

Execute Athena queries and download results from S3.
This script follows AWS Athena best practices by downloading results
from S3 instead of using the Athena query results API (avoids pagination).

Usage:
    python3 query_athena.py --query "SELECT * FROM table LIMIT 10" \\
                           --database my_database \\
                           --output-location s3://my-bucket/athena-results/

    python3 query_athena.py --query-file query.sql \\
                           --database my_database \\
                           --output-location s3://my-bucket/athena-results/ \\
                           --format csv
"""

import argparse
import boto3
import time
import sys
from pathlib import Path


class AthenaQueryExecutor:
    """Execute Athena queries and download results from S3."""

    def __init__(self, database, output_location, region=None, profile=None):
        """
        Initialize Athena query executor.

        Args:
            database: Athena database name
            output_location: S3 location for query results (e.g., s3://bucket/path/)
            region: AWS region (optional, uses default if not specified)
            profile: AWS profile name (optional, uses default credential chain if not specified)
        """
        self.database = database
        self.output_location = output_location

        # Create session with optional profile
        session_kwargs = {}
        if profile:
            session_kwargs['profile_name'] = profile
        if region:
            session_kwargs['region_name'] = region
        session = boto3.Session(**session_kwargs)

        self.athena_client = session.client('athena')
        self.s3_client = session.client('s3')

    def execute_query(self, query, wait=True):
        """
        Execute an Athena query.

        Args:
            query: SQL query string
            wait: Whether to wait for query completion (default: True)

        Returns:
            query_execution_id: The ID of the query execution
        """
        print(f"Executing query in database '{self.database}'...")

        response = self.athena_client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={'Database': self.database},
            ResultConfiguration={'OutputLocation': self.output_location}
        )

        query_execution_id = response['QueryExecutionId']
        print(f"Query execution ID: {query_execution_id}")

        if wait:
            self._wait_for_query_completion(query_execution_id)

        return query_execution_id

    def _wait_for_query_completion(self, query_execution_id):
        """
        Wait for query to complete.

        Args:
            query_execution_id: The ID of the query execution
        """
        print("Waiting for query to complete...")

        while True:
            response = self.athena_client.get_query_execution(
                QueryExecutionId=query_execution_id
            )

            status = response['QueryExecution']['Status']['State']

            if status in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
                break

            time.sleep(1)

        if status == 'SUCCEEDED':
            print("✓ Query completed successfully")
        elif status == 'FAILED':
            reason = response['QueryExecution']['Status'].get('StateChangeReason', 'Unknown error')
            print(f"✗ Query failed: {reason}", file=sys.stderr)
            sys.exit(1)
        elif status == 'CANCELLED':
            print("✗ Query was cancelled", file=sys.stderr)
            sys.exit(1)

    def download_results_from_s3(self, query_execution_id, output_file=None, format='csv'):
        """
        Download query results from S3.

        This method follows AWS Athena best practices by downloading results
        directly from S3 instead of using the Athena query results API,
        which avoids pagination issues.

        Args:
            query_execution_id: The ID of the query execution
            output_file: Local file path to save results (optional)
            format: Output format (csv, json, parquet) - default: csv

        Returns:
            local_file_path: Path to the downloaded results file
        """
        print("Downloading results from S3...")

        # Get query execution details to find S3 location
        response = self.athena_client.get_query_execution(
            QueryExecutionId=query_execution_id
        )

        s3_output_location = response['QueryExecution']['ResultConfiguration']['OutputLocation']

        # Parse S3 location
        # Format: s3://bucket-name/path/to/results.csv
        s3_parts = s3_output_location.replace('s3://', '').split('/', 1)
        bucket = s3_parts[0]
        key = s3_parts[1]

        # Determine output file name
        if output_file is None:
            output_file = f"athena_results_{query_execution_id}.{format}"

        # Download from S3
        print(f"Downloading from s3://{bucket}/{key}")
        self.s3_client.download_file(bucket, key, output_file)

        print(f"✓ Results downloaded to: {output_file}")
        return output_file

    def execute_and_download(self, query, output_file=None, format='csv'):
        """
        Execute query and download results in one operation.

        Args:
            query: SQL query string
            output_file: Local file path to save results (optional)
            format: Output format (csv, json, parquet) - default: csv

        Returns:
            local_file_path: Path to the downloaded results file
        """
        query_execution_id = self.execute_query(query, wait=True)
        return self.download_results_from_s3(query_execution_id, output_file, format)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Execute AWS Athena queries and download results from S3',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    query_group = parser.add_mutually_exclusive_group(required=True)
    query_group.add_argument(
        '--query',
        help='SQL query to execute'
    )
    query_group.add_argument(
        '--query-file',
        help='Path to file containing SQL query'
    )

    parser.add_argument(
        '--database',
        required=True,
        help='Athena database name'
    )

    parser.add_argument(
        '--output-location',
        required=True,
        help='S3 location for query results (e.g., s3://my-bucket/athena-results/)'
    )

    parser.add_argument(
        '--output-file',
        help='Local file path to save results (optional, auto-generated if not specified)'
    )

    parser.add_argument(
        '--format',
        default='csv',
        choices=['csv', 'json', 'parquet'],
        help='Output format (default: csv)'
    )

    parser.add_argument(
        '--region',
        help='AWS region (optional, uses default if not specified)'
    )

    parser.add_argument(
        '--profile',
        required=True,
        help='AWS profile name (required)'
    )

    parser.add_argument(
        '--no-download',
        action='store_true',
        help='Only execute query, do not download results'
    )

    args = parser.parse_args()

    # Read query from file if specified
    if args.query_file:
        query = Path(args.query_file).read_text()
    else:
        query = args.query

    # Initialize executor
    executor = AthenaQueryExecutor(
        database=args.database,
        output_location=args.output_location,
        region=args.region,
        profile=args.profile
    )

    # Execute query
    if args.no_download:
        query_execution_id = executor.execute_query(query, wait=True)
        print(f"\nQuery execution ID: {query_execution_id}")
        print(f"Results available at: {args.output_location}")
    else:
        result_file = executor.execute_and_download(
            query=query,
            output_file=args.output_file,
            format=args.format
        )
        print(f"\n✓ Complete! Results saved to: {result_file}")


if __name__ == '__main__':
    main()
