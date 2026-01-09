//! Reactive Runtime
//!
//! The runtime is the central coordinator that connects signals, memos, and
//! effects. It manages the dependency graph and schedules updates when
//! signals change.
//!
//! # How It Works
//!
//! 1. When a signal is created, it registers with the runtime.
//!
//! 2. When a memo or effect accesses a signal, the runtime records the
//!    dependency.
//!
//! 3. When a signal's value changes, the runtime:
//!    a. Finds all dependent memos/effects
//!    b. Marks them as "maybe dirty"
//!    c. Schedules effects for execution
//!    d. Memos are lazy - they recompute on next access
//!
//! # Thread Safety
//!
//! The runtime uses thread-local storage for the reactive context and
//! a global registry for cross-thread signal access. This allows signals
//! to be shared across threads while keeping the common case fast.

use std::sync::{Arc, RwLock, Weak, OnceLock};
use std::collections::HashMap;

use super::subscriber::SubscriberId;
use super::context::ReactiveContext;

/// A trait for types that can be notified when dependencies change.
pub trait Reactive: Send + Sync {
    /// Get the subscriber ID for this reactive value.
    fn subscriber_id(&self) -> SubscriberId;

    /// Mark this reactive value as potentially needing update.
    fn mark_maybe_dirty(&self);

    /// Schedule this reactive value for execution (effects only).
    fn schedule(&self);

    /// Check if this reactive value is an effect (eager) or memo (lazy).
    fn is_eager(&self) -> bool;
}

/// Handle to a registered reactive value.
///
/// Dropping this handle unregisters the reactive value from the runtime.
pub struct ReactiveHandle {
    subscriber_id: SubscriberId,
}

impl Drop for ReactiveHandle {
    fn drop(&mut self) {
        Runtime::unregister(self.subscriber_id);
    }
}

/// The global reactive runtime.
///
/// This is a singleton that manages all reactive values in the application.
pub struct Runtime;

// Global registry of reactive values.
// Maps subscriber IDs to weak references to avoid preventing cleanup.
static REGISTRY: OnceLock<RwLock<HashMap<SubscriberId, Weak<dyn Reactive>>>> = OnceLock::new();
static SIGNAL_SUBSCRIBERS: OnceLock<RwLock<HashMap<u64, Vec<SubscriberId>>>> = OnceLock::new();

fn get_registry() -> &'static RwLock<HashMap<SubscriberId, Weak<dyn Reactive>>> {
    REGISTRY.get_or_init(|| RwLock::new(HashMap::new()))
}

fn get_signal_subscribers() -> &'static RwLock<HashMap<u64, Vec<SubscriberId>>> {
    SIGNAL_SUBSCRIBERS.get_or_init(|| RwLock::new(HashMap::new()))
}

impl Runtime {
    /// Register a reactive value with the runtime.
    ///
    /// Returns a handle that unregisters the value when dropped.
    pub fn register(reactive: Arc<dyn Reactive>) -> ReactiveHandle {
        let id = reactive.subscriber_id();
        
        get_registry()
            .write()
            .expect("registry lock poisoned")
            .insert(id, Arc::downgrade(&reactive));
        
        ReactiveHandle { subscriber_id: id }
    }

    /// Unregister a reactive value.
    fn unregister(id: SubscriberId) {
        get_registry()
            .write()
            .expect("registry lock poisoned")
            .remove(&id);
        
        // Also remove from signal subscribers
        let mut subscribers = get_signal_subscribers()
            .write()
            .expect("signal_subscribers lock poisoned");
        
        for subs in subscribers.values_mut() {
            subs.retain(|s| *s != id);
        }
    }

    /// Record that a subscriber depends on a signal.
    ///
    /// Called automatically when a signal is read within a reactive context.
    pub fn add_dependency(signal_id: u64, subscriber_id: SubscriberId) {
        get_signal_subscribers()
            .write()
            .expect("signal_subscribers lock poisoned")
            .entry(signal_id)
            .or_insert_with(Vec::new)
            .push(subscriber_id);
    }

    /// Remove all dependencies for a subscriber.
    ///
    /// Called before re-running a computation to clear stale dependencies.
    pub fn clear_dependencies(subscriber_id: SubscriberId) {
        let mut subscribers = get_signal_subscribers()
            .write()
            .expect("signal_subscribers lock poisoned");
        
        for subs in subscribers.values_mut() {
            subs.retain(|s| *s != subscriber_id);
        }
    }

