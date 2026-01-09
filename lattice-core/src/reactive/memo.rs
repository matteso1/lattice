//! Memo Implementation
//!
//! A Memo is a cached derived value that re-evaluates only when its
//! dependencies change.
//!
//! # How Memos Work
//!
//! 1. On first access, the memo runs its computation and caches the result.
//!
//! 2. When accessed again, if no dependencies have changed, returns cached value.
//!
//! 3. When a dependency changes, the memo is marked "maybe dirty".
//!
//! 4. On next access, the memo re-checks if inputs actually changed.
//!
//! 5. If inputs changed, recompute. Otherwise, mark clean and return cache.
//!
//! # Why This Matters
//!
//! This "lazy" approach avoids unnecessary recomputation:
//!
//! - A signal changes
//! - 10 memos depend on it
//! - Only the memos actually accessed will recompute
//! - Memos that are never read stay dirty (no wasted work)
//!
//! # Thread Safety
//!
//! Memos are thread-safe. The cached value and dirty state are protected
//! by locks. However, the computation function is called with the lock held,
//! so computations should be fast and not block.

use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, RwLock};
use std::collections::HashSet;
use std::fmt::Debug;

use super::context::ReactiveContext;
use super::subscriber::SubscriberId;

/// Counter for generating unique memo IDs.
static MEMO_ID_COUNTER: AtomicU64 = AtomicU64::new(0);

/// Generate a new unique memo ID.
fn next_memo_id() -> u64 {
    MEMO_ID_COUNTER.fetch_add(1, Ordering::Relaxed)
}

/// Dirty state for a memo.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MemoState {
    /// The cached value is up-to-date.
    Clean,

    /// A dependency might have changed. Need to check.
    MaybeDirty,

    /// The memo definitely needs to recompute.
    Dirty,
}

/// A cached derived value that recomputes only when dependencies change.
///
/// # Type Parameters
///
/// - `T`: The type of the computed value. Must be Clone + Send + Sync + PartialEq.
///
/// The PartialEq bound is needed to detect when the computed value actually
/// changed (some memos might return the same value even if inputs changed).
pub struct Memo<T>
where
    T: Clone + Send + Sync + PartialEq + 'static,
{
    /// Unique identifier for this memo.
    id: u64,

    /// The subscriber ID used for dependency tracking.
    subscriber_id: SubscriberId,

    /// The computation function.
    compute: Arc<dyn Fn() -> T + Send + Sync>,

    /// The cached value (None if never computed).
    value: Arc<RwLock<Option<T>>>,

    /// Current dirty state.
    state: Arc<RwLock<MemoState>>,

    /// Signal IDs that this memo depends on.
    /// Updated each time the memo recomputes.
    dependencies: Arc<RwLock<HashSet<u64>>>,

    /// Subscriber IDs that depend on this memo.
    dependents: Arc<RwLock<HashSet<SubscriberId>>>,
}

