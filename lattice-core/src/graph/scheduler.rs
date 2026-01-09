//! Update Scheduler
//!
//! The scheduler determines the order in which dirty nodes should be updated.
//! It ensures that dependencies are always updated before their dependents.
//!
//! # Algorithm
//!
//! We use a topological sort to process nodes in dependency order:
//!
//! 1. When a source node changes, mark all its direct dependents as "maybe dirty"
//! 2. Propagate "maybe dirty" to their dependents, recursively
//! 3. Collect all maybe-dirty and dirty nodes
//! 4. Sort them topologically (dependencies before dependents)
//! 5. Process each node in order:
//!    - For "maybe dirty" nodes: check if any input actually changed
//!    - For "dirty" nodes: recompute
//!    - If output changed, mark dependents as dirty
//!
//! This "push-pull" approach minimizes unnecessary recomputation.

use std::collections::{HashMap, HashSet, VecDeque};
use super::node::{Node, NodeId, DirtyState};

/// The update scheduler manages the dependency graph and coordinates updates.
pub struct UpdateScheduler {
    /// All nodes in the graph, indexed by ID.
    nodes: HashMap<NodeId, Node>,
}

impl UpdateScheduler {
    /// Create a new empty scheduler.
    pub fn new() -> Self {
        Self {
            nodes: HashMap::new(),
        }
    }

    /// Add a node to the graph.
    pub fn add_node(&mut self, node: Node) -> NodeId {
        let id = node.id();
        self.nodes.insert(id, node);
        id
    }

    /// Remove a node from the graph.
    ///
    /// Also removes all edges involving this node.
    pub fn remove_node(&mut self, node_id: NodeId) {
        if let Some(node) = self.nodes.remove(&node_id) {
            // Remove this node from its dependencies' dependent lists
            for dep_id in node.dependencies() {
                if let Some(dep) = self.nodes.get_mut(dep_id) {
                    dep.remove_dependent(node_id);
                }
            }

            // Remove this node from its dependents' dependency lists
            for dependent_id in node.dependents() {
                if let Some(dependent) = self.nodes.get_mut(dependent_id) {
                    dependent.remove_dependency(node_id);
                }
            }
        }
    }

    /// Get a reference to a node.
    pub fn get_node(&self, node_id: NodeId) -> Option<&Node> {
        self.nodes.get(&node_id)
    }

    /// Get a mutable reference to a node.
    pub fn get_node_mut(&mut self, node_id: NodeId) -> Option<&mut Node> {
        self.nodes.get_mut(&node_id)
    }

    /// Add a dependency edge: `dependent` depends on `dependency`.
    ///
    /// This means when `dependency` changes, `dependent` may need to update.
    pub fn add_edge(&mut self, dependency: NodeId, dependent: NodeId) {
        if let Some(dep_node) = self.nodes.get_mut(&dependency) {
            dep_node.add_dependent(dependent);
        }
        if let Some(dependent_node) = self.nodes.get_mut(&dependent) {
            dependent_node.add_dependency(dependency);
        }
    }

    /// Remove a dependency edge.
    pub fn remove_edge(&mut self, dependency: NodeId, dependent: NodeId) {
        if let Some(dep_node) = self.nodes.get_mut(&dependency) {
            dep_node.remove_dependent(dependent);
        }
        if let Some(dependent_node) = self.nodes.get_mut(&dependent) {
            dependent_node.remove_dependency(dependency);
        }
    }

    /// Mark a source node as changed and propagate dirty flags.
    ///
    /// Returns the set of node IDs that need to be processed.
    pub fn mark_changed(&mut self, source_id: NodeId) -> Vec<NodeId> {
        let mut to_process = Vec::new();
        let mut visited = HashSet::new();
        let mut queue = VecDeque::new();

        // Start with the source node's direct dependents
        if let Some(source) = self.nodes.get(&source_id) {
            for dependent_id in source.dependents() {
                queue.push_back(*dependent_id);
            }
        }

        // BFS to propagate maybe-dirty status
        while let Some(node_id) = queue.pop_front() {
            if visited.contains(&node_id) {
                continue;
            }
            visited.insert(node_id);

            if let Some(node) = self.nodes.get_mut(&node_id) {
                // Mark as maybe dirty (or dirty if already maybe dirty)
                if node.is_clean() {
                    node.mark_maybe_dirty();
                }
                to_process.push(node_id);

                // Propagate to dependents
                for dependent_id in node.dependents().clone() {
                    queue.push_back(dependent_id);
                }
            }
        }

        // Sort topologically so dependencies are processed first
        self.topological_sort(to_process)
    }

