//! Dependency Graph
//!
//! This module implements the computational dependency graph that tracks
//! relationships between reactive values and computations.
//!
//! # Overview
//!
//! The dependency graph is a directed acyclic graph (DAG) where:
//!
//! - Nodes represent reactive values (signals) or computations (memos, effects)
//! - Edges represent dependencies: if A depends on B, there is an edge from B to A
//!
//! When a signal changes, we traverse the graph to find all affected nodes
//! and mark them as dirty. The incremental computation engine then determines
//! which dirty nodes actually need to recompute.
//!
//! # Design Decisions
//!
//! 1. We use a centralized graph rather than distributed linked lists because:
//!    - It enables efficient topological ordering for batch updates
//!    - It simplifies cycle detection
//!    - It allows for global optimization of update scheduling
//!
//! 2. The graph is indexed by node ID for O(1) lookups.
//!
//! 3. We maintain both forward (dependencies) and reverse (dependents) edges
//!    to enable efficient traversal in both directions.

mod node;
mod scheduler;

pub use node::{Node, NodeId, NodeKind};
pub use scheduler::UpdateScheduler;
