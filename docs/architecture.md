# Lattice Architecture

This document describes the technical architecture of Lattice, a reactive Python framework with a Rust-powered core.

## System Overview

```mermaid
flowchart TB
    subgraph User["User Code"]
        APP["Python Application"]
    end
    
    subgraph Python["Python Layer"]
        API["Public API<br/>signal, memo, effect"]
        CTX["ReactiveContext<br/>Thread-local tracking"]
        WRAP["Type Wrappers<br/>Signal, Memo, Effect"]
    end
    
    subgraph Rust["Rust Core (PyO3)"]
        SIG["Signal Runtime<br/>Mutable state, notifications"]
        RT["Runtime<br/>Global registry, scheduling"]
        GRAPH["Dependency Graph<br/>Topological ordering"]
    end
    
    subgraph Future["Future Components"]
        RENDER["Rendering Pipeline"]
        TRANSPORT["WebSocket Transport"]
        CRDT["CRDT Collaboration"]
    end
    
    APP --> API
    API --> CTX
    CTX --> WRAP
    WRAP --> SIG
    SIG --> RT
    RT --> GRAPH
    
    GRAPH -.-> RENDER
    RENDER -.-> TRANSPORT
    TRANSPORT -.-> CRDT
```

## Core Components

### 1. Reactive Primitives

The foundation of Lattice is three reactive primitives:

```mermaid
flowchart LR
    subgraph Primitives
        S["Signal<br/>Mutable state"]
        M["Memo<br/>Cached derived value"]
        E["Effect<br/>Side effect"]
    end
    
    S -->|"notifies"| M
    S -->|"notifies"| E
    M -->|"notifies"| E
```

| Primitive | Purpose | Evaluation | Thread-Safe |
| --------- | ------- | ---------- | ----------- |
| Signal | Hold mutable state | Immediate | Yes |
| Memo | Cache derived values | Lazy (on access) | Yes |
| Effect | Run side effects | Eager (on change) | Yes |

### 2. Dependency Tracking

Dependencies are tracked automatically using a context stack:

```mermaid
sequenceDiagram
    participant User
    participant Effect
    participant Context
    participant Signal
    
    User->>Effect: Create effect
    Effect->>Context: Push context
    Effect->>Signal: Read value
    Signal->>Context: Register dependency
    Effect->>Context: Pop context
    
    Note over Effect,Signal: Dependency established
    
    User->>Signal: Set new value
    Signal->>Effect: Notify change
    Effect->>Effect: Re-run
```

**Implementation:**

- Thread-local stack (`_ReactiveContext`)
- Each memo/effect pushes itself onto the stack
- Signal reads check the stack and register dependencies
- On pop, memo/effect subscribes to all tracked signals

### 3. Update Propagation

When a signal changes, updates propagate through the graph:

```mermaid
flowchart TD
    subgraph "1. Signal Changes"
        S[Signal A]
    end
    
    subgraph "2. Mark Phase"
        M1[Memo X<br/>mark dirty]
        M2[Memo Y<br/>mark dirty]
        E1[Effect 1<br/>schedule]
    end
    
    subgraph "3. Execute Phase"
        RUN[Run scheduled effects]
    end
    
    S --> M1
    S --> M2
    S --> E1
    M1 --> RUN
    M2 --> RUN
    E1 --> RUN
```

**Key behaviors:**

- Memos are lazy: marked dirty but not recomputed until accessed
- Effects are eager: scheduled and run immediately
- Diamond dependencies: handled correctly (each node runs once)

### 4. Runtime Registry

The global runtime tracks all reactive values:

```mermaid
flowchart LR
    subgraph Runtime
        REG[Registry<br/>SubscriberId -> Reactive]
        DEPS[Dependencies<br/>SignalId -> Subscribers]
    end
    
    subgraph Operations
        ADD[Register]
        REM[Unregister]
        NOTIFY[Notify Change]
    end
    
    ADD --> REG
    REM --> REG
    NOTIFY --> DEPS
    DEPS --> REG
```

**Data structures:**

- `OnceLock<RwLock<HashMap>>` for thread-safe lazy initialization
- Weak references to avoid preventing cleanup
- Automatic cleanup on handle drop

## Data Flow

### Read Path

```mermaid
flowchart LR
    A[User reads signal.value] --> B{Active context?}
    B -->|Yes| C[Track dependency]
    B -->|No| D[Return value]
    C --> D
```

### Write Path

```mermaid
flowchart LR
    A[User sets signal.value] --> B[Update value]
    B --> C[Notify local subscribers]
    C --> D[Notify runtime]
    D --> E[Mark memos dirty]
    E --> F[Schedule effects]
    F --> G[Run effects]
```

## File Structure

```
lattice-core/
    src/
        lib.rs              # PyO3 module entry
        reactive/
            mod.rs          # Module exports
            signal.rs       # Signal<T> and PySignal
            memo.rs         # Memo<T> with caching
            effect.rs       # Effect with scheduling
            context.rs      # ReactiveContext stack
            runtime.rs      # Global registry
            subscriber.rs   # SubscriberId type
        graph/
            mod.rs          # Graph module
            node.rs         # Node types
            scheduler.rs    # Update scheduler
    python/
        lattice/
            __init__.py     # Python API
```

## Performance Characteristics

| Operation | Complexity | Notes |
| --------- | ---------- | ----- |
| Signal read | O(1) | Hash lookup for context check |
| Signal write | O(k) | k = number of direct dependents |
| Memo compute | O(1) + f(n) | f(n) = user computation time |
| Effect run | O(1) + f(n) | f(n) = user function time |
| Update propagation | O(delta) | Only touched nodes, not full graph |

## Thread Safety

All primitives are thread-safe:

- `Signal`: `Arc<RwLock<T>>` for value storage
- `Memo`: `Arc<RwLock>` for cache and state
- `Effect`: `AtomicBool` for disposal flag
- `Runtime`: `OnceLock + RwLock` for global state
- `Context`: Thread-local (no sharing needed)

## Future Architecture

### Phase 2: Rendering

```mermaid
flowchart LR
    STATE[Reactive State] --> VDOM[Virtual DOM]
    VDOM --> DIFF[Diff Engine]
    DIFF --> PATCH[UI Patches]
    PATCH --> CLIENT[Browser Client]
```

### Phase 3: Collaboration

```mermaid
flowchart LR
    CLIENT1[Client A] --> CRDT[CRDT Layer]
    CLIENT2[Client B] --> CRDT
    CRDT --> MERGE[Automatic Merge]
    MERGE --> SYNC[Sync to All]
```
