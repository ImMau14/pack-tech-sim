# Builds the production line and runs a single replication.
# Tracks queue lengths and feeds results into ReplicationMetrics.

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass

import pack_tech_sim.config as cfg
from pack_tech_sim.core.engine import SimulatorEngine
from pack_tech_sim.core.entities import Product, Source, Station
from pack_tech_sim.stats import ReplicationMetrics


@dataclass
class QueueTracker:
    """Accumulates the time-weighted length of a station's input queue."""
    env: SimulatorEngine
    station: Station
    last_time: float = 0.0
    accum: float = 0.0

    def update(self) -> None:
        """Call on every queue change to capture the integral piece."""
        now = self.env.now
        dt = now - self.last_time
        if dt > 0:
            self.accum += len(self.station.input_queue) * dt
            self.last_time = now

    def finalise(self, until: float) -> None:
        """Add the final segment up to `until`."""
        if until < self.last_time:
            return
        self.accum += len(self.station.input_queue) * (until - self.last_time)
        self.last_time = until


@dataclass
class SimulationLine:
    """Container for a complete production line and its associated trackers."""
    source: Source
    lavado: Station
    pintura: Station
    horno: Station
    inspeccion: Station
    env: SimulatorEngine
    tracker_pintura: QueueTracker
    tracker_horno: QueueTracker

    def finalise(self, until: float) -> None:
        for station in (self.lavado, self.pintura, self.horno, self.inspeccion):
            station.finalise(until)
        self.tracker_pintura.finalise(until)
        self.tracker_horno.finalise(until)


def build_line(
    arrival_dist: Callable[[], float],
    inspection_buffer_size: int,
    horizon: float = cfg.SIMULATION_MINUTES,
) -> SimulationLine:
    """Assemble the four stations (Washing → Painting → Oven → Inspection)
    with the given inspection buffer and return a SimulationLine ready to run."""
    env = SimulatorEngine()

    lavado = Station(
        env,
        "Lavado",
        capacity=5,
        buffer_capacity=float("inf"),  # infinite queue before washing
        processing_time_dist=cfg.LAVADO_PROC,
        transport_time_dist=cfg.TRANSPORT_LAVADO_PINTURA,
    )

    pintura = Station(
        env,
        "Pintura",
        capacity=3,
        buffer_capacity=10,
        processing_time_dist=cfg.PINTURA_PROC,
        transport_time_dist=cfg.TRANSPORT_PINTURA_HORNO,
    )

    horno = Station(
        env,
        "Horno",
        capacity=1,                     # single oven
        buffer_capacity=10,
        processing_time_dist=cfg.HORNO_PROC,
        transport_time_dist=cfg.TRANSPORT_HORNO_INSPECCION,
    )

    inspeccion = Station(
        env,
        "Inspección",
        capacity=2,
        buffer_capacity=inspection_buffer_size,  # configurable
        processing_time_dist=cfg.INSPECCION_PROC,
        transport_time_dist=lambda: 0.0,          # no transport after inspection
    )

    # Wire the flow
    lavado.downstream = pintura
    pintura.upstream = lavado
    pintura.downstream = horno
    horno.upstream = pintura
    horno.downstream = inspeccion
    inspeccion.upstream = horno

    source = Source(env, arrival_dist, cfg.TRANSPORT_TO_LAVADO, lavado, horizon)

    tracker_pintura = QueueTracker(env, pintura)
    tracker_horno = QueueTracker(env, horno)

    pintura.on_queue_change = tracker_pintura.update
    horno.on_queue_change = tracker_horno.update

    return SimulationLine(
        source=source,
        lavado=lavado,
        pintura=pintura,
        horno=horno,
        inspeccion=inspeccion,
        env=env,
        tracker_pintura=tracker_pintura,
        tracker_horno=tracker_horno,
    )


def run_replication(
    arrival_dist: Callable[[], float],
    inspection_buffer_size: int,
) -> ReplicationMetrics:
    """Execute one full replication and return its metrics."""
    random.seed()  # ensure distinct random streams across replications

    line = build_line(arrival_dist, inspection_buffer_size)

    metrics = ReplicationMetrics()

    def record_exit(product: Product) -> None:
        lead_time = line.env.now - product.arrival_time
        metrics.throughput += 1
        metrics.total_lead_time += lead_time
        metrics.lead_time_count += 1

    line.inspeccion.on_exit = record_exit

    total_time = cfg.SIMULATION_MINUTES
    line.source.start()
    line.env.run(until=total_time)

    # Gather raw counters before computing final ratios
    line.finalise(total_time)

    metrics.oven_busy_time = line.horno.stats_busy_time
    metrics.oven_idle_time = line.horno.stats_idle_time
    metrics.oven_blocked_time = line.horno.stats_blocked_time
    metrics.inspection_busy_time = line.inspeccion.busy_servers_integral
    metrics.queue_pintura_time_sum = line.tracker_pintura.accum
    metrics.queue_horno_time_sum = line.tracker_horno.accum

    metrics.finalise(total_time)
    return metrics
