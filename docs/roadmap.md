# Lattice Development Roadmap

This document outlines the development plan for Lattice across four phases.

## Timeline Overview

```mermaid
gantt
    title Lattice Development Phases
    dateFormat YYYY-MM-DD
    
    section Phase 1
    Reactive Core           :done, p1a, 2026-01-09, 7d
    Dependency Graph        :done, p1b, after p1a, 3d
    Python Bindings         :done, p1c, after p1b, 4d
    
    section Phase 2
    Component Model         :p2a, after p1c, 7d
    Virtual DOM             :p2b, after p2a, 7d
    WebSocket Transport     :p2c, after p2b, 7d
    
    section Phase 3
    CRDT Foundation         :p3a, after p2c, 7d
    Conflict Resolution     :p3b, after p3a, 7d
    Presence System         :p3c, after p3b, 7d
    
    section Phase 4
    JIT Compilation         :p4a, after p3c, 7d
    WASM Target             :p4b, after p4a, 7d
    Performance Tuning      :p4c, after p4b, 7d
```

## Phase 1: Core Runtime (CURRENT)

Build the reactive foundation.

```mermaid
flowchart TB
    subgraph Complete["Completed"]
        S[Signal Primitive]
        M[Memo Primitive]
        E[Effect Primitive]
        RT[Runtime Registry]
        CTX[Context Tracking]
        PY[Python Bindings]
    end
    
    subgraph Next["Next Steps"]
        BUILD[Build Package]
        DEMO[Demo App]
        BENCH[Benchmarks]
    end
    
    S --> RT
    M --> RT
    E --> RT
    RT --> CTX
    CTX --> PY
    PY --> BUILD
    BUILD --> DEMO
    DEMO --> BENCH
```

### Milestones

| Task | Status | Notes |
| ---- | ------ | ----- |
| Signal with auto-tracking | Done | Rust + Python wrapper |
| Memo with caching | Done | Lazy evaluation |
| Effect with scheduling | Done | Eager execution |
| Runtime registry | Done | Global dependency tracking |
| Python API | Done | Decorators and context |
| Build with maturin | In Progress | Create wheel |
| Demo application | Planned | Compare vs Streamlit |
| Benchmarks | Planned | Performance validation |

## Phase 2: Rendering and Transport

Build UI primitives and network layer.

```mermaid
flowchart LR
    subgraph Components
        COMP[Component Model]
        VDOM[Virtual DOM]
        DIFF[Diff Algorithm]
    end
    
    subgraph Transport
        WS[WebSocket Server]
        PROTO[Binary Protocol]
        PATCH[Patch Streaming]
    end
    
    subgraph Client
        JS[JavaScript Runtime]
        DOM[DOM Patcher]
    end
    
    COMP --> VDOM
    VDOM --> DIFF
    DIFF --> PATCH
    PATCH --> WS
    WS --> PROTO
    PROTO --> JS
    JS --> DOM
```

### Milestones

| Task | Status | Notes |
| ---- | ------ | ----- |
| Component decorator | Planned | Define UI components |
| Virtual DOM tree | Planned | Efficient representation |
| Diff algorithm | Planned | Minimal patch generation |
| WebSocket server | Planned | Tokio-based async |
| MessagePack protocol | Planned | Compact binary format |
| JavaScript client | Planned | Minimal DOM patcher |

## Phase 3: Collaboration Layer

Real-time multi-user support.

```mermaid
flowchart TB
    subgraph CRDT["CRDT Layer"]
        LWW[Last-Write-Wins]
        COUNTER[Counters]
        TEXT[Text (Yjs-style)]
    end
    
    subgraph Sync["Synchronization"]
        VEC[Version Vectors]
        MERGE[Auto-Merge]
        CONFLICT[Conflict Resolution]
    end
    
    subgraph Presence["Presence"]
        CURSOR[Cursor Sharing]
        AWARE[Awareness Protocol]
    end
    
    LWW --> MERGE
    COUNTER --> MERGE
    TEXT --> MERGE
    MERGE --> VEC
    VEC --> CONFLICT
    CONFLICT --> CURSOR
    CURSOR --> AWARE
```

### Milestones

| Task | Status | Notes |
| ---- | ------ | ----- |
| LWW Register CRDT | Planned | Basic conflict-free type |
| Counter CRDT | Planned | For numeric values |
| Text CRDT | Planned | Collaborative editing |
| Version vectors | Planned | Causality tracking |
| Presence system | Planned | User awareness |

## Phase 4: Performance Optimization

Advanced compilation and execution.

```mermaid
flowchart LR
    subgraph Compile["Compilation"]
        TRACE[Trace Capture]
        IR[Intermediate Rep]
        LLVM[LLVM Backend]
    end
    
    subgraph Targets["Targets"]
        NATIVE[Native Code]
        WASM[WebAssembly]
    end
    
    subgraph Optimize["Optimization"]
        INLINE[Inlining]
        BATCH[Batching]
        CACHE[Cache Warming]
    end
    
    TRACE --> IR
    IR --> LLVM
    LLVM --> NATIVE
    LLVM --> WASM
    NATIVE --> INLINE
    WASM --> BATCH
    INLINE --> CACHE
```

### Milestones

| Task | Status | Notes |
| ---- | ------ | ----- |
| Expression tracing | Planned | Capture computation graph |
| LLVM integration | Planned | JIT compilation |
| WASM compilation | Planned | Browser execution |
| Performance benchmarks | Planned | Validation suite |

## Success Metrics

| Metric | Target | Current |
| ------ | ------ | ------- |
| Update latency | < 10ms | TBD |
| Memory per signal | < 100 bytes | TBD |
| Throughput | > 100k updates/sec | TBD |
| Build size (WASM) | < 500KB | N/A |

## Getting Involved

See [CONTRIBUTING.md](../CONTRIBUTING.md) for development guidelines.

Current priority: **Phase 1 completion** - build package and create demo app.
