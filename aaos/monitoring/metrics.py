"""Lightweight in-process metrics (Phase 4 will export Prometheus)."""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Metrics:
    counters: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    timings_ms: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def inc(self, name: str, value: int = 1) -> None:
        with self._lock:
            self.counters[name] += value

    def timing(self, name: str, ms: float) -> None:
        with self._lock:
            bucket = self.timings_ms[name]
            bucket.append(ms)
            if len(bucket) > 500:
                del bucket[:250]

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            avg = {
                k: (sum(v) / len(v) if v else 0.0) for k, v in self.timings_ms.items()
            }
            return {
                "counters": dict(self.counters),
                "timing_avg_ms": avg,
            }


_metrics = Metrics()


def get_metrics() -> Metrics:
    return _metrics


class Timer:
    def __init__(self, name: str):
        self.name = name
        self._t0 = 0.0

    def __enter__(self):
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, *args):
        ms = (time.perf_counter() - self._t0) * 1000
        get_metrics().timing(self.name, ms)
