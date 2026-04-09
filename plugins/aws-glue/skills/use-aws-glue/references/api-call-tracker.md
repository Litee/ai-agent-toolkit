### 1. Track per-API-operation metrics in jobs that call external services

When a Glue job calls external APIs (SageMaker endpoints, DynamoDB, REST services), simple record counters (see best practice #6, #8) are not enough. You need per-operation latency percentiles, success/failure/retry rates, and TPS — otherwise you are flying blind when a downstream service starts throttling you or degrading silently.

```python
import time, threading, logging, statistics
from collections import defaultdict
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class ApiCallTracker:
    """Thread-safe per-operation metrics collector.

    Create one instance per partition (inside mapPartitions).
    NOT serialisable — do not pass across Spark stage boundaries.
    """

    def __init__(self, log_interval: int = 300):
        self._lock = threading.Lock()
        self._calls     = defaultdict(int)    # op -> total call count
        self._successes = defaultdict(int)
        self._failures  = defaultdict(int)
        self._retries   = defaultdict(int)
        self._latencies = defaultdict(list)   # op -> [float seconds]
        self._start     = time.time()
        self._stop_evt  = threading.Event()
        self._daemon    = threading.Thread(
            target=self._periodic_log, args=(log_interval,), daemon=True
        )
        self._daemon.start()

    @contextmanager
    def track(self, operation: str):
        """Context manager that records latency, success, and failure."""
        t0 = time.monotonic()
        try:
            yield
            self._record(operation, time.monotonic() - t0, success=True)
        except Exception:
            self._record(operation, time.monotonic() - t0, success=False)
            raise

    def record_retry(self, operation: str):
        """Call once per retry attempt inside your retry loop."""
        with self._lock:
            self._retries[operation] += 1

    def _record(self, op: str, elapsed: float, success: bool):
        with self._lock:
            self._calls[op] += 1
            self._latencies[op].append(elapsed)
            if success:
                self._successes[op] += 1
            else:
                self._failures[op] += 1

    def _periodic_log(self, interval: int):
        while not self._stop_evt.wait(interval):
            self._emit("periodic")

    def _emit(self, tag: str):
        with self._lock:
            wall = time.time() - self._start
            for op in sorted(self._calls):
                lats = self._latencies[op]
                n    = self._calls[op]
                tps  = n / wall if wall else 0
                p50  = statistics.median(lats) if lats else 0
                p99  = sorted(lats)[int(len(lats) * 0.99)] if lats else 0
                logger.info(
                    f"[api-metrics:{tag}] op={op} calls={n} tps={tps:.1f} "
                    f"ok={self._successes[op]} fail={self._failures[op]} "
                    f"retry={self._retries[op]} "
                    f"p50={p50 * 1000:.0f}ms p99={p99 * 1000:.0f}ms"
                )

    def report(self):
        """Stop the daemon thread and emit the final summary. Call once at partition end."""
        self._stop_evt.set()
        self._emit("final")
```

Integrate with `mapPartitions` and aggregate on the driver via accumulators:

```python
from pyspark.context import SparkContext

sc = SparkContext.getOrCreate()
total_api_calls    = sc.accumulator(0)
total_api_failures = sc.accumulator(0)

def process_partition(rows):
    tracker = ApiCallTracker(log_interval=300)  # logs every 5 minutes
    for row in rows:
        with tracker.track("sagemaker-invoke"):
            result = call_sagemaker(row)         # your API call here
        # Inside your retry loop (if any):
        # tracker.record_retry("sagemaker-invoke")
        total_api_calls.add(1)
        yield result
    tracker.report()  # emits [api-metrics:final] with full per-op breakdown

output_df = input_df.rdd.mapPartitions(process_partition).toDF()
```

Each executor emits `[api-metrics:periodic]` log lines every 5 minutes and a `[api-metrics:final]` line when its partition finishes. The final line includes: call count, TPS, ok/fail/retry counts, and p50/p99 latency — one line per distinct `operation` name. Combine with the driver-side accumulators from best practice #8 for the global job summary.

**When to skip:** Pure DataFrame transformations with no external API calls. If your job only reads from S3, transforms, and writes back, best practices #6 and #8 are sufficient.
