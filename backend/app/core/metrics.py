"""In-process performance metrics collection.

Collects request latency, error rates, and throughput using a fixed-size
ring buffer. Exposes percentile calculations (p50, p95, p99) and counters.

No external dependency required — metrics are stored in-memory and exposed
via the /api/v1/metrics endpoint. For production, ship these to your
preferred time-series database (Prometheus, Datadog, CloudWatch).
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Maximum number of latency samples retained per endpoint (rolling window)
_MAX_SAMPLES = 10_000
# Maximum age of samples in seconds (1 hour)
_MAX_AGE_SECONDS = 3600


@dataclass
class _TimedSample:
    timestamp: float
    value: float


@dataclass
class _EndpointMetrics:
    """Metrics for a single endpoint."""

    latencies: deque[_TimedSample] = field(default_factory=lambda: deque(maxlen=_MAX_SAMPLES))
    request_count: int = 0
    error_count: int = 0  # 5xx responses
    status_counts: dict[int, int] = field(default_factory=lambda: defaultdict(int))


class MetricsCollector:
    """Thread-safe in-memory metrics collector.

    Uses threading.Lock for synchronization. In an asyncio context the lock
    acquisition is blocking, but the critical sections are very short (a deque
    append and counter increment) so contention is negligible in practice.
    Migrating to asyncio.Lock would require making record_request and
    get_summary async, which would cascade through all call sites.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._endpoints: dict[str, _EndpointMetrics] = defaultdict(_EndpointMetrics)
        self._global = _EndpointMetrics()
        self._start_time = time.time()

    def record_request(
        self, *, method: str, path: str, status_code: int, duration_ms: float
    ) -> None:
        """Record a completed request."""
        now = time.time()
        sample = _TimedSample(timestamp=now, value=duration_ms)
        key = f"{method} {_normalize_path(path)}"

        with self._lock:
            # Per-endpoint
            ep = self._endpoints[key]
            ep.latencies.append(sample)
            ep.request_count += 1
            ep.status_counts[status_code] += 1
            if status_code >= 500:
                ep.error_count += 1

            # Global
            self._global.latencies.append(sample)
            self._global.request_count += 1
            self._global.status_counts[status_code] += 1
            if status_code >= 500:
                self._global.error_count += 1

    def get_summary(self) -> dict[str, Any]:
        """Return a summary of all metrics."""
        now = time.time()
        with self._lock:
            return {
                "uptime_seconds": round(now - self._start_time, 0),
                "global": self._summarize(self._global, now),
                "endpoints": {
                    key: self._summarize(ep, now)
                    for key, ep in sorted(self._endpoints.items())
                    if ep.request_count > 0
                },
            }

    def get_global_summary(self) -> dict[str, Any]:
        """Return only the global summary (for alerting)."""
        now = time.time()
        with self._lock:
            return self._summarize(self._global, now)

    def _summarize(self, ep: _EndpointMetrics, now: float) -> dict[str, Any]:
        """Compute percentiles and error rate for an endpoint."""
        # Filter to recent samples only
        recent = [s.value for s in ep.latencies if (now - s.timestamp) < _MAX_AGE_SECONDS]
        recent.sort()

        total = ep.request_count
        error_rate = ep.error_count / total if total > 0 else 0.0

        result: dict[str, Any] = {
            "request_count": total,
            "error_count": ep.error_count,
            "error_rate": round(error_rate, 4),
            "status_codes": dict(ep.status_counts),
        }

        if recent:
            result["latency_ms"] = {
                "p50": round(_percentile(recent, 50), 2),
                "p90": round(_percentile(recent, 90), 2),
                "p95": round(_percentile(recent, 95), 2),
                "p99": round(_percentile(recent, 99), 2),
                "max": round(recent[-1], 2),
                "min": round(recent[0], 2),
                "avg": round(sum(recent) / len(recent), 2),
                "sample_count": len(recent),
            }
        else:
            result["latency_ms"] = None

        return result


def _percentile(sorted_values: list[float], pct: float) -> float:
    """Calculate percentile from a sorted list."""
    if not sorted_values:
        return 0.0
    k = (len(sorted_values) - 1) * (pct / 100.0)
    f = int(k)
    c = f + 1
    if c >= len(sorted_values):
        return sorted_values[f]
    d = k - f
    return sorted_values[f] + d * (sorted_values[c] - sorted_values[f])


def _normalize_path(path: str) -> str:
    """Replace UUIDs in paths with :id for aggregation.

    /api/v1/firms/abc-123/matters/def-456/tasks → /api/v1/firms/:id/matters/:id/tasks
    """
    import re

    return re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", ":id", path)


# Module-level singleton
metrics_collector = MetricsCollector()
