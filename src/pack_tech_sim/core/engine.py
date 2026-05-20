# Thin wrapper around SimPy's Environment. Allows future customisation while
# keeping the interface compatible.

from __future__ import annotations

import simpy


class SimulatorEngine(simpy.Environment):
    """Compatibility alias over SimPy's Environment."""
