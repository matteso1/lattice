//! Graph Nodes
//!
//! This module defines the node types that live in the dependency graph.

use std::sync::atomic::{AtomicU64, Ordering};
use std::collections::HashSet;

/// Unique identifier for a node in the dependency graph.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct NodeId(u64);

impl NodeId {
    /// Generate a new unique node ID.
    pub fn new() -> Self {
        static COUNTER: AtomicU64 = AtomicU64::new(0);
        Self(COUNTER.fetch_add(1, Ordering::Relaxed))
    }

    /// Get the raw ID value.
    pub fn raw(&self) -> u64 {
        self.0
    }
}

impl Default for NodeId {
    fn default() -> Self {
        Self::new()
    }
}

impl From<u64> for NodeId {
    fn from(id: u64) -> Self {
        Self(id)
    }
}

/// The kind of node in the dependency graph.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum NodeKind {
    /// A source node (signal). These are the roots of the graph.
    /// They have no dependencies, only dependents.
    Source,

    /// A derived node (memo). These have dependencies and may have dependents.
    /// They cache their computed value.
    Derived,

    /// An effect node. These are leaves of the graph.
    /// They have dependencies but no dependents (they produce side effects, not values).
    Effect,
}

/// Dirty state of a node.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DirtyState {
    /// The node's value is up-to-date.
    Clean,

    /// The node might need to recompute. One of its dependencies changed,
    /// but we have not yet verified if the actual input values are different.
    MaybeDirty,

    /// The node definitely needs to recompute. Its inputs have changed.
    Dirty,
}

/// A node in the dependency graph.
#[derive(Debug)]
pub struct Node {
    /// Unique identifier for this node.
    id: NodeId,

    /// What kind of node this is.
    kind: NodeKind,

    /// Current dirty state.
    dirty: DirtyState,

    /// Nodes that this node depends on (parents in the DAG).
    /// For a memo, these are the signals/memos it reads from.
    dependencies: HashSet<NodeId>,

    /// Nodes that depend on this node (children in the DAG).
    /// For a signal, these are the memos/effects that read from it.
    dependents: HashSet<NodeId>,
}

impl Node {
    /// Create a new node with the given kind.
    pub fn new(kind: NodeKind) -> Self {
        Self {
            id: NodeId::new(),
            kind,
            dirty: match kind {
                NodeKind::Source => DirtyState::Clean,
                NodeKind::Derived => DirtyState::Dirty, // Start dirty to ensure first computation
                NodeKind::Effect => DirtyState::Dirty,
            },
            dependencies: HashSet::new(),
            dependents: HashSet::new(),
        }
    }

    /// Create a new source (signal) node.
    pub fn source() -> Self {
        Self::new(NodeKind::Source)
    }

    /// Create a new derived (memo) node.
    pub fn derived() -> Self {
        Self::new(NodeKind::Derived)
    }

    /// Create a new effect node.
    pub fn effect() -> Self {
        Self::new(NodeKind::Effect)
    }

    /// Get the node's ID.
    pub fn id(&self) -> NodeId {
        self.id
    }

    /// Get the node's kind.
    pub fn kind(&self) -> NodeKind {
        self.kind
    }

    /// Get the current dirty state.
    pub fn dirty_state(&self) -> DirtyState {
        self.dirty
    }

    /// Check if the node needs any processing.
    pub fn is_clean(&self) -> bool {
        self.dirty == DirtyState::Clean
    }

    /// Mark the node as clean.
    pub fn mark_clean(&mut self) {
        self.dirty = DirtyState::Clean;
    }

    /// Mark the node as maybe dirty (a dependency might have changed).
    pub fn mark_maybe_dirty(&mut self) {
        if self.dirty == DirtyState::Clean {
            self.dirty = DirtyState::MaybeDirty;
        }
    }

    /// Mark the node as definitely dirty (needs recomputation).
    pub fn mark_dirty(&mut self) {
        self.dirty = DirtyState::Dirty;
    }

    /// Add a dependency (a node that this node reads from).
    pub fn add_dependency(&mut self, node_id: NodeId) {
        self.dependencies.insert(node_id);
    }

    /// Remove a dependency.
    pub fn remove_dependency(&mut self, node_id: NodeId) {
        self.dependencies.remove(&node_id);
    }

    /// Get all dependencies.
    pub fn dependencies(&self) -> &HashSet<NodeId> {
        &self.dependencies
    }

    /// Add a dependent (a node that reads from this node).
    pub fn add_dependent(&mut self, node_id: NodeId) {
        self.dependents.insert(node_id);
    }

    /// Remove a dependent.
    pub fn remove_dependent(&mut self, node_id: NodeId) {
        self.dependents.remove(&node_id);
    }

    /// Get all dependents.
    pub fn dependents(&self) -> &HashSet<NodeId> {
        &self.dependents
    }

    /// Clear all dependencies.
    pub fn clear_dependencies(&mut self) {
        self.dependencies.clear();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn node_ids_are_unique() {
        let id1 = NodeId::new();
        let id2 = NodeId::new();
        assert_ne!(id1, id2);
    }

    #[test]
    fn source_node_starts_clean() {
        let node = Node::source();
        assert_eq!(node.kind(), NodeKind::Source);
        assert!(node.is_clean());
    }

    #[test]
    fn derived_node_starts_dirty() {
        let node = Node::derived();
        assert_eq!(node.kind(), NodeKind::Derived);
        assert_eq!(node.dirty_state(), DirtyState::Dirty);
    }

    #[test]
    fn dependency_management() {
        let mut node = Node::derived();
        let dep1 = NodeId::new();
        let dep2 = NodeId::new();

        node.add_dependency(dep1);
        node.add_dependency(dep2);

        assert!(node.dependencies().contains(&dep1));
        assert!(node.dependencies().contains(&dep2));
        assert_eq!(node.dependencies().len(), 2);

        node.remove_dependency(dep1);
        assert!(!node.dependencies().contains(&dep1));
        assert_eq!(node.dependencies().len(), 1);
    }

    #[test]
    fn dirty_state_transitions() {
        let mut node = Node::derived();

        // Start dirty
        assert_eq!(node.dirty_state(), DirtyState::Dirty);

        // Mark clean
        node.mark_clean();
        assert_eq!(node.dirty_state(), DirtyState::Clean);

        // Mark maybe dirty
        node.mark_maybe_dirty();
        assert_eq!(node.dirty_state(), DirtyState::MaybeDirty);

        // Mark dirty
        node.mark_dirty();
        assert_eq!(node.dirty_state(), DirtyState::Dirty);
    }
}
