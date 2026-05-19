# Pack-Tech Sim

A discrete event simulation engine designed to optimize capacity, analyze bottleneck constraints, and evaluate flow strategies for precision packaging lines using only the Python Standard Library.

---

## Index

- [Technologies](#technologies)
- [Building](#building)
- [Installation & Usage](#installation--usage)
- [Commands](#commands)
- [Code Quality](#code-quality)
- [License](#license)

---

## Technologies

This project is primarily built with:

- **[Python](https://www.python.org/)** - "Python is a programming language that lets you work quickly and integrate systems more effectively."
- **[Sympy](https://www.sympy.org/)** - "SymPy is a Python library for symbolic mathematics."

> [!NOTE]
> The project is structured as a package using `src` layout, implementing a custom discrete event simulation engine (`heapq`) alongside `sympy` for analytical validation and confidence interval metrics.

---

## Building

For local development:

```bash
uv sync
uv run start
```

> [!NOTE]
> `uv sync` will automatically create a virtual environment and install all necessary dependencies and dev-tools.

---

## Installation & Usage

> [!IMPORTANT]
> **Recommended Requirements**
> * **Python** 3.12 or higher.
> * **uv** 0.11 or higher.

1. **Clone the repository and enter the directory:**

```bash
git clone [https://github.com/ImMau14/pack-tech-sim.git](https://github.com/ImMau14/pack-tech-sim.git)
cd pack-tech-sim
```

2. **Sync the project environment:**

```bash
uv sync
```

3. **Run the simulation:**

```bash
uv run start
```

> [!NOTE]
> You can also run the package directly if installed in your environment using the `start` command defined in `pyproject.toml`.

---

## Commands

| Command | Description |
| --- | --- |
| `uv run start` | Starts the packaging line simulation CLI execution. |
| `uv run lint` | Analyzes the code using Ruff to find issues. |
| `uv run fix` | Automatically fixes linting errors and formats the code. |
| `uv run check` | Performs static type checking with Pyright. |
| `uv sync` | Synchronizes the virtual environment with the lockfile. |

> [!NOTE]
> These commands map to the scripts defined in the `[project.scripts]` section of the `pyproject.toml` file.

---

## Code Quality

This project includes professional-grade code quality tools:

* **[Ruff](https://docs.astral.sh/ruff/)** – "An extremely fast Python linter and code formatter, written in Rust."
* **[Pyright](https://microsoft.github.io/pyright/)** – "Pyright is a static type checker for Python."

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.
