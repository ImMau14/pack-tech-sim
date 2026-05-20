# Pack-Tech Sim

A discrete event simulation engine (exercise) designed to optimize capacity, analyze bottleneck constraints, and evaluate flow strategies for precision packaging lines.  

The engine uses SimPy for event scheduling and extends it with custom station logic, blocking, transport delays, and continuous statistics collection.

---

## Index

- [About the Simulation](#about-the-simulation)
- [Understanding the Results](#understanding-the-results)
- [Visual Replay](#visual-replay)
- [Technologies](#technologies)
- [Installation & Usage](#installation--usage)
- [Commands](#commands)
- [Code Quality](#code-quality)
- [License](#license)

---

## About the Simulation

<details>
<summary><strong>Why this project exists</strong></summary>

The simulation addresses a real industrial problem: a packaging line suffering from bottlenecks due to lack of synchronization between the oven and inspection stations.  
The goal is to quantify the impact of adding an intermediate buffer and increasing demand on throughput, lead time, and resource utilisation.

The line consists of five stages: reception → washing → painting → oven → inspection.  
Each station has specific processing times (normal, triangular, uniform, etc.), transport delays, and buffer capacities.  
Three scenarios are evaluated:

1. **Base** – current configuration without buffer between oven and inspection.
2. **Buffer=5** – a 5‑slot buffer is placed before inspection to reduce blocking.
3. **High demand** – the arrival rate increases from Exp(2) to Exp(1.5) minutes.

</details>

<details>
<summary><strong>How the simulation engine works</strong></summary>

The engine is built on top of **SimPy**, a process‑based discrete‑event simulation framework.  
The `SimulatorEngine` class is a thin wrapper around `simpy.Environment` that provides a familiar interface for the rest of the system.

Key design decisions:

- **Stations** are modeled as resources with a fixed number of parallel servers and an optional input buffer. Their behavior is implemented using SimPy processes (`env.process`) and `timeout` calls.
- **Blocking logic** uses a back‑pressure mechanism: if a station cannot send a finished product downstream, the product is placed in a `blocked_items` queue, and upstream stations are notified as soon as space becomes available.
- **Transport‑aware acceptance** (`in_transit` counter) prevents over‑acceptance of products that are still traveling.
- **Statistics** (utilisation, queue lengths, lead times) are collected continuously and aggregated at the end of each 40‑hour replication. State changes and busy‑server integrals are tracked analytically, not by sampling.
- **Inspection utilisation** correctly tracks the integral of busy servers (two parallel operators) so that the reported percentage represents the average utilisation per operator.
- **Confidence intervals** (95 %) are computed using the t‑distribution (30 replications, adjustable via environment variables).

All station logic, queue trackers, and metric aggregation are custom‑built on top of SimPy’s event loop; no other simulation‑specific library is required.

</details>

---

## Understanding the Results

When you run `uv run start`, the program prints a table like the one below (values are illustrative).

<details>
<summary><strong>Example output table</strong></summary>

```
================================================================================
                  SIMULATION RESULTS (95% Confidence Intervals)
================================================================================
+---------------------------+---------------------+---------------------+---------------------+
|           Metric          |       1. Base       |     2. Buffer=5     |    3. High demand   |
+---------------------------+---------------------+---------------------+---------------------+
|   Throughput (parts/40h)  |    542.2 - 545.4    |    753.9 - 758.2    |    542.4 - 545.8    |
|    Avg lead time (min)    | 669.65 - 681.03 min | 458.62 - 471.07 min | 802.42 - 812.43 min |
|        Oven busy %        |    68.0 - 68.4 %    |    88.1 - 90.7 %    |    68.0 - 68.5 %    |
|        Oven idle %        |     1.1 - 1.2 %     |     1.1 - 1.2 %     |     1.1 - 1.1 %     |
|       Oven blocked %      |    30.3 - 30.7 %    |     3.4 - 3.9 %     |    30.3 - 30.8 %    |
|     Inspection util %     |    67.7 - 68.0 %    |    94.7 - 95.3 %    |    67.8 - 68.1 %    |
| Avg queue Pintura (parts) |     8.84 - 8.87     |     8.67 - 8.71     |     8.89 - 8.91     |
|  Avg queue Horno (parts)  |     8.91 - 8.93     |     8.41 - 8.44     |     8.93 - 8.94     |
+---------------------------+---------------------+---------------------+---------------------+
```

</details>

**Each row shows the 95% confidence interval (lower – upper) for one metric across the 30 replications.**

| Metric                | What it tells you                                                                                                                                     |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Throughput**        | Total finished products in 40 hours. Higher is better.                                                                                                |
| **Avg lead time**     | Average time a product spends in the system (from arrival to exit). Lower is better.                                                                  |
| **Oven busy %**       | Percentage of time the oven is actually processing. Indicates how much of its capacity is used.                                                       |
| **Oven idle %**       | Percentage of time the oven is empty (no work).                                                                                                       |
| **Oven blocked %**    | Percentage of time the oven is blocked because inspection cannot accept the finished part. A high value means the oven is starved and unable to work. |
| **Inspection util %** | Average utilisation per inspection operator (two operators). 100 % means both are always busy.                                                        |
| **Avg queue Pintura** | Average number of products waiting in front of the painting station (buffer capacity = 10).                                                           |
| **Avg queue Horno**   | Average number of products waiting in front of the oven (buffer capacity = 10).                                                                       |

If the lower bound of an interval is negative (e.g., `-0.01`), it is physically impossible; the code truncates negative bounds to zero for queue lengths and utilisation percentages.

---

## Visual Replay

In addition to the batch simulation, the project includes a **live animated view** built with [Rich](https://github.com/Textualize/rich).  
It shows the three scenarios running side‑by‑side in real time, with metrics panels and station tables that update continuously.

To launch it:

```bash
uv run start --visual
```

The display is divided into three rows (Base, Buffer=5, High demand). Each row contains:

- **Metrics panel** – arrivals, throughput, average lead time, oven busy/blocked percentages, and inspection utilisation.
- **Station table** – current state of each station (Washing, Painting, Oven, Inspection), showing capacity, products being processed, blocked items, queue lengths, and a colour‑coded state (`BUSY` in green, `BLOCKED` in red, `Idle` in dim).

The animation pauses at the end and waits for **Enter** before exiting, so you can examine the final state.  
This feature fulfills the “Animation & Visualization” requirement by letting you identify bottlenecks visually without relying on external simulation software.

---

## Technologies

This project is primarily built with:

- **[Python](https://www.python.org/)** – "Python is a programming language that lets you work quickly and integrate systems more effectively."
- **[SimPy](https://pypi.org/project/simpy/)** – "SimPy is a process-based discrete-event simulation framework based on standard Python."
- **[PrettyTable](https://pypi.org/project/prettytable/)** – "PrettyTable is a simple Python library for easily displaying tabular data in a visually appealing ASCII table format."
- **[python-dotenv](https://pypi.org/project/python-dotenv/)** – "Python-dotenv reads key-value pairs from a .env file and can set them as environment variables."
- **[Rich](https://github.com/Textualize/rich)** – "Rich is a Python library for rich text and beautiful formatting in the terminal."

> [!NOTE]
> The simulation engine is built on top of SimPy’s event queue; all station behaviours, blocking, transport handling, and statistics are implemented as custom SimPy processes.

---

## Installation & Usage

> [!IMPORTANT]
> **Recommended Requirements**
>
> - **Python** 3.12 or higher.
> - **uv** 0.11 or higher.

1. **Clone the repository and enter the directory:**

```bash
git clone https://github.com/ImMau14/pack-tech-sim.git
cd pack-tech-sim
```

2. **Sync the project environment:**

```bash
uv sync
```

3. **(Optional) Configure parameters:**  
   Copy the provided `.env.template` (or create a `.env` file) and adjust the simulation parameters (hours, buffer sizes, arrival rates, etc.). If no `.env` is present, default values are used.

4. **Run the simulation:**

```bash
uv run start
```

5. **(Optional) Launch the visual replay:**

```bash
uv run start --visual
```

> [!NOTE]
> You can also run the package directly if installed in your environment using the `start` command defined in `pyproject.toml`.

---

## Commands

| Command                 | Description                                                               |
| ----------------------- | ------------------------------------------------------------------------- |
| `uv run start`          | Runs the batch simulation (30 replications) and prints the results table. |
| `uv run start --visual` | Launches the live animated view of the three scenarios simultaneously.    |
| `uv run lint`           | Analyzes the code using Ruff to find issues.                              |
| `uv run fix`            | Automatically fixes linting errors and formats the code.                  |
| `uv run check`          | Performs static type checking with Pyright.                               |
| `uv sync`               | Synchronizes the virtual environment with the lockfile.                   |

> [!NOTE]
> These commands map to the scripts defined in the `[project.scripts]` section of the `pyproject.toml` file.

---

## Code Quality

This project includes professional-grade code quality tools:

- **[Ruff](https://docs.astral.sh/ruff/)** – "An extremely fast Python linter and code formatter, written in Rust."
- **[Pyright](https://microsoft.github.io/pyright/)** – "Pyright is a static type checker for Python."

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.
