# Entry point for the simulation. Runs three scenarios, collects replication
# metrics, computes confidence intervals, and prints the results in a table.

from __future__ import annotations

import sys
from collections.abc import Callable, Sequence

import pack_tech_sim.config as cfg
from pack_tech_sim.simulation.scenarios import run_replication
from pack_tech_sim.stats import ReplicationMetrics, confidence_interval

try:
    from prettytable import PrettyTable

    TABLE_AVAILABLE = True
except ImportError:
    TABLE_AVAILABLE = False


def run_scenario(
    name: str,
    arrival_dist: Callable[[], float],
    inspection_buffer: int,
) -> dict[str, tuple[float, float] | str]:
    """Execute multiple replications of a scenario and return CI bounds."""
    print(f"\nRunning scenario: {name} ...")
    metrics_list: list[ReplicationMetrics] = []

    for i in range(cfg.REPLICATIONS):
        metrics = run_replication(arrival_dist, inspection_buffer)
        metrics_list.append(metrics)
        if (i + 1) % 10 == 0:
            print(f"  ... {i + 1}/{cfg.REPLICATIONS} replications done")

    # Extract raw metrics from all replications
    throughput = [float(m.throughput) for m in metrics_list]
    lead_time = [m.avg_lead_time for m in metrics_list]
    oven_busy = [m.oven_util_busy * 100 for m in metrics_list]
    oven_idle = [m.oven_util_idle * 100 for m in metrics_list]
    oven_blocked = [m.oven_util_blocked * 100 for m in metrics_list]
    inspection_util = [m.inspection_util * 100 for m in metrics_list]
    queue_pintura = [m.avg_queue_pintura for m in metrics_list]
    queue_horno = [m.avg_queue_horno for m in metrics_list]

    def ci(values: Sequence[float]) -> tuple[float, float]:
        lo, hi = confidence_interval(values, cfg.T_CRITICAL)
        return lo, hi

    return {
        "name": name,
        "throughput": ci(throughput),
        "lead_time": ci(lead_time),
        "oven_util_busy": ci(oven_busy),
        "oven_util_idle": ci(oven_idle),
        "oven_util_blocked": ci(oven_blocked),
        "inspection_util": ci(inspection_util),
        "avg_queue_pintura": ci(queue_pintura),
        "avg_queue_horno": ci(queue_horno),
    }


def print_results_table(all_results: list[dict[str, tuple[float, float] | str]]) -> None:
    """Output a formatted table or plain text with 95% CI intervals."""
    if not TABLE_AVAILABLE:
        for result in all_results:
            print(f"\nScenario: {result['name']}")
            for key, value in result.items():
                if key == "name":
                    continue
                lo, hi = value  # type: ignore[misc]
                print(f"  {key}: {max(0, lo):.2f} - {hi:.2f}")
        return

    table = PrettyTable()
    table.field_names = [
        "Metric",
        *[str(result["name"]) for result in all_results],
    ]

    metrics = [
        ("Throughput (parts/40h)", "throughput", "parts"),
        ("Avg lead time (min)", "lead_time", "min"),
        ("Oven busy %", "oven_util_busy", "%"),
        ("Oven idle %", "oven_util_idle", "%"),
        ("Oven blocked %", "oven_util_blocked", "%"),
        ("Inspection util %", "inspection_util", "%"),
        ("Avg queue Pintura (parts)", "avg_queue_pintura", ""),
        ("Avg queue Horno (parts)", "avg_queue_horno", ""),
    ]

    for label, key, unit in metrics:
        row = [label]
        for result in all_results:
            lo, hi = result[key]  # type: ignore[misc]

            # Avoid negative lower bounds for utilization/queue metrics
            if key in (
                "avg_queue_pintura",
                "avg_queue_horno",
                "oven_util_blocked",
                "oven_util_idle",
                "oven_util_busy",
                "inspection_util",
            ):
                lo = max(0.0, lo)

            if unit == "parts" and key == "throughput":
                row.append(f"{lo:.1f} - {hi:.1f}")
            elif unit == "%":
                row.append(f"{lo:.1f} - {hi:.1f} %")
            else:
                row.append(f"{lo:.2f} - {hi:.2f} {unit}".strip())

        table.add_row(row)

    print("\n" + "=" * 80)
    print("                  SIMULATION RESULTS (95% Confidence Intervals)")
    print("=" * 80)
    print(table)
    print()


def main() -> None:
    # If --visual flag is passed, launch the live visualisation instead
    if "--visual" in sys.argv:
        from pack_tech_sim.visual import run_visual_all_scenarios

        run_visual_all_scenarios()
        return

    # Three pre-defined scenarios
    results = [
        run_scenario(
            "1. Base",
            cfg.ARRIVAL_BASE,
            inspection_buffer=cfg.SCENARIO1_BUFFER,
        ),
        run_scenario(
            "2. Buffer=5",
            cfg.ARRIVAL_BASE,
            inspection_buffer=cfg.SCENARIO2_BUFFER,
        ),
        run_scenario(
            "3. High demand",
            cfg.ARRIVAL_HIGH,
            inspection_buffer=cfg.SCENARIO3_BUFFER,
        ),
    ]

    print_results_table(results)
    print("All scenarios completed.")


if __name__ == "__main__":
    main()
