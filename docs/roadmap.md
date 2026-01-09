# Development Roadmap

This document outlines the phased implementation plan for Lattice.

## Phase 1: Core Runtime (Weeks 1-4)

The foundation: reactive primitives and incremental computation.

### Week 1-2: Reactive Primitives

Implement the core reactive system in Rust:

- Signal: Mutable state container with dependency tracking
- Memo: Cached derived values
- Effect: Side-effecting computations

These follow the fine-grained reactivity model used in SolidJS and Leptos.

### Week 3-4: Incremental Computation Engine

Build the dependency graph and delta propagation:

- Computational DAG data structure
- Push-pull dirty checking algorithm
- Minimal recomputation scheduling

## Phase 2: Rendering and Transport (Weeks 5-8)

Connect the reactive core to actual UI rendering.

### Week 5-6: Virtual DOM and Diffing

- Virtual DOM representation in Rust
- Keyed diffing algorithm
- Patch generation

### Week 7-8: WebSocket Transport

- Server implementation with Tokio
- Binary protocol with MessagePack
- Minimal TypeScript client

## Phase 3: Collaboration Layer (Weeks 9-12)

Add real-time collaboration support.

### Week 9-10: CRDT Implementation

- Design state model as CRDTs
- Implement sync protocol

### Week 11-12: Multiplayer Features

- Presence API (cursors, selections)
- Offline persistence

## Phase 4: Performance Optimization (Weeks 13-16)

Push performance to the limit.

### Week 13-14: JIT Compilation

- Python function tracing
- Rust IR generation
- LLVM backend integration

### Week 15-16: Data Operations

- Polars integration
- SIMD vectorization
- Parallel execution

## Milestones

| Milestone | Target | Success Criteria |
|-----------|--------|------------------|
| M1: Reactive Core | Week 2 | Signals, memos, effects working |
| M2: Basic App | Week 6 | Counter app running in browser |
| M3: Benchmark | Week 8 | Demonstrate 10x faster than Streamlit |
| M4: Collaboration | Week 12 | Two users editing same app |
| M5: Production Ready | Week 16 | Full feature set, documentation |

## Current Status

Phase 1, Week 1: Project setup and initial implementation.
