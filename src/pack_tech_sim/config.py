# Simulation configuration and probability distributions.
# Values are loaded from environment variables or default constants.

from __future__ import annotations

import os
import random

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Global simulation duration
SIMULATION_HOURS = int(os.getenv("SIM_HOURS", "40"))
SIMULATION_MINUTES = SIMULATION_HOURS * 60

# Replication and confidence settings
REPLICATIONS = int(os.getenv("REPLICATIONS", "30"))
CONFIDENCE_LEVEL = float(os.getenv("CONFIDENCE_LEVEL", "0.95"))
T_CRITICAL = 2.045  # t-value for 95% CI with ~30 replications

# Inspection buffer sizes for the three standard scenarios
SCENARIO1_BUFFER = int(os.getenv("SCENARIO1_BUFFER", "0"))
SCENARIO2_BUFFER = int(os.getenv("SCENARIO2_BUFFER", "5"))
SCENARIO3_BUFFER = int(os.getenv("SCENARIO3_BUFFER", "0"))


# --- Factory functions for random variates ---

def exp(mean: float):
    """Exponential distribution (rate = 1/mean)."""
    return lambda: random.expovariate(1.0 / mean)


def normal(mean: float, std: float):
    """Normal distribution, truncated at zero."""
    return lambda: max(0.0, random.normalvariate(mean, std))


def triangular(low: float, high: float, mode: float):
    """Triangular distribution."""
    return lambda: random.triangular(low, high, mode)


def uniform(low: float, high: float):
    """Uniform distribution."""
    return lambda: random.uniform(low, high)


def erlang(mean: float, k: int):
    """Erlang distribution (sum of k exponentials)."""
    sub_mean = mean / k

    def draw():
        return sum(random.expovariate(1.0 / sub_mean) for _ in range(k))

    return draw


# --- Arrival processes ---
ARRIVAL_BASE_MEAN = float(os.getenv("ARRIVAL_BASE_MEAN", "2.0"))
ARRIVAL_HIGH_MEAN = float(os.getenv("ARRIVAL_HIGH_MEAN", "1.5"))

ARRIVAL_BASE = exp(ARRIVAL_BASE_MEAN)
ARRIVAL_HIGH = exp(ARRIVAL_HIGH_MEAN)

# --- Transport times ---
TRANSPORT_TO_LAVADO_MEAN = float(os.getenv("TRANSPORT_TO_LAVADO_MEAN", "3.0"))
TRANSPORT_LAVADO_PINTURA_MEAN = float(
    os.getenv("TRANSPORT_LAVADO_PINTURA_MEAN", "2.0")
)
TRANSPORT_PINTURA_HORNO_LOW = float(os.getenv("TRANSPORT_PINTURA_HORNO_LOW", "2.0"))
TRANSPORT_PINTURA_HORNO_HIGH = float(os.getenv("TRANSPORT_PINTURA_HORNO_HIGH", "5.0"))
TRANSPORT_HORNO_INSPECCION_LOW = float(
    os.getenv("TRANSPORT_HORNO_INSPECCION_LOW", "1.0")
)
TRANSPORT_HORNO_INSPECCION_HIGH = float(
    os.getenv("TRANSPORT_HORNO_INSPECCION_HIGH", "3.0")
)

TRANSPORT_TO_LAVADO = exp(TRANSPORT_TO_LAVADO_MEAN)
TRANSPORT_LAVADO_PINTURA = exp(TRANSPORT_LAVADO_PINTURA_MEAN)
TRANSPORT_PINTURA_HORNO = uniform(TRANSPORT_PINTURA_HORNO_LOW, TRANSPORT_PINTURA_HORNO_HIGH)
TRANSPORT_HORNO_INSPECCION = uniform(
    TRANSPORT_HORNO_INSPECCION_LOW, TRANSPORT_HORNO_INSPECCION_HIGH
)

# --- Processing times ---
LAVADO_MEAN = float(os.getenv("LAVADO_MEAN", "10.0"))
LAVADO_STD = float(os.getenv("LAVADO_STD", "2.0"))

PINTURA_LOW = float(os.getenv("PINTURA_LOW", "4.0"))
PINTURA_HIGH = float(os.getenv("PINTURA_HIGH", "10.0"))
PINTURA_MODE = float(os.getenv("PINTURA_MODE", "8.0"))

HORNO_LOW = float(os.getenv("HORNO_LOW", "2.0"))
HORNO_HIGH = float(os.getenv("HORNO_HIGH", "4.0"))

INSPECCION_MEAN = float(os.getenv("INSPECCION_MEAN", "2.0"))
INSPECCION_ELEMENTS = int(os.getenv("INSPECCION_ELEMENTS", "3"))

LAVADO_PROC = normal(LAVADO_MEAN, LAVADO_STD)
PINTURA_PROC = triangular(PINTURA_LOW, PINTURA_HIGH, PINTURA_MODE)
HORNO_PROC = uniform(HORNO_LOW, HORNO_HIGH)
INSPECCION_PROC = erlang(INSPECCION_MEAN * INSPECCION_ELEMENTS, INSPECCION_ELEMENTS)
