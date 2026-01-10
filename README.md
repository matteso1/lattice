# Lattice

A reactive Python framework for building high-performance data applications with JIT compilation.

[![Tests](https://img.shields.io/badge/tests-71%20passed-brightgreen)](tests/)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)
[![Rust](https://img.shields.io/badge/rust-1.75%2B-orange)](https://rust-lang.org)

## Why Lattice?

| Feature | Lattice | Streamlit | Dash | Reflex |
| ------- | ------- | --------- | ---- | ------ |
| **Reactivity** | Fine-grained | Full rerun | Callbacks | Event handlers |
| **JIT Compilation** | ✅ Cranelift | ❌ | ❌ | ❌ |
| **Real-time Collab** | ✅ Built-in CRDT | ❌ | ❌ | ❌ |
| **Rust Core** | ✅ PyO3 | ❌ | ❌ | ❌ |

**Unique to Lattice:**

- JIT compilation to native code (3000-5000x for hot loops)
- CRDT-based real-time collaboration
- Rust-powered dependency tracking

## Honest Benchmark

```
Scenario: 10 expensive computed values, update ONE, render ALL

                              Lattice         Streamlit-style
Total time (ms)               17.47           185.03
Total recomputations          100             1000     (10x more waste!)

🚀 Lattice is 10.6x FASTER in this realistic scenario
```

**Why?** Lattice only recomputes what changed. Streamlit reruns everything.

## Quick Start

```bash
git clone https://github.com/matteso1/lattice
cd lattice/lattice-core
pip install maturin aiohttp pycrdt
maturin develop
pytest tests/ -v  # 71 tests
```

## Usage

```python
from lattice import signal, memo, effect

count = signal(0)

@memo
def doubled():
    return count.value * 2  # Only recomputes when count changes

@effect
def log():
    print(f"Count: {count.value}, Doubled: {doubled()}")

count.value = 5  # Prints: "Count: 5, Doubled: 10"
```

## Features

### 1. Fine-Grained Reactivity

```python
@memo
def expensive():
    return process_data(data.value)  # Cached until data changes
```

### 2. Real-Time Collaboration

```python
from lattice.collab import Room, collaborative_signal

room = Room("my-room")
counter = collaborative_signal(room, "counter", 0)
counter.value += 1  # Syncs to all connected clients
```

### 3. JIT Compilation

```python
from lattice._core import JitCompiler
compiler = JitCompiler()
result = compiler.compile_and_run(ir_json, [5.0, 3.0])
# 3000-5000x faster than Python eval for traced expressions
```

## Stress Test Results

| Test | Result |
| ---- | ------ |
| Signal updates | 460,000/sec |
| 10,000 signals | 9.85ms create |
| CRDT sync | 10,500 ops/sec |
| JIT speedup | 3000-5000x |

## Demos

```bash
python examples/realistic_benchmark.py   # Honest comparison
python examples/jit_benchmark.py         # JIT speedup
python examples/stress_test.py           # Limits test
```

## Collaboration Deployment

| Option | Description |
| ------ | ----------- |
| **Local** | Works now (same network) |
| **y-websocket** | Self-hosted sync server |
| **Liveblocks** | Managed service |

## PyPI Publishing

```bash
maturin build --release
twine upload target/wheels/*.whl
```

## License

MIT