impl<T> Memo<T>
where
    T: Clone + Send + Sync + PartialEq + 'static,
{
    /// Create a new memo with the given computation function.
    ///
    /// The computation is not run immediately. It runs on first access.
    pub fn new<F>(compute: F) -> Self
    where
        F: Fn() -> T + Send + Sync + 'static,
    {
        Self {
            id: next_memo_id(),
            subscriber_id: SubscriberId::new(),
            compute: Arc::new(compute),
            value: Arc::new(RwLock::new(None)),
            state: Arc::new(RwLock::new(MemoState::Dirty)),
            dependencies: Arc::new(RwLock::new(HashSet::new())),
            dependents: Arc::new(RwLock::new(HashSet::new())),
        }
    }

    /// Get the memo's unique ID.
    pub fn id(&self) -> u64 {
        self.id
    }

    /// Get the subscriber ID for this memo.
    pub fn subscriber_id(&self) -> SubscriberId {
        self.subscriber_id
    }

    /// Get the current value, recomputing if necessary.
    ///
    /// This is the main entry point for reading a memo's value.
    pub fn get(&self) -> T {
        // If we're inside a reactive context, track this memo as a dependency
        if ReactiveContext::is_active() {
            if let Some(current_subscriber) = ReactiveContext::current_subscriber() {
                self.dependents
                    .write()
                    .expect("dependents lock poisoned")
                    .insert(current_subscriber);
            }
        }

        // Check if we need to recompute
        let state = *self.state.read().expect("state lock poisoned");

        match state {
            MemoState::Clean => {
                // Value is up-to-date, return cached
                self.value
                    .read()
                    .expect("value lock poisoned")
                    .clone()
                    .expect("clean memo should have a value")
            }
            MemoState::MaybeDirty | MemoState::Dirty => {
                // Need to recompute
                self.recompute()
            }
        }
    }

    /// Mark the memo as potentially needing recomputation.
    ///
    /// Called when a dependency changes.
    pub fn mark_maybe_dirty(&self) {
        let mut state = self.state.write().expect("state lock poisoned");
        if *state == MemoState::Clean {
            *state = MemoState::MaybeDirty;
        }
    }

    /// Mark the memo as definitely needing recomputation.
    pub fn mark_dirty(&self) {
        let mut state = self.state.write().expect("state lock poisoned");
        *state = MemoState::Dirty;
    }

    /// Recompute the memo's value.
    ///
    /// This runs the computation function within a reactive context to
    /// track dependencies.
    fn recompute(&self) -> T {
        // Enter a reactive context to track dependencies
        let _ctx = ReactiveContext::enter(self.subscriber_id);

        // Run the computation
        let new_value = (self.compute)();

        // Get the dependencies that were accessed during computation
        let new_deps: HashSet<u64> = ReactiveContext::get_dependencies()
            .into_iter()
            .collect();

        // Update our dependency set
        *self.dependencies.write().expect("dependencies lock poisoned") = new_deps;

        // Check if value actually changed
        let value_changed = {
            let current = self.value.read().expect("value lock poisoned");
            current.as_ref() != Some(&new_value)
        };

        // Update cached value
        *self.value.write().expect("value lock poisoned") = Some(new_value.clone());

        // Mark as clean
        *self.state.write().expect("state lock poisoned") = MemoState::Clean;

        // If value changed, notify dependents
        if value_changed {
            self.notify_dependents();
        }

        new_value
    }

    /// Notify all dependents that this memo's value might have changed.
    fn notify_dependents(&self) {
        // In a full implementation, this would trigger the reactive system
        // to mark dependent memos/effects as maybe-dirty
        //
        // For now, we just track the dependents.
        // The integration with the scheduler will be added next.
    }

    /// Get the current dirty state.
    pub fn state(&self) -> MemoState {
        *self.state.read().expect("state lock poisoned")
    }

    /// Get the number of dependents.
    pub fn dependent_count(&self) -> usize {
        self.dependents
            .read()
            .expect("dependents lock poisoned")
            .len()
    }

    /// Check if the memo has a cached value.
    pub fn has_value(&self) -> bool {
        self.value
            .read()
            .expect("value lock poisoned")
            .is_some()
    }
}

impl<T> Clone for Memo<T>
where
    T: Clone + Send + Sync + PartialEq + 'static,
{
    fn clone(&self) -> Self {
        Self {
            id: self.id,
            subscriber_id: self.subscriber_id,
            compute: Arc::clone(&self.compute),
            value: Arc::clone(&self.value),
            state: Arc::clone(&self.state),
            dependencies: Arc::clone(&self.dependencies),
            dependents: Arc::clone(&self.dependents),
        }
    }
}

impl<T> Debug for Memo<T>
where
    T: Clone + Send + Sync + PartialEq + Debug + 'static,
{
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Memo")
            .field("id", &self.id)
            .field("state", &self.state())
            .field("has_value", &self.has_value())
            .field("dependent_count", &self.dependent_count())
            .finish()
    }
}

