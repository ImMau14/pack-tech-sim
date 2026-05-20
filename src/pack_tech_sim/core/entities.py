# Core simulation entities: products, multi-server stations with blocking and
# transport delays, and an arrival source. All time-varying statistics are
# tracked here.

from __future__ import annotations

import contextlib
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

from pack_tech_sim.core.engine import SimulatorEngine


@dataclass(slots=True)
class Product:
    """Simple product with an ID and arrival timestamp for lead-time tracking."""
    product_id: int
    arrival_time: float


class Station:
    """A multi-server station with a finite input buffer, processing, blocking,
    downstream transport, and detailed utilisation stats."""

    def __init__(
        self,
        env: SimulatorEngine,
        name: str,
        capacity: int,
        buffer_capacity: float,
        processing_time_dist: Callable[[], float],
        transport_time_dist: Callable[[], float],
    ) -> None:
        self.env = env
        self.name = name
        self.capacity = capacity                    # number of servers
        self.buffer_capacity = buffer_capacity      # max queued items (0 means no queue)
        self.processing_time_dist = processing_time_dist
        self.transport_time_dist = transport_time_dist

        self.input_queue: deque[Product] = deque()
        self.processing: list[Product] = []         # products currently being served
        self.blocked_items: deque[Product] = deque()# finished but downstream full
        self.in_transit: int = 0                    # items being transported to this station

        self.downstream: Station | None = None
        self.upstream: Station | None = None

        # State-duration accumulators
        self.stats_busy_time: float = 0.0
        self.stats_idle_time: float = 0.0
        self.stats_blocked_time: float = 0.0
        self._last_state_change: float = 0.0
        self._current_state: str = "idle"

        # Time-average number of busy servers
        self._busy_servers: int = 0
        self._last_busy_change_time: float = 0.0
        self.busy_servers_integral: float = 0.0

        # Optional callbacks
        self.on_exit: Callable[[Product], None] | None = None
        self.on_queue_change: Callable[[], None] | None = None

    def _change_state(self, new_state: str) -> None:
        """Accumulate time in the previous state, then switch."""
        if new_state == self._current_state:
            return

        now = self.env.now
        dt = now - self._last_state_change

        if self._current_state == "idle":
            self.stats_idle_time += dt
        elif self._current_state == "busy":
            self.stats_busy_time += dt
        elif self._current_state == "blocked":
            self.stats_blocked_time += dt

        self._current_state = new_state
        self._last_state_change = now

    def _update_state(self) -> None:
        """Determine the station's aggregate state from its contents."""
        if self.blocked_items:
            self._change_state("blocked")
        elif self.processing:
            self._change_state("busy")
        else:
            self._change_state("idle")

    def _record_busy_servers_change(self) -> None:
        """Integrate the number of busy servers between changes."""
        now = self.env.now
        dt = now - self._last_busy_change_time
        self.busy_servers_integral += self._busy_servers * dt
        self._last_busy_change_time = now
        self._busy_servers = len(self.processing)

    def finalise(self, until: float) -> None:
        """Accumulate time from the last change until `until` for final reporting."""
        if until < self._last_state_change:
            return

        # Finalise the three-state accumulator
        dt = until - self._last_state_change
        if self._current_state == "idle":
            self.stats_idle_time += dt
        elif self._current_state == "busy":
            self.stats_busy_time += dt
        elif self._current_state == "blocked":
            self.stats_blocked_time += dt
        self._last_state_change = until

        # Finalise busy servers integral
        busy_dt = until - self._last_busy_change_time
        if busy_dt > 0:
            self.busy_servers_integral += self._busy_servers * busy_dt
            self._last_busy_change_time = until

    def can_accept(self) -> bool:
        """Check if the station can receive an incoming product."""
        if self.buffer_capacity == 0:
            # No queue: items go directly into processing (if space in servers)
            return (
                len(self.processing) + len(self.blocked_items) + self.in_transit
                < self.capacity
            )

        return (len(self.input_queue) + self.in_transit) < self.buffer_capacity

    def receive_product(self, product: Product) -> None:
        """Called by an upstream station or source after transport."""
        self.in_transit = max(0, self.in_transit - 1)

        if self.buffer_capacity == 0:
            self._record_busy_servers_change()
            self.processing.append(product)
            self._record_busy_servers_change()
            self.env.process(self._process_product(product, self.processing_time_dist()))
        else:
            self.input_queue.append(product)
            if self.on_queue_change is not None:
                self.on_queue_change()
            self._start_processing_if_possible()

        self._update_state()

    def _start_processing_if_possible(self) -> None:
        """Move products from the queue into free servers."""
        while self.input_queue and (
            len(self.processing) + len(self.blocked_items)
        ) < self.capacity:
            product = self.input_queue.popleft()

            if self.on_queue_change is not None:
                self.on_queue_change()

            self._record_busy_servers_change()
            self.processing.append(product)
            self._record_busy_servers_change()

            # Notify upstream that it may now send blocked items
            if self.upstream is not None:
                self.upstream._on_downstream_available()

            self.env.process(self._process_product(product, self.processing_time_dist()))

        self._update_state()

    def _process_product(self, product: Product, process_time: float):
        """SimPy process: wait for the processing time, then complete."""
        yield self.env.timeout(process_time)
        self._complete_processing(product)

    def _complete_processing(self, product: Product) -> None:
        """Finish processing and either exit or try to send downstream."""
        self._record_busy_servers_change()
        with contextlib.suppress(ValueError):
            self.processing.remove(product)
        self._record_busy_servers_change()

        if self.downstream is None:
            # Last station - record exit and free the server
            if self.on_exit is not None:
                self.on_exit(product)

            self._start_processing_if_possible()

            if self.buffer_capacity == 0 and self.upstream is not None:
                self.upstream._on_downstream_available()
        else:
            if self.downstream.can_accept():
                self._send_to_downstream(product)
                self._start_processing_if_possible()

                if self.buffer_capacity == 0 and self.upstream is not None:
                    self.upstream._on_downstream_available()
            else:
                # Downstream full - block this product
                self.blocked_items.append(product)

        self._update_state()

    def _on_downstream_available(self) -> None:
        """Called by downstream when it frees capacity; unblock items."""
        while self.blocked_items and self.downstream and self.downstream.can_accept():
            product = self.blocked_items.popleft()
            self._send_to_downstream(product)
            self._start_processing_if_possible()

            if self.buffer_capacity == 0 and self.upstream is not None:
                self.upstream._on_downstream_available()

        self._update_state()

    def _send_to_downstream(self, product: Product) -> None:
        """Initiate transport delay to the next station."""
        if self.downstream is None:
            return

        self.downstream.in_transit += 1
        self.env.process(
            self._deliver_to_downstream(product, self.transport_time_dist())
        )

    def _deliver_to_downstream(self, product: Product, delay: float):
        """SimPy process: wait for transport, then hand over to downstream."""
        yield self.env.timeout(delay)
        if self.downstream is not None:
            self.downstream.receive_product(product)


class Source:
    """Generates products according to an inter-arrival distribution and sends
    them through a transport delay to the first station."""

    def __init__(
        self,
        env: SimulatorEngine,
        inter_arrival_dist: Callable[[], float],
        transport_dist: Callable[[], float],
        first_station: Station,
        horizon: float,
    ) -> None:
        self.env = env
        self.inter_arrival = inter_arrival_dist
        self.transport = transport_dist
        self.first_station = first_station
        self.horizon = horizon
        self._product_counter = 0
        self.on_create: Callable[[Product], None] | None = None

    def start(self):
        """Kick off the arrival generator process."""
        return self.env.process(self.run())

    def run(self):
        """Main arrival loop: wait, create product, transport it."""
        while True:
            delay = self.inter_arrival()
            if self.env.now + delay > self.horizon:
                break  # stop if next arrival would exceed simulation horizon

            yield self.env.timeout(delay)

            self._product_counter += 1
            product = Product(self._product_counter, self.env.now)

            if self.on_create is not None:
                self.on_create(product)

            self.env.process(self._transport_product(product))

    def _transport_product(self, product: Product):
        """Transport the newly created product to the first station."""
        yield self.env.timeout(self.transport())
        self.first_station.receive_product(product)
