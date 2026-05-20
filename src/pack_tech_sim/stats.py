# Statistics module: holds metrics from a single replication and provides
# confidence-interval calculation.

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass
class ReplicationMetrics:
    """Raw counts accumulated during one replication; finalise() computes
    time-based utilisation and average queue lengths."""

    throughput: int = 0
    total_lead_time: float = 0.0
    lead_time_count: int = 0

    oven_busy_time: float = 0.0
    oven_idle_time: float = 0.0
    oven_blocked_time: float = 0.0

    inspection_busy_time: float = 0.0

    queue_pintura_time_sum: float = 0.0
    queue_horno_time_sum: float = 0.0

    # Final computed metrics
    oven_util_busy: float = 0.0
    oven_util_idle: float = 0.0
    oven_util_blocked: float = 0.0
    inspection_util: float = 0.0
    avg_queue_pintura: float = 0.0
    avg_queue_horno: float = 0.0
    avg_lead_time: float = 0.0

    def finalise(self, total_time: float) -> None:
        """Convert accumulated times into fractions of the total simulation time."""
        self.oven_util_busy = self.oven_busy_time / total_time
        self.oven_util_idle = self.oven_idle_time / total_time
        self.oven_util_blocked = self.oven_blocked_time / total_time
        # Inspection has two servers, hence division by (2 * total_time)
        self.inspection_util = self.inspection_busy_time / (2 * total_time)
        self.avg_queue_pintura = self.queue_pintura_time_sum / total_time
        self.avg_queue_horno = self.queue_horno_time_sum / total_time
        self.avg_lead_time = (
            self.total_lead_time / self.lead_time_count if self.lead_time_count else 0.0
        )


def confidence_interval(
    data: Sequence[float],
    t_value: float = 2.045,
) -> tuple[float, float]:
    """Compute a t-based confidence interval (mean ± margin)."""
    n = len(data)
    if n < 2:
        return (data[0], data[0]) if n == 1 else (0.0, 0.0)

    mean = sum(data) / n
    variance = sum((x - mean) ** 2 for x in data) / (n - 1)
    std_err = math.sqrt(variance / n)
    margin = t_value * std_err
    return mean - margin, mean + margin