// ----------------------------------------------------------------------------
// Tests
// ----------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicI32, Ordering};

    #[test]
    fn memo_computes_on_first_access() {
        let call_count = Arc::new(AtomicI32::new(0));
        let call_count_clone = call_count.clone();

        let memo = Memo::new(move || {
            call_count_clone.fetch_add(1, Ordering::SeqCst);
            42
        });

        // Not computed yet
        assert!(!memo.has_value());
        assert_eq!(call_count.load(Ordering::SeqCst), 0);

        // First access triggers computation
        let value = memo.get();
        assert_eq!(value, 42);
        assert_eq!(call_count.load(Ordering::SeqCst), 1);
        assert!(memo.has_value());
    }

    #[test]
    fn memo_caches_value_when_clean() {
        let call_count = Arc::new(AtomicI32::new(0));
        let call_count_clone = call_count.clone();

        let memo = Memo::new(move || {
            call_count_clone.fetch_add(1, Ordering::SeqCst);
            42
        });

        // First access
        assert_eq!(memo.get(), 42);
        assert_eq!(call_count.load(Ordering::SeqCst), 1);

        // Second access should use cache
        assert_eq!(memo.get(), 42);
        assert_eq!(call_count.load(Ordering::SeqCst), 1);

        // Third access should also use cache
        assert_eq!(memo.get(), 42);
        assert_eq!(call_count.load(Ordering::SeqCst), 1);
    }

    #[test]
    fn memo_recomputes_when_marked_dirty() {
        let call_count = Arc::new(AtomicI32::new(0));
        let call_count_clone = call_count.clone();

        let counter = Arc::new(AtomicI32::new(0));
        let counter_clone = counter.clone();

        let memo = Memo::new(move || {
            call_count_clone.fetch_add(1, Ordering::SeqCst);
            counter_clone.load(Ordering::SeqCst)
        });

        // First access
        assert_eq!(memo.get(), 0);
        assert_eq!(call_count.load(Ordering::SeqCst), 1);

        // Update counter and mark memo dirty
        counter.store(5, Ordering::SeqCst);
        memo.mark_dirty();

        // Next access should recompute
        assert_eq!(memo.get(), 5);
        assert_eq!(call_count.load(Ordering::SeqCst), 2);
    }

    #[test]
    fn memo_recomputes_when_maybe_dirty() {
        let call_count = Arc::new(AtomicI32::new(0));
        let call_count_clone = call_count.clone();

        let memo = Memo::new(move || {
            call_count_clone.fetch_add(1, Ordering::SeqCst);
            42
        });

        // First access
        assert_eq!(memo.get(), 42);
        assert_eq!(call_count.load(Ordering::SeqCst), 1);

        // Mark as maybe dirty
        memo.mark_maybe_dirty();

        // Next access should recompute (in full implementation, would check deps)
        assert_eq!(memo.get(), 42);
        assert_eq!(call_count.load(Ordering::SeqCst), 2);
    }

    #[test]
    fn memo_clone_shares_state() {
        let memo1 = Memo::new(|| 42);

        // Force computation
        assert_eq!(memo1.get(), 42);

        let memo2 = memo1.clone();

        // Clone should have same ID and share state
        assert_eq!(memo1.id(), memo2.id());
        assert!(memo2.has_value());
        assert_eq!(memo2.get(), 42);

        // Marking one dirty affects both
        memo1.mark_dirty();
        assert_eq!(memo2.state(), MemoState::Dirty);
    }

    #[test]
    fn memo_state_transitions() {
        let memo = Memo::new(|| 42);

        // Starts dirty
        assert_eq!(memo.state(), MemoState::Dirty);

        // After get, becomes clean
        memo.get();
        assert_eq!(memo.state(), MemoState::Clean);

        // Mark maybe dirty
        memo.mark_maybe_dirty();
        assert_eq!(memo.state(), MemoState::MaybeDirty);

        // Mark dirty overrides maybe dirty
        memo.mark_dirty();
        assert_eq!(memo.state(), MemoState::Dirty);

        // After get, becomes clean again
        memo.get();
        assert_eq!(memo.state(), MemoState::Clean);
    }
}
