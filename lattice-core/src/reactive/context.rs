//! Reactive Context
//!
//! The reactive context tracks which computation is currently running.
//! This enables automatic dependency tracking: when a signal is read,
//! we can register the current computation as a dependent.
//!
//! # Implementation
//!
//! We use a thread-local stack to track the currently executing computation.
//! When entering a reactive context (e.g., running a memo or effect), we push
//! the subscriber onto the stack. When the computation completes, we pop it.
//!
//! This design supports nested reactive contexts (e.g., a memo that reads
//! from another memo).

use std::cell::RefCell;
use super::SubscriberId;

/// The reactive context stack.
///
/// Each thread has its own stack to track which computation is running.
/// This thread-local approach avoids the need for synchronization in the
/// common case of single-threaded reactivity.
thread_local! {
    static CONTEXT_STACK: RefCell<Vec<ContextEntry>> = RefCell::new(Vec::new());
}

/// An entry in the reactive context stack.
///
/// Contains information about the currently executing computation.
#[derive(Debug, Clone)]
struct ContextEntry {
    /// The subscriber ID of the current computation.
    subscriber_id: SubscriberId,
    /// Dependencies collected during this computation.
    /// These are the signal IDs that were read.
    dependencies: Vec<u64>,
}

/// Guard that pops the context when dropped.
///
/// This ensures the context stack is properly maintained even if
/// the computation panics.
pub struct ReactiveContext {
    subscriber_id: SubscriberId,
}

impl ReactiveContext {
    /// Enter a new reactive context for the given subscriber.
    ///
    /// While this context is active, any signals that are read will
    /// register the subscriber as a dependent.
    ///
    /// The context is automatically exited when the returned guard is dropped.
    pub fn enter(subscriber_id: SubscriberId) -> Self {
        CONTEXT_STACK.with(|stack| {
            stack.borrow_mut().push(ContextEntry {
                subscriber_id,
                dependencies: Vec::new(),
            });
        });

        Self { subscriber_id }
    }

    /// Check if there is an active reactive context.
    pub fn is_active() -> bool {
        CONTEXT_STACK.with(|stack| !stack.borrow().is_empty())
    }

    /// Get the current subscriber ID, if any.
    pub fn current_subscriber() -> Option<SubscriberId> {
        CONTEXT_STACK.with(|stack| {
            stack.borrow().last().map(|entry| entry.subscriber_id)
        })
    }

    /// Record a dependency on the given signal.
    ///
    /// This is called by signals when they are read.
    pub fn track_dependency(signal_id: u64) {
        CONTEXT_STACK.with(|stack| {
            if let Some(entry) = stack.borrow_mut().last_mut() {
                entry.dependencies.push(signal_id);
            }
        });
    }

    /// Get the dependencies collected in the current context.
    pub fn get_dependencies() -> Vec<u64> {
        CONTEXT_STACK.with(|stack| {
            stack
                .borrow()
                .last()
                .map(|entry| entry.dependencies.clone())
                .unwrap_or_default()
        })
    }
}

impl Drop for ReactiveContext {
    fn drop(&mut self) {
        CONTEXT_STACK.with(|stack| {
            let popped = stack.borrow_mut().pop();
            
            // Verify we're popping the right context.
            // This helps catch bugs where contexts are mismatched.
            if let Some(entry) = popped {
                debug_assert_eq!(
                    entry.subscriber_id, self.subscriber_id,
                    "ReactiveContext mismatch: expected {:?}, got {:?}",
                    self.subscriber_id, entry.subscriber_id
                );
            }
        });
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn context_tracks_subscriber() {
        let id = SubscriberId::new();
        
        assert!(!ReactiveContext::is_active());
        assert!(ReactiveContext::current_subscriber().is_none());

        {
            let _ctx = ReactiveContext::enter(id);
            
            assert!(ReactiveContext::is_active());
            assert_eq!(ReactiveContext::current_subscriber(), Some(id));
        }

        // Context should be cleaned up after drop
        assert!(!ReactiveContext::is_active());
        assert!(ReactiveContext::current_subscriber().is_none());
    }

    #[test]
    fn context_tracks_dependencies() {
        let id = SubscriberId::new();
        let _ctx = ReactiveContext::enter(id);

        ReactiveContext::track_dependency(1);
        ReactiveContext::track_dependency(2);
        ReactiveContext::track_dependency(3);

        let deps = ReactiveContext::get_dependencies();
        assert_eq!(deps, vec![1, 2, 3]);
    }

    #[test]
    fn nested_contexts() {
        let id1 = SubscriberId::new();
        let id2 = SubscriberId::new();

        {
            let _ctx1 = ReactiveContext::enter(id1);
            assert_eq!(ReactiveContext::current_subscriber(), Some(id1));

            {
                let _ctx2 = ReactiveContext::enter(id2);
                assert_eq!(ReactiveContext::current_subscriber(), Some(id2));
            }

            // After inner context drops, outer should be current
            assert_eq!(ReactiveContext::current_subscriber(), Some(id1));
        }

        assert!(ReactiveContext::current_subscriber().is_none());
    }
}
