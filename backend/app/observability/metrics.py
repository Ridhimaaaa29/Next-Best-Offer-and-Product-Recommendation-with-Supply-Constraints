"""
Observability Metrics Collection (Lightweight In-Memory Counter).
Tracks request latencies, cache hits, recommendation requests, and policy rejections.
"""

from typing import Dict, Any
from collections import Counter
import threading

_lock = threading.Lock()
_counters: Counter = Counter()


def increment_metric(metric_name: str, count: int = 1) -> None:
    with _lock:
        _counters[metric_name] += count


def get_metrics_snapshot() -> Dict[str, Any]:
    with _lock:
        return dict(_counters)