    /// Perform a topological sort of the given nodes.
    ///
    /// Returns nodes in order such that dependencies come before dependents.
    fn topological_sort(&self, nodes: Vec<NodeId>) -> Vec<NodeId> {
        let node_set: HashSet<_> = nodes.iter().copied().collect();
        let mut in_degree: HashMap<NodeId, usize> = HashMap::new();
        let mut result = Vec::new();
        let mut queue = VecDeque::new();

        // Calculate in-degrees (only counting edges within the node set)
        for &node_id in &nodes {
            if let Some(node) = self.nodes.get(&node_id) {
                let degree = node
                    .dependencies()
                    .iter()
                    .filter(|d| node_set.contains(d))
                    .count();
                in_degree.insert(node_id, degree);
                if degree == 0 {
                    queue.push_back(node_id);
                }
            }
        }

        // Kahn's algorithm
        while let Some(node_id) = queue.pop_front() {
            result.push(node_id);

            if let Some(node) = self.nodes.get(&node_id) {
                for &dependent_id in node.dependents() {
                    if let Some(degree) = in_degree.get_mut(&dependent_id) {
                        *degree = degree.saturating_sub(1);
                        if *degree == 0 {
                            queue.push_back(dependent_id);
                        }
                    }
                }
            }
        }

        result
    }

    /// Get the total number of nodes in the graph.
    pub fn node_count(&self) -> usize {
        self.nodes.len()
    }
}

impl Default for UpdateScheduler {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::graph::node::NodeKind;

    #[test]
    fn add_and_remove_nodes() {
        let mut scheduler = UpdateScheduler::new();

        let node1 = Node::source();
        let node2 = Node::derived();

        let id1 = scheduler.add_node(node1);
        let id2 = scheduler.add_node(node2);

        assert_eq!(scheduler.node_count(), 2);

        scheduler.remove_node(id1);
        assert_eq!(scheduler.node_count(), 1);
        assert!(scheduler.get_node(id1).is_none());
        assert!(scheduler.get_node(id2).is_some());
    }

    #[test]
    fn add_and_remove_edges() {
        let mut scheduler = UpdateScheduler::new();

        let source = Node::source();
        let derived = Node::derived();

        let source_id = scheduler.add_node(source);
        let derived_id = scheduler.add_node(derived);

        scheduler.add_edge(source_id, derived_id);

        // Check the edge exists
        assert!(scheduler
            .get_node(source_id)
            .unwrap()
            .dependents()
            .contains(&derived_id));
        assert!(scheduler
            .get_node(derived_id)
            .unwrap()
            .dependencies()
            .contains(&source_id));

        // Remove the edge
        scheduler.remove_edge(source_id, derived_id);

        assert!(!scheduler
            .get_node(source_id)
            .unwrap()
            .dependents()
            .contains(&derived_id));
        assert!(!scheduler
            .get_node(derived_id)
            .unwrap()
            .dependencies()
            .contains(&source_id));
    }

    #[test]
    fn mark_changed_propagates() {
        let mut scheduler = UpdateScheduler::new();

        // Create a chain: source -> derived1 -> derived2
        let source = Node::source();
        let derived1 = Node::derived();
        let derived2 = Node::derived();

        let source_id = scheduler.add_node(source);
        let derived1_id = scheduler.add_node(derived1);
        let derived2_id = scheduler.add_node(derived2);

        scheduler.add_edge(source_id, derived1_id);
        scheduler.add_edge(derived1_id, derived2_id);

        // Mark all as clean first
        scheduler.get_node_mut(derived1_id).unwrap().mark_clean();
        scheduler.get_node_mut(derived2_id).unwrap().mark_clean();

        // Mark source as changed
        let to_process = scheduler.mark_changed(source_id);

        // Both derived nodes should be marked
        assert_eq!(to_process.len(), 2);
        
        // They should be in topological order (derived1 before derived2)
        let pos1 = to_process.iter().position(|&id| id == derived1_id);
        let pos2 = to_process.iter().position(|&id| id == derived2_id);
        assert!(pos1 < pos2);
    }
}
