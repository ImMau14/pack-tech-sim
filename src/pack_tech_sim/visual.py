# Live visualisation of all three scenarios running side-by-side.
# Uses Rich to display metrics and station states in real time.

from __future__ import annotations

import contextlib
import heapq
import math
import time
from collections.abc import Callable
from dataclasses import dataclass

from rich import box
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

import pack_tech_sim.config as cfg
from pack_tech_sim.core.engine import SimulatorEngine
from pack_tech_sim.core.entities import Product, Source, Station
from pack_tech_sim.simulation.scenarios import build_line

_STATION_DISPLAY = {
    "Lavado": "Washing",
    "Pintura": "Painting",
    "Horno": "Oven",
    "Inspección": "Inspection",
}


@dataclass
class ScenarioState:
    """Holds all simulation objects for one scenario and collects its runtime stats."""
    name: str
    source: Source
    lavado: Station
    pintura: Station
    horno: Station
    inspeccion: Station
    env: SimulatorEngine
    throughput: int = 0
    total_lead_time: float = 0.0
    lead_time_count: int = 0
    arrivals: int = 0
    display_time: float = 0.0  # snapshot time used after the sim ends

    def _time_reference(self) -> float:
        """Use frozen display_time after finalisation, else current sim time."""
        return self.display_time if self.display_time > 0 else self.env.now

    def finalise(self, until: float | None = None) -> None:
        """Force finalise all stations and store the snapshot time."""
        target = self.env.now if until is None else until
        for station in (self.lavado, self.pintura, self.horno, self.inspeccion):
            station.finalise(target)
        self.display_time = target

    def make_metrics_panel(self) -> Panel:
        """Rich panel summarising key performance indicators."""
        elapsed = max(1.0, self._time_reference())
        avg_lt = self.total_lead_time / self.lead_time_count if self.lead_time_count else 0.0
        horno_busy = self.horno.stats_busy_time / elapsed * 100
        horno_blocked = self.horno.stats_blocked_time / elapsed * 100
        ins_busy = self.inspeccion.busy_servers_integral / (2 * elapsed) * 100

        text = (
            f"[bold]Arrivals:[/] {self.arrivals}\n"
            f"[bold]Throughput:[/] {self.throughput}\n"
            f"[bold]Avg lead time:[/] {avg_lt:.1f} min\n"
            f"[bold]Oven busy:[/] {horno_busy:.1f}%\n"
            f"[bold]Oven blocked:[/] {horno_blocked:.1f}%\n"
            f"[bold]Inspection util:[/] {ins_busy:.1f}%"
        )
        return Panel(text, title=f"{self.name} Metrics", border_style="blue")

    def make_station_table(self) -> Table:
        """Rich table showing current queue lengths, state, and utilisation."""
        elapsed = max(1.0, self._time_reference())
        table = Table(
            title=f"{self.name} - Time: {elapsed:.1f}/{cfg.SIMULATION_MINUTES} min",
            box=box.ROUNDED,
            expand=True,
            title_style="bold cyan",
        )
        table.add_column("Station", style="bold yellow")
        table.add_column("Cap.", justify="center")
        table.add_column("Proc.", justify="center")
        table.add_column("Blocked", justify="center")
        table.add_column("Queue", justify="center")
        table.add_column("Max Q", justify="center")
        table.add_column("State", justify="center")
        table.add_column("Util.", justify="center")

        for st_name, st in [
            ("Lavado", self.lavado),
            ("Pintura", self.pintura),
            ("Horno", self.horno),
            ("Inspección", self.inspeccion),
        ]:
            display = _STATION_DISPLAY.get(st_name, st_name)
            in_proc = len(st.processing)
            blocked = len(st.blocked_items)
            queue_len = len(st.input_queue)
            max_q = st.buffer_capacity if st.buffer_capacity != float("inf") else "∞"

            if blocked > 0:
                state = "[bold red]BLOCKED[/]"
            elif in_proc > 0:
                state = "[green]BUSY[/]"
            else:
                state = "[dim]Idle[/]"

            if st.capacity > 0:
                util = (in_proc / st.capacity) * 100
                util_str = f"{util:.0f}%"
            else:
                util_str = "N/A"

            table.add_row(
                display,
                str(st.capacity),
                str(in_proc),
                str(blocked),
                str(queue_len),
                str(max_q),
                state,
                util_str,
            )

        return table