    /// Notify all subscribers that a signal changed.
    ///
    /// This is the core update propagation mechanism.
    pub fn notify_signal_change(signal_id: u64) {
        // Get subscribers for this signal
        let subscriber_ids = {
            let subscribers = get_signal_subscribers()
                .read()
                .expect("signal_subscribers lock poisoned");
            
            subscribers
                .get(&signal_id)
                .cloned()
                .unwrap_or_default()
        };

        if subscriber_ids.is_empty() {
            return;
        }

        // Get the actual reactive values
        let registry = get_registry()
            .read()
            .expect("registry lock poisoned");

        let mut effects_to_run = Vec::new();

        for sub_id in subscriber_ids {
            if let Some(weak) = registry.get(&sub_id) {
                if let Some(reactive) = weak.upgrade() {
                    // Mark as maybe dirty
                    reactive.mark_maybe_dirty();
                    
                    // If it's an eager reactive (effect), schedule it
                    if reactive.is_eager() {
                        effects_to_run.push(reactive);
                    }
                }
            }
        }

        // Release the registry lock before running effects
        drop(registry);

        // Run scheduled effects
        for effect in effects_to_run {
            effect.schedule();
        }
    }

    /// Get the current subscriber being tracked, if any.
    pub fn current_subscriber() -> Option<SubscriberId> {
        ReactiveContext::current_subscriber()
    }

    /// Check if we're inside a reactive context.
    pub fn is_tracking() -> bool {
        ReactiveContext::is_active()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicI32, AtomicBool, Ordering};

    struct MockReactive {
        id: SubscriberId,
        dirty: AtomicBool,
        scheduled: AtomicI32,
        eager: bool,
    }

    impl MockReactive {
        fn new(eager: bool) -> Arc<Self> {
            Arc::new(Self {
                id: SubscriberId::new(),
                dirty: AtomicBool::new(false),
                scheduled: AtomicI32::new(0),
                eager,
            })
        }
    }

    impl Reactive for MockReactive {
        fn subscriber_id(&self) -> SubscriberId {
            self.id
        }

        fn mark_maybe_dirty(&self) {
            self.dirty.store(true, Ordering::SeqCst);
        }

        fn schedule(&self) {
            self.scheduled.fetch_add(1, Ordering::SeqCst);
        }

        fn is_eager(&self) -> bool {
            self.eager
        }
    }

    #[test]
    fn runtime_registers_and_unregisters() {
        let reactive = MockReactive::new(false);
        let id = reactive.id;
        
        let handle = Runtime::register(reactive);
        
        // Should be registered
        assert!(get_registry().read().unwrap().contains_key(&id));
        
        // Drop handle
        drop(handle);
        
        // Should be unregistered
        assert!(!get_registry().read().unwrap().contains_key(&id));
    }

    #[test]
    fn runtime_notifies_subscribers() {
        let memo = MockReactive::new(false);
        let effect = MockReactive::new(true);
        
        let memo_id = memo.id;
        let effect_id = effect.id;
        
        let _memo_handle = Runtime::register(memo.clone());
        let _effect_handle = Runtime::register(effect.clone());
        
        // Add dependencies
        Runtime::add_dependency(42, memo_id);
        Runtime::add_dependency(42, effect_id);
        
        // Notify change
        Runtime::notify_signal_change(42);
        
        // Both should be marked dirty
        assert!(memo.dirty.load(Ordering::SeqCst));
        assert!(effect.dirty.load(Ordering::SeqCst));
        
        // Only effect should be scheduled (it's eager)
        assert_eq!(memo.scheduled.load(Ordering::SeqCst), 0);
        assert_eq!(effect.scheduled.load(Ordering::SeqCst), 1);
    }

    #[test]
    fn runtime_clears_dependencies() {
        let reactive = MockReactive::new(false);
        let id = reactive.id;
        
        let _handle = Runtime::register(reactive.clone());
        
        // Add dependency
        Runtime::add_dependency(100, id);
        
        // Verify it exists
        {
            let subs = get_signal_subscribers().read().unwrap();
            assert!(subs.get(&100).map(|v| v.contains(&id)).unwrap_or(false));
        }
        
        // Clear
        Runtime::clear_dependencies(id);
        
        // Verify it's gone
        {
            let subs = get_signal_subscribers().read().unwrap();
            assert!(!subs.get(&100).map(|v| v.contains(&id)).unwrap_or(false));
        }
    }
}
