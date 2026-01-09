# Lattice

A reactive Python UI framework with a Rust-powered core for building high-performance data applications.

## Overview

Lattice is designed to address fundamental limitations in existing Python UI frameworks for data science and machine learning applications. The framework combines Python's ergonomic API design with Rust's performance characteristics to enable:

- Incremental computation: Only recompute what changed, not the entire script
- Fine-grained reactivity: Surgical UI updates based on dependency tracking
- Multi-target execution: Run server-side, in WebAssembly, or hybrid
- Real-time collaboration: Built-in multiplayer support via CRDTs
- High performance: Rust core with SIMD vectorization and parallel execution

## Architecture

The framework is structured in three layers:

```
Python API Layer (user-facing)
        |
        v
  PyO3 Bindings
        |
        v
Rust Core (lattice-core)
   - Reactive runtime
   - Incremental computation engine
   - Rendering pipeline
   - Collaboration layer
```

See [docs/architecture.md](docs/architecture.md) for detailed technical documentation.

## Project Structure

```
lattice/
    lattice-core/           Rust crate containing the core runtime
    lattice/                Python package with user-facing API
    client/                 Minimal TypeScript client for browser
    docs/                   Technical documentation
    examples/               Example applications
    tests/                  Test suites
```

## Development Status

This project is in early development. See [docs/roadmap.md](docs/roadmap.md) for the planned phases.

## Building from Source

### Prerequisites

- Rust 1.75 or later
- Python 3.11 or later
- Node.js 20 or later (for client development)
- maturin (for building Python bindings)

### Build Instructions

```bash
# Install maturin
pip install maturin

# Build the Rust core with Python bindings
cd lattice-core
maturin develop

# Run tests
cargo test
pytest tests/
```

## Documentation

- [Architecture Overview](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [Contributing](CONTRIBUTING.md)

## License

MIT License. See LICENSE for details.