def _build_layout(states: list[ScenarioState], headline: str) -> Layout:
    """Compose the overall Rich layout: headline + a grid of scenario rows."""
    layout = Layout()
    layout.split(
        Layout(Panel(headline), size=3),
        Layout(name="grid"),
    )

    rows = []
    for state in states:
        row = Layout()
        row.split_row(
            Layout(state.make_metrics_panel(), ratio=1),
            Layout(state.make_station_table(), ratio=3),
        )
        rows.append(row)

    layout["grid"].split_column(*rows)
    return layout


def build_scenario_state(
    scenario_name: str,
    arrival_dist: Callable[[], float],
    buffer_size: int,
) -> ScenarioState:
    """Create the production line for a scenario and attach record-keeping callbacks."""
    line = build_line(arrival_dist, buffer_size)

    state = ScenarioState(
        name=scenario_name,
        source=line.source,
        lavado=line.lavado,
        pintura=line.pintura,
        horno=line.horno,
        inspeccion=line.inspeccion,
        env=line.env,
    )

    def record_exit(product: Product) -> None:
        state.throughput += 1
        lead_time = line.env.now - product.arrival_time
        state.total_lead_time += lead_time
        state.lead_time_count += 1

    def record_arrival(_: Product) -> None:
        state.arrivals += 1

    line.inspeccion.on_exit = record_exit
    line.source.on_create = record_arrival

    return state


def run_visual_all_scenarios(speed_factor: float = 60.0) -> None:
    """Run all three scenarios visually using a synchronised event heap."""
    total_time = cfg.SIMULATION_MINUTES

    states = [
        build_scenario_state("1. Base", cfg.ARRIVAL_BASE, cfg.SCENARIO1_BUFFER),
        build_scenario_state("2. Buffer=5", cfg.ARRIVAL_BASE, cfg.SCENARIO2_BUFFER),
        build_scenario_state("3. High demand", cfg.ARRIVAL_HIGH, cfg.SCENARIO3_BUFFER),
    ]

    for state in states:
        state.source.start()

    # Min-heap of (next_event_time, state_index) for fair interleaving
    heap: list[tuple[float, int]] = []
    for idx, state in enumerate(states):
        next_time = state.env.peek()
        if next_time != math.inf and next_time <= total_time:
            heapq.heappush(heap, (next_time, idx))

    speed = speed_factor if speed_factor > 0 else 1.0
    console = Console()
    start_real = time.time()

    with Live(console=console, screen=True, refresh_per_second=8) as live:
        last_update = 0.0

        while heap:
            current_time, idx = heapq.heappop(heap)

            if current_time > total_time:
                break

            state = states[idx]
            state.env.step()  # advance the environment whose next event is due

            # Re-schedule next event for this scenario
            next_time = state.env.peek()
            if next_time != math.inf and next_time <= total_time:
                heapq.heappush(heap, (next_time, idx))

            # Pace to wall clock using the speed factor
            target_real = current_time / speed
            elapsed_real = time.time() - start_real
            if target_real > elapsed_real:
                time.sleep(target_real - elapsed_real)

            # Limit UI refresh to ~8 Hz
            now_real = time.time()
            if now_real - last_update >= 0.125:
                live.update(
                    _build_layout(
                        states,
                        "[bold magenta]Pack-Tech Sim - All Scenarios Live[/]",
                    )
                )
                last_update = now_real

        # Finalise all stations at the end of the simulation
        for state in states:
            state.finalise(total_time)

        live.update(
            _build_layout(
                states,
                "[bold green]Simulation finished - Press Enter to exit[/]",
            )
        )

        with contextlib.suppress(EOFError):
            console.input("[bold yellow]Press Enter to exit...")

    print("\n=== All scenarios finished ===")
    for state in states:
        avg_lt = state.total_lead_time / state.lead_time_count if state.lead_time_count else 0.0
        elapsed = max(1.0, state.display_time)

        print(f"\n{state.name}:")
        print(f"  Arrivals: {state.arrivals}")
        print(f"  Throughput: {state.throughput}")
        print(f"  Avg lead time: {avg_lt:.1f} min")
        print(f"  Oven busy: {state.horno.stats_busy_time / elapsed * 100:.1f}%")
        print(f"  Oven blocked: {state.horno.stats_blocked_time / elapsed * 100:.1f}%")
        print(
            f"  Inspection util: {state.inspeccion.busy_servers_integral / (2 * elapsed) * 100:.1f}%"
        )
