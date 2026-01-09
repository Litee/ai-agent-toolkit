#!/usr/bin/env python3
"""
CloudWatch Log Insights Query Executor

Execute CloudWatch Log Insights queries with progress tracking and flexible output formats.
"""

import argparse
import boto3
import csv
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union


class CloudWatchQueryError(Exception):
    """Base exception for CloudWatch query errors."""
    pass


class LogGroupNotFoundError(CloudWatchQueryError):
    """Raised when log group doesn't exist."""
    pass


class QuerySyntaxError(CloudWatchQueryError):
    """Raised when query syntax is invalid."""
    pass


class CloudWatchLogsQueryExecutor:
    """Execute CloudWatch Log Insights queries with progress tracking."""

    def __init__(self, region: Optional[str] = None, profile: Optional[str] = None):
        """
        Initialize CloudWatch Logs query executor.

        Args:
            region: AWS region (optional, uses default if not specified)
            profile: AWS profile name (optional, uses default credential chain if not specified)
        """
        session_kwargs = {}
        if profile:
            session_kwargs['profile_name'] = profile
        if region:
            session_kwargs['region_name'] = region
        session = boto3.Session(**session_kwargs)

        self.logs_client = session.client('logs')

        self.start_time = None
        self.last_update_time = None

    def parse_time(self, time_str: str) -> int:
        """
        Parse various time formats to Unix timestamp in milliseconds.

        Supports:
        - ISO 8601: "2025-12-05T10:00:00Z"
        - Unix timestamp (ms): "1733395200000"
        - Relative: "1h", "2d", "30m", "now"
        - Named: "last-hour", "last-24h", "last-week", "yesterday", "today"

        Args:
            time_str: Time string in various formats

        Returns:
            Unix timestamp in milliseconds
        """
        time_str = time_str.strip()

        # Handle "now"
        if time_str.lower() == 'now':
            return int(datetime.now().timestamp() * 1000)

        # Handle named ranges
        named_ranges = {
            'last-hour': timedelta(hours=1),
            'last-24h': timedelta(hours=24),
            'last-day': timedelta(days=1),
            'last-week': timedelta(weeks=1),
            'yesterday': timedelta(days=1),
            'today': timedelta(hours=0),
        }

        if time_str.lower() in named_ranges:
            if time_str.lower() == 'today':
                # Start of today
                now = datetime.now()
                start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
                return int(start_of_day.timestamp() * 1000)
            elif time_str.lower() == 'yesterday':
                # Start of yesterday
                now = datetime.now()
                start_of_yesterday = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                return int(start_of_yesterday.timestamp() * 1000)
            else:
                delta = named_ranges[time_str.lower()]
                return int((datetime.now() - delta).timestamp() * 1000)

        # Handle relative times like "1h", "2d", "30m"
        if time_str[-1] in ['h', 'd', 'm', 's']:
            try:
                unit = time_str[-1]
                value = int(time_str[:-1])

                if unit == 's':
                    delta = timedelta(seconds=value)
                elif unit == 'm':
                    delta = timedelta(minutes=value)
                elif unit == 'h':
                    delta = timedelta(hours=value)
                elif unit == 'd':
                    delta = timedelta(days=value)

                return int((datetime.now() - delta).timestamp() * 1000)
            except ValueError:
                pass

        # Handle Unix timestamp in milliseconds (13 digits)
        if time_str.isdigit() and len(time_str) == 13:
            return int(time_str)

        # Handle ISO 8601 formats
        try:
            # Try with timezone
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            return int(dt.timestamp() * 1000)
        except ValueError:
            pass

        # Try without timezone (assume UTC)
        try:
            dt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S")
            return int(dt.timestamp() * 1000)
        except ValueError:
            pass

        # Try date only
        try:
            dt = datetime.strptime(time_str, "%Y-%m-%d")
            return int(dt.timestamp() * 1000)
        except ValueError:
            pass

        raise ValueError(f"Unable to parse time format: {time_str}\n"
                        "Supported formats: ISO 8601, Unix ms, relative (1h, 2d), named (last-hour, now)")

    def validate_log_groups(self, log_groups: List[str]) -> List[str]:
        """
        Validate log groups exist and expand wildcards.

        Args:
            log_groups: List of log group names/patterns

        Returns:
            List of validated log group names

        Raises:
            LogGroupNotFoundError: If log group doesn't exist
        """
        validated_groups = []

        for log_group_pattern in log_groups:
            if '*' in log_group_pattern:
                # Handle wildcard patterns
                prefix = log_group_pattern.replace('*', '')
                try:
                    paginator = self.logs_client.get_paginator('describe_log_groups')
                    page_iterator = paginator.paginate(logGroupNamePrefix=prefix)

                    for page in page_iterator:
                        for log_group in page['logGroups']:
                            validated_groups.append(log_group['logGroupName'])

                    if not validated_groups:
                        raise LogGroupNotFoundError(
                            f"No log groups found matching pattern: {log_group_pattern}"
                        )
                except Exception as e:
                    if 'ResourceNotFoundException' in str(e):
                        raise LogGroupNotFoundError(
                            f"Log group not found: {log_group_pattern}"
                        )
                    raise
            else:
                # Validate single log group
                try:
                    self.logs_client.describe_log_groups(
                        logGroupNamePrefix=log_group_pattern,
                        limit=1
                    )
                    validated_groups.append(log_group_pattern)
                except Exception as e:
                    if 'ResourceNotFoundException' in str(e):
                        raise LogGroupNotFoundError(
                            f"Log group not found: {log_group_pattern}\n"
                            "Please verify the log group exists and you have permissions to access it."
                        )
                    raise

        # CloudWatch has a limit of 20 log groups per query
        if len(validated_groups) > 20:
            print(f"WARNING: CloudWatch limits queries to 20 log groups. "
                  f"Using first 20 of {len(validated_groups)} groups.", file=sys.stderr)
            validated_groups = validated_groups[:20]

        return validated_groups

    def execute_query(
        self,
        query: str,
        log_groups: List[str],
        start_time: str,
        end_time: str,
        limit: int = 10000
    ) -> str:
        """
        Execute CloudWatch Log Insights query.

        Args:
            query: Log Insights query string
            log_groups: List of log group names
            start_time: Start time (various formats supported)
            end_time: End time (various formats supported)
            limit: Maximum results to return

        Returns:
            query_id: The query execution ID

        Raises:
            QuerySyntaxError: If query syntax is invalid
        """
        # Convert times
        try:
            start_epoch = self.parse_time(start_time)
            end_epoch = self.parse_time(end_time)
        except ValueError as e:
            raise QuerySyntaxError(str(e))

        # Validate time range
        if start_epoch >= end_epoch:
            raise QuerySyntaxError(
                f"Start time must be before end time\n"
                f"Start: {start_time} ({start_epoch})\n"
                f"End: {end_time} ({end_epoch})"
            )

        # Validate log groups
        try:
            validated_groups = self.validate_log_groups(log_groups)
        except LogGroupNotFoundError as e:
            print(f"✗ Error: {e}", file=sys.stderr)
            sys.exit(1)

        print(f"Executing query across {len(validated_groups)} log group(s)...")
        print(f"Time range: {start_time} to {end_time}")
        if len(validated_groups) <= 5:
            for group in validated_groups:
                print(f"  - {group}")

        try:
            response = self.logs_client.start_query(
                logGroupNames=validated_groups,
                startTime=start_epoch,
                endTime=end_epoch,
                queryString=query,
                limit=limit
            )

            query_id = response['queryId']
            print(f"Query ID: {query_id}")

            return query_id
        except Exception as e:
            error_code = e.response.get('Error', {}).get('Code', '') if hasattr(e, 'response') else ''

            if 'MalformedQueryException' in str(e) or 'InvalidParameterException' in error_code:
                raise QuerySyntaxError(f"Invalid query syntax: {e}")
            elif 'LimitExceededException' in error_code:
                print("✗ API rate limit exceeded. Please wait and try again.", file=sys.stderr)
                sys.exit(1)
            else:
                raise CloudWatchQueryError(f"Query execution failed: {e}")

    def wait_for_results(
        self,
        query_id: str,
        update_interval: int = 30
    ) -> Dict:
        """
        Wait for query completion with periodic status updates.

        Args:
            query_id: The query execution ID
            update_interval: Seconds between status updates (default: 30)

        Returns:
            Query response with results
        """
        self.start_time = time.time()
        self.last_update_time = self.start_time

        print("Waiting for query to complete...")

        while True:
            current_time = time.time()
            elapsed = current_time - self.start_time

            # Get query status
            try:
                response = self.logs_client.get_query_results(queryId=query_id)
            except Exception as e:
                print(f"✗ Error fetching query results: {e}", file=sys.stderr)
                sys.exit(1)

            status = response['status']

            # Print update every N seconds or on status change
            should_update = (current_time - self.last_update_time >= update_interval)
            is_terminal_state = status in ['Complete', 'Failed', 'Cancelled', 'Timeout']

            if should_update or is_terminal_state:
                self._print_status_update(response, elapsed)
                self.last_update_time = current_time

            # Check completion
            if is_terminal_state:
                if status == 'Complete':
                    return response
                elif status == 'Failed':
                    print(f"✗ Query failed", file=sys.stderr)
                    sys.exit(1)
                elif status == 'Cancelled':
                    print(f"✗ Query was cancelled", file=sys.stderr)
                    sys.exit(1)
                elif status == 'Timeout':
                    print(f"✗ Query timed out", file=sys.stderr)
                    sys.exit(1)

            # Poll every 2 seconds
            time.sleep(2)

    def _print_status_update(self, response: Dict, elapsed: float):
        """
        Print formatted status update.

        Args:
            response: Query results response from CloudWatch
            elapsed: Elapsed time in seconds
        """
        status = response['status']
        stats = response.get('statistics', {})

        # Format elapsed time
        if elapsed >= 60:
            minutes = int(elapsed / 60)
            seconds = int(elapsed % 60)
            elapsed_str = f"{minutes}m {seconds}s"
        else:
            elapsed_str = f"{int(elapsed)}s"

        print(f"[{elapsed_str}] Status: {status}")

        if stats:
            records_scanned = stats.get('recordsScanned', 0)
            records_matched = stats.get('recordsMatched', 0)
            bytes_scanned = stats.get('bytesScanned', 0)

            # Format bytes
            if bytes_scanned > 0:
                mb_scanned = bytes_scanned / (1024 * 1024)
                print(f"  → Scanned: {records_scanned:,} records ({mb_scanned:.2f} MB)")
            else:
                print(f"  → Scanned: {records_scanned:,} records")

            print(f"  → Matched: {records_matched:,} records")

        # Print completion message
        if status == 'Complete':
            print(f"✓ Query completed successfully in {elapsed_str}")

    def format_results(
        self,
        results: List[List[Dict]],
        format: str,
        output_file: Optional[str] = None,
        exclude_metadata: bool = False
    ) -> Optional[str]:
        """
        Format and save query results.

        Args:
            results: Query results from CloudWatch
            format: Output format (table, csv, json)
            output_file: File to save results (optional)
            exclude_metadata: Exclude CloudWatch metadata fields

        Returns:
            Output file path if saved, None otherwise
        """
        if not results:
            print("No results returned from query")
            return None

        # Extract field names from first result
        if not results[0]:
            print("No results returned from query")
            return None

        # Get all unique field names
        all_fields = set()
        for result in results:
            for field in result:
                all_fields.add(field['field'])

        # Sort fields: metadata fields first, then others alphabetically
        metadata_fields = ['@timestamp', '@message', '@logStream', '@log']
        sorted_fields = [f for f in metadata_fields if f in all_fields]
        other_fields = sorted([f for f in all_fields if f not in metadata_fields])
        sorted_fields.extend(other_fields)

        if exclude_metadata:
            sorted_fields = [f for f in sorted_fields if not f.startswith('@')]

        # Convert results to list of dicts
        rows = []
        for result in results:
            row = {field['field']: field.get('value', '') for field in result}
            rows.append(row)

        # Format output based on requested format
        if format == 'json':
            return self._format_json(rows, output_file)
        elif format == 'csv':
            return self._format_csv(rows, sorted_fields, output_file)
        elif format == 'table':
            return self._format_table(rows, sorted_fields, output_file)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _format_json(self, rows: List[Dict], output_file: Optional[str]) -> Optional[str]:
        """Format results as JSON."""
        json_output = json.dumps(rows, indent=2)

        if output_file:
            with open(output_file, 'w') as f:
                f.write(json_output)
            print(f"✓ Results saved to: {output_file}")
            return output_file
        else:
            print(json_output)
            return None

    def _format_csv(
        self,
        rows: List[Dict],
        fields: List[str],
        output_file: Optional[str]
    ) -> Optional[str]:
        """Format results as CSV."""
        if output_file:
            with open(output_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
            print(f"✓ Results saved to: {output_file}")
            return output_file
        else:
            import io
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
            print(output.getvalue())
            return None

    def _format_table(
        self,
        rows: List[Dict],
        fields: List[str],
        output_file: Optional[str]
    ) -> Optional[str]:
        """Format results as a table."""
        if not rows:
            return None

        # Calculate column widths
        widths = {field: len(field) for field in fields}
        for row in rows:
            for field in fields:
                value = str(row.get(field, ''))
                widths[field] = max(widths[field], len(value))

        # Limit column width to 50 chars for readability
        for field in widths:
            widths[field] = min(widths[field], 50)

        # Create table
        lines = []

        # Header
        header = ' | '.join(field.ljust(widths[field]) for field in fields)
        separator = '-+-'.join('-' * widths[field] for field in fields)
        lines.append(header)
        lines.append(separator)

        # Rows
        for row in rows:
            values = []
            for field in fields:
                value = str(row.get(field, ''))
                if len(value) > 50:
                    value = value[:47] + '...'
                values.append(value.ljust(widths[field]))
            lines.append(' | '.join(values))

        table_output = '\n'.join(lines)

        if output_file:
            with open(output_file, 'w') as f:
                f.write(table_output)
            print(f"✓ Results saved to: {output_file}")
            return output_file
        else:
            print(table_output)
            return None

    def execute_and_save(
        self,
        query: str,
        log_groups: List[str],
        start_time: str,
        end_time: str,
        output_file: Optional[str] = None,
        format: str = 'table',
        limit: int = 10000,
        update_interval: int = 30,
        exclude_metadata: bool = False
    ):
        """
        Execute query and save results in one operation.

        Args:
            query: Log Insights query string
            log_groups: List of log group names
            start_time: Start time (various formats)
            end_time: End time (various formats)
            output_file: Output file path (optional)
            format: Output format (table, csv, json)
            limit: Maximum results to return
            update_interval: Status update interval in seconds
            exclude_metadata: Exclude CloudWatch metadata fields
        """
        try:
            query_id = self.execute_query(query, log_groups, start_time, end_time, limit)
            response = self.wait_for_results(query_id, update_interval)

            results = response.get('results', [])

            # Generate output filename if not specified
            if output_file is None and format != 'table':
                ext = format
                output_file = f"cloudwatch_logs_results_{query_id[:8]}.{ext}"

            self.format_results(results, format, output_file, exclude_metadata)

        except (CloudWatchQueryError, QuerySyntaxError, LogGroupNotFoundError) as e:
            print(f"✗ Error: {e}", file=sys.stderr)
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n✗ Query interrupted by user", file=sys.stderr)
            sys.exit(130)
        except Exception as e:
            print(f"✗ Unexpected error: {e}", file=sys.stderr)
            sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Execute CloudWatch Log Insights queries with progress tracking',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Time format examples:
  ISO 8601:     2025-12-05T10:00:00Z
  Unix (ms):    1733395200000
  Relative:     1h, 2d, 30m, now
  Named:        last-hour, last-24h, last-week, yesterday, today

Log group examples:
  Single:       /aws/lambda/my-function
  Multiple:     /aws/lambda/func1,/aws/lambda/func2
  Wildcard:     /aws/lambda/*

Query examples:
  fields @timestamp, @message | filter @message like /ERROR/
  stats count() by bin(5m)
  parse @message '[*] *' as level, msg | filter level = 'ERROR'
        """
    )

    # Query input
    query_group = parser.add_mutually_exclusive_group(required=True)
    query_group.add_argument(
        '--query',
        help='Log Insights query string'
    )
    query_group.add_argument(
        '--query-file',
        help='File containing query'
    )

    # Log groups
    parser.add_argument(
        '--log-groups',
        required=True,
        help='Comma-separated log groups or patterns (max 20)'
    )

    # Time range
    parser.add_argument(
        '--start-time',
        required=True,
        help='Start time (ISO8601, Unix ms, relative, or named)'
    )

    parser.add_argument(
        '--end-time',
        default='now',
        help='End time (default: now)'
    )

    # Output options
    parser.add_argument(
        '--output-file',
        help='Save results to file (auto-generated if not specified for csv/json)'
    )

    parser.add_argument(
        '--format',
        default='table',
        choices=['table', 'csv', 'json'],
        help='Output format (default: table)'
    )

    # Query options
    parser.add_argument(
        '--limit',
        type=int,
        default=10000,
        help='Maximum results to return (default: 10000)'
    )

    parser.add_argument(
        '--exclude-metadata',
        action='store_true',
        help='Exclude CloudWatch metadata fields (@timestamp, @message, etc.)'
    )

    # AWS options
    parser.add_argument(
        '--region',
        help='AWS region (uses default if not specified)'
    )

    parser.add_argument(
        '--profile',
        required=True,
        help='AWS profile name (required)'
    )

    # Progress options
    parser.add_argument(
        '--update-interval',
        type=int,
        default=30,
        help='Seconds between status updates (default: 30)'
    )

    args = parser.parse_args()

    # Read query from file if specified
    if args.query_file:
        query_file = Path(args.query_file)
        if not query_file.exists():
            print(f"✗ Error: Query file not found: {args.query_file}", file=sys.stderr)
            sys.exit(1)
        query = query_file.read_text().strip()
    else:
        query = args.query

    # Parse log groups
    log_groups = [lg.strip() for lg in args.log_groups.split(',')]

    # Execute query
    executor = CloudWatchLogsQueryExecutor(region=args.region, profile=args.profile)
    executor.execute_and_save(
        query=query,
        log_groups=log_groups,
        start_time=args.start_time,
        end_time=args.end_time,
        output_file=args.output_file,
        format=args.format,
        limit=args.limit,
        update_interval=args.update_interval,
        exclude_metadata=args.exclude_metadata
    )


if __name__ == '__main__':
    main()
