# Lattice

A reactive Python framework for building high-performance data applications.

## What is Lattice?

Lattice is a Python UI framework that uses **incremental computation** to make data applications fast. Instead of re-executing your entire program when something changes, Lattice tracks dependencies and updates only what needs updating.

## The Problem

Data application frameworks like Streamlit re-run your entire script on every user interaction:

```mermaid
flowchart LR
    A[User clicks button] --> B[Run entire script]
    B --> C[Load data]
    C --> D[Process data]
    D --> E[Compute stats]
    E --> F[Generate charts]
    F --> G[Render UI]
```

This causes:

- **Slow interactions**: 100-500ms delays on every click
- **Wasted computation**: Recalculating unchanged values
- **Poor scalability**: Memory and CPU usage grows with complexity
- **No collaboration**: Each user session is isolated

## The Solution

Lattice only re-runs the code that depends on what changed:

```mermaid
flowchart LR
    A[User clicks button] --> B[Update signal]
    B --> C{What depends on this?}
    C --> D[Recompute affected memo]
    D --> E[Patch UI]
    
    style B fill:#2ecc71
    style D fill:#2ecc71
    style E fill:#2ecc71
```

Result: **Sub-10ms updates** instead of hundreds of milliseconds.

## How It Works

### Reactive Primitives

Lattice provides three core primitives:

```mermaid
flowchart TB
    subgraph Signals
        S1[count = signal 0]
        S2[name = signal Alice]
    end
    
    subgraph Memos
        M1[doubled = count * 2]
        M2[greeting = Hello name]
    end
    
    subgraph Effects
        E1[log count to console]
        E2[update DOM]
    end
    
    S1 --> M1
    S1 --> E1
    S2 --> M2
    M1 --> E2
    M2 --> E2
```

**Signals** hold mutable state:

```python
from lattice import signal

count = signal(0)
count.value = 5  # Notifies all dependents
```

**Memos** cache derived values:

```python
from lattice import signal, memo

count = signal(0)

@memo
def doubled():
    return count.value * 2  # Only recomputes when count changes
```

**Effects** run side effects:

```python
from lattice import signal, effect

count = signal(0)

@effect
def log_changes():
    print(f"Count: {count.value}")  # Runs when count changes
```

### Dependency Tracking

When you read a signal inside a memo or effect, Lattice automatically records that dependency:

```mermaid
sequenceDiagram
    participant User
    participant Effect
    participant Signal
    participant Context
    
    User->>Effect: Create effect
    Effect->>Context: Enter tracking context
    Effect->>Signal: Read value
    Signal->>Context: Register dependency
    Effect->>Context: Exit context
    
    Note over Effect,Signal: Now Effect depends on Signal
    
    User->>Signal: Set new value
    Signal->>Effect: Notify change
    Effect->>Effect: Re-run
```

### Update Propagation

When a signal changes, updates flow through the dependency graph:

```mermaid
flowchart TB
    subgraph "1. Signal Changes"
        S[Signal A]
    end
    
    subgraph "2. Mark Dirty"
        M1[Memo X]
        M2[Memo Y]
    end
    
    subgraph "3. Recompute"
        E1[Effect 1]
        E2[Effect 2]
    end
    
    S -->|mark maybe-dirty| M1
    S -->|mark maybe-dirty| M2
    M1 -->|if value changed| E1
    M2 -->|if value changed| E2
```

This is O(delta) complexity - proportional to what changed, not total program size.

## Architecture

```mermaid
flowchart TB
    subgraph Python["Python Layer"]
        API[User API]
        DEC[Decorators]
        WRAP[Type Wrappers]
    end
    
    subgraph Rust["Rust Core"]
        SIG[Signal Runtime]
        MEM[Memo Cache]
        EFF[Effect Scheduler]
        GRAPH[Dependency Graph]
    end
    
    subgraph Target["Execution Targets"]
        SRV[Server Native]
        WASM[Browser WASM]
        HYB[Hybrid]
    end
    
    API --> DEC
    DEC --> WRAP
    WRAP -->|PyO3| SIG
    SIG --> GRAPH
    MEM --> GRAPH
    EFF --> GRAPH
    
    GRAPH --> SRV
    GRAPH --> WASM
    GRAPH --> HYB
```

### Why Rust?

The core is written in Rust for three reasons:

1. **Performance**: Native code, no interpreter overhead
2. **Parallelism**: No GIL, true multi-threading
3. **Safety**: Memory bugs caught at compile time

This follows the pattern used by Pydantic v2 (17x faster with Rust core), Polars, and Ruff.

## Project Structure

```
lattice/
    lattice-core/           # Rust crate
        src/
            lib.rs          # PyO3 module entry
            reactive/       # Signal, Memo, Effect
            graph/          # Dependency tracking
        python/
            lattice/        # Python API wrapper
    docs/                   # Documentation
    examples/               # Example apps
```

## Quick Start

### Prerequisites

- Rust 1.75+
- Python 3.11+
- maturin

### Installation

```bash
git clone https://github.com/matteso1/lattice
cd lattice/lattice-core
pip install maturin
maturin develop
```

### Usage

```python
from lattice import signal, memo, effect

# Create reactive state
count = signal(0)
name = signal("World")

# Derive computed values
@memo
def greeting():
    return f"Hello, {name.value}! Count: {count.value}"

# React to changes
@effect
def on_change():
    print(greeting())

# Update state
count.value = 1  # Prints: "Hello, World! Count: 1"
name.value = "Lattice"  # Prints: "Hello, Lattice! Count: 1"
```

## Roadmap

```mermaid
gantt
    title Development Phases
    dateFormat  YYYY-MM-DD
    section Phase 1
    Reactive Primitives    :done, p1, 2026-01-09, 14d
    section Phase 2
    Rendering Pipeline     :p2, after p1, 28d
    section Phase 3
    Collaboration          :p3, after p2, 28d
    section Phase 4
    Performance Optimization :p4, after p3, 28d
```

| Phase | Focus | Status |
| ----- | ----- | ------ |
| 1 | Reactive primitives (Signal, Memo, Effect) | In Progress |
| 2 | Rendering and WebSocket transport | Planned |
| 3 | CRDT-based collaboration | Planned |
| 4 | JIT compilation and optimization | Planned |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## License

MIT License. See [LICENSE](LICENSE).
