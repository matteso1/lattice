# Lattice Architecture

This document describes the technical architecture of Lattice, explaining how the
components work together to provide a high-performance reactive UI framework.

## Table of Contents

1. [Design Goals](#design-goals)
2. [System Overview](#system-overview)
3. [Core Components](#core-components)
4. [Data Flow](#data-flow)
5. [Execution Modes](#execution-modes)
6. [Performance Characteristics](#performance-characteristics)

## Design Goals

Lattice is designed around five core principles:

1. **Incremental Computation**: Never recompute more than necessary. When state
   changes, only the dependent computations should re-execute.

2. **Zero-Cost Abstractions**: The Python API should feel natural while the
   underlying implementation achieves near-native performance.

3. **Multi-Target Execution**: The same application code should run server-side,
   in WebAssembly, or in a hybrid configuration.

4. **Collaborative by Default**: Real-time collaboration should be a first-class
   feature, not an afterthought.

5. **Debuggability**: The system should be transparent and easy to understand
   when things go wrong.

## System Overview

```
+------------------------------------------------------------------+
|                        Python Layer                               |
|  +------------------+  +------------------+  +------------------+ |
|  | User Application |  | Component DSL    |  | Python Bindings  | |
|  +------------------+  +------------------+  +------------------+ |
+------------------------------------------------------------------+
                              |
                              | PyO3
                              v
+------------------------------------------------------------------+
|                        Rust Core                                  |
|  +------------------+  +------------------+  +------------------+ |
|  | Reactive Runtime |  | Incremental Eng. |  | Render Pipeline  | |
|  +------------------+  +------------------+  +------------------+ |
|  +------------------+  +------------------+  +------------------+ |
|  | CRDT Layer       |  | Transport        |  | Data Operations  | |
|  +------------------+  +------------------+  +------------------+ |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|                     Execution Targets                             |
|  +------------------+  +------------------+  +------------------+ |
|  | Server (Native)  |  | Browser (WASM)   |  | Hybrid           | |
|  +------------------+  +------------------+  +------------------+ |
+------------------------------------------------------------------+
```

## Core Components

### 1. Reactive Runtime

The reactive runtime manages the dependency graph between signals, memos, and
effects. It tracks which computations depend on which pieces of state.

Key concepts:

- **Signal**: A container for mutable state. When read within a tracking context,
  the signal registers the current computation as a dependent.

- **Memo**: A derived value that caches its result. Re-evaluates only when its
  dependencies change.

- **Effect**: A side-effecting computation that runs when its dependencies change.

Implementation details are in `lattice-core/src/reactive/`.

### 2. Incremental Computation Engine

The incremental engine determines the minimal set of computations to re-run when
state changes. This is inspired by Differential Dataflow but adapted for UI
rendering.

The algorithm:

1. When a signal value changes, mark all direct dependents as "potentially dirty"
2. Walk the dependency graph, propagating the dirty state
3. For each dirty computation, check if its inputs actually changed
4. If inputs changed, re-run the computation and propagate to dependents
5. If inputs are the same, mark as clean without re-running

This is called "push-pull" dirty checking: we push dirty flags down and pull
recomputation up only when needed.

### 3. Rendering Pipeline

The rendering pipeline converts the component tree into DOM updates:

1. **Virtual DOM Construction**: Components return a virtual DOM representation
2. **Diffing**: Compare new virtual DOM against previous version
3. **Patch Generation**: Generate minimal set of DOM operations
4. **Patch Transmission**: Send patches to client via WebSocket or apply directly

The renderer uses keyed reconciliation for efficient list updates.

### 4. CRDT Layer

For collaborative features, application state is represented as Conflict-free
Replicated Data Types (CRDTs). This enables:

- Offline editing with automatic sync on reconnection
- Concurrent edits by multiple users without conflicts
- Deterministic state resolution across all clients

We implement a subset of the Yjs protocol for compatibility with existing tools.

### 5. Transport Layer

Communication between server and client uses a binary protocol:

- **WebSocket**: For real-time bidirectional communication
- **MessagePack**: Binary serialization format (30% smaller than JSON)
- **WebRTC**: Optional peer-to-peer communication for reduced latency

## Data Flow

A typical interaction follows this path:

```
1. User interacts with UI element in browser

2. Client serializes event, sends via WebSocket

3. Server deserializes event, updates signal value

4. Reactive runtime marks dependents as dirty

5. Incremental engine determines minimal recomputation

6. Affected computations re-run

7. Renderer diffs the changed component subtrees

8. Patches sent to client via WebSocket

9. Client applies patches to DOM
```

Total latency target: under 10ms for steps 2-9.

## Execution Modes

### Server Mode

The Rust core runs on the server. All computation happens server-side.
The client is a thin layer that applies DOM patches.

Advantages:

- Full access to server resources (files, databases)
- Simpler security model
- Works with any data size

Disadvantages:

- Requires server infrastructure
- Latency for each interaction

### WASM Mode

The Rust core compiles to WebAssembly and runs in the browser.
No server required after initial load.

Advantages:

- No server infrastructure needed
- Works offline
- Zero-latency interactions

Disadvantages:

- Limited data size (browser memory)
- Initial load time for WASM bundle
- Cannot access server resources directly

### Hybrid Mode

Core runs in browser, but can stream data from server.
Best of both worlds for many use cases.

## Performance Characteristics

### Time Complexity

| Operation | Complexity | Notes |
|-----------|------------|-------|
| Signal read | O(1) | Hash table lookup |
| Signal write | O(d) | d = number of direct dependents |
| Incremental update | O(delta) | delta = changed nodes in graph |
| DOM patch | O(p) | p = number of patches |

### Memory Usage

- Each signal: ~48 bytes + value size
- Each memo: ~64 bytes + cached value size
- Dependency edges: ~16 bytes each

### Benchmarks

Target performance (to be validated):

| Metric | Streamlit | Lattice Target |
|--------|-----------|----------------|
| Update latency | 100-500ms | less than 10ms |
| Memory per session | 50-100MB | less than 10MB |
| Concurrent users | ~50 | 1000+ |
