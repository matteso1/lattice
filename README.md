# Lattice

A reactive Python framework for building high-performance data applications.

## The Problem

Building interactive data applications in Python today is painful:

```
You write a Streamlit app.
User moves a slider.
Your entire script reruns.
Every. Single. Time.
```

This means:

- Slow interactions (100-500ms delays)
- Wasted computation (recalculating things that did not change)
- Poor scalability (memory and CPU blow up with users)
- No collaboration (each user is isolated)

Existing tools force you to choose between ease of use and performance. Streamlit is simple but slow. Dash is faster but complex. Neither supports real-time collaboration.

## The Solution

Lattice rethinks how Python UI frameworks work:

```
You write a Lattice app.
User moves a slider.
Only the affected code reruns.
Everything else stays cached.
```

This is called **incremental computation**. Instead of re-executing your entire program, Lattice tracks dependencies and updates only what changed.

## How It Works

### Traditional Approach (Streamlit)

```
User Input
    |
    v
+------------------+
| Rerun Everything |  <-- Entire script executes
+------------------+
    |
    v
Render Full UI
```

### Lattice Approach

```
User Input
    |
    v
+------------------+
| Update Signal    |  <-- Only the changed value
+------------------+
    |
    v
+------------------+
| Propagate Delta  |  <-- Only affected computations
+------------------+
    |
    v
Patch UI
```

## Architecture

The framework has three layers:

```
+-----------------------------------------------------------+
|                     Python API                             |
|  Decorators, type hints, familiar syntax                   |
+-----------------------------------------------------------+
                           |
                           | PyO3 bindings
                           v
+-----------------------------------------------------------+
|                     Rust Core                              |
|  Reactive runtime, dependency graph, incremental engine    |
+-----------------------------------------------------------+
                           |
                           v
+-----------------------------------------------------------+
|                  Execution Targets                         |
|  Server (native)  |  Browser (WASM)  |  Hybrid             |
+-----------------------------------------------------------+
```

### Reactive Primitives

The core abstraction is the **signal**: a container for mutable state that tracks its dependents.

```python
from lattice import signal

# Create reactive state
count = signal(0)

# Read value (establishes dependency if inside reactive context)
print(count.value)  # 0

# Write value (notifies all dependents)
count.value = 5
```

**Memos** are cached computations that re-evaluate only when dependencies change:

```python
from lattice import signal, memo

count = signal(0)

@memo
def doubled():
    return count.value * 2

print(doubled())  # 0
count.value = 5
print(doubled())  # 10 (recomputed because count changed)
print(doubled())  # 10 (cached, count did not change)
```

**Effects** are side effects that run when dependencies change:

```python
from lattice import signal, effect

count = signal(0)

@effect
def log_changes():
    print(f"Count is now: {count.value}")

count.value = 1  # Prints: "Count is now: 1"
count.value = 2  # Prints: "Count is now: 2"
```

### Dependency Graph

Lattice builds a directed acyclic graph (DAG) of dependencies:

```
+----------+     +----------+     +----------+
| signal A | --> | memo X   | --> | effect 1 |
+----------+     +----------+     +----------+
                      |
+----------+          |
| signal B | ---------+
+----------+
```

When signal A changes:

1. Mark memo X as "maybe dirty"
2. Check if memo X inputs actually changed
3. If yes, recompute memo X
4. Notify effect 1

This is O(delta) instead of O(n) - we only touch what changed.

### Why Rust?

The core is written in Rust for three reasons:

1. **Performance**: Rust compiles to native code. No interpreter overhead.
2. **Parallelism**: Rust escapes Python's GIL. True multi-threading.
3. **Safety**: Rust's type system prevents memory bugs at compile time.

This follows the pattern used by Pydantic v2 (17x faster), Polars, and Ruff.

## Project Structure

```
lattice/
    lattice-core/           # Rust crate
        src/
            lib.rs          # PyO3 module exports
            reactive/       # Signal, Memo, Effect
            graph/          # Dependency graph
        python/lattice/     # Python API wrapper
    docs/                   # Technical documentation
    examples/               # Example applications
```

## Development

### Prerequisites

- Rust 1.75 or later
- Python 3.11 or later
- maturin (`pip install maturin`)

### Build

```bash
cd lattice-core
maturin develop  # Build and install in development mode
```

### Test

```bash
cargo test       # Rust tests
pytest tests/    # Python tests
```

## Roadmap

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Core reactive primitives | In Progress |
| 2 | Rendering and transport | Planned |
| 3 | Real-time collaboration | Planned |
| 4 | Performance optimization | Planned |

See [docs/roadmap.md](docs/roadmap.md) for details.

## License

MIT
