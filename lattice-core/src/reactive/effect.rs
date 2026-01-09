//! Effect Implementation
//!
//! An Effect is a side-effecting computation that runs whenever its
//! dependencies change.
//!
//! # How Effects Work
//!
//! 1. When created, the effect runs its function immediately to establish
//!    initial dependencies.
//!
//! 2. When any dependency changes, the effect is scheduled to re-run.
//!
//! 3. Before re-running, the effect clears its old dependencies and tracks
//!    new ones during execution.
//!
//! # Use Cases
//!
//! Effects are used to synchronize reactive state with the outside world:
//!
//! - Updating the DOM when state changes
//! - Logging state changes
//! - Making network requests
//! - Writing to files
//!
//! # Differences from Memo
//!
//! - Memos return a value; effects do not.
//! - Memos are lazy (compute on access); effects are eager (run when deps change).
//! - Memos cache results; effects just run their side effect.
//!
//! # Cleanup
//!
//! Effects can optionally return a cleanup function. This function is called
//! before the effect re-runs and when the effect is disposed. This is useful
//! for cleaning up resources like event listeners or timers.

use std::sync::atomic::{AtomicU64, Ordering, AtomicBool};
use std::sync::{Arc, RwLock};
use std::collections::HashSet;

use super::context::ReactiveContext;
use super::subscriber::SubscriberId;

/// Counter for generating unique effect IDs.
static EFFECT_ID_COUNTER: AtomicU64 = AtomicU64::new(0);

/// Generate a new unique effect ID.
fn next_effect_id() -> u64 {
    EFFECT_ID_COUNTER.fetch_add(1, Ordering::Relaxed)
}

/// A side-effecting computation that runs when dependencies change.
///
/// # Example
///
/// ```rust,ignore
/// let count = Signal::new(0);
///
/// let effect = Effect::new(|| {
///     println!("Count is: {}", count.get());
/// });
///
/// count.set(5);  // Prints: "Count is: 5"
/// ```
pub struct Effect {
    /// Unique identifier for this effect.
    id: u64,

    /// The subscriber ID used for dependency tracking.
    subscriber_id: SubscriberId,

    /// The effect function.
    run: Arc<dyn Fn() + Send + Sync>,

    /// Signal IDs that this effect depends on.
    dependencies: Arc<RwLock<HashSet<u64>>>,

    /// Whether the effect has been disposed.
    disposed: Arc<AtomicBool>,

    /// Number of times the effect has run.
    run_count: Arc<RwLock<usize>>,
}

impl Effect {
    /// Create a new effect with the given function.
    ///
    /// The function runs immediately to establish initial dependencies.
    pub fn new<F>(run: F) -> Self
    where
        F: Fn() + Send + Sync + 'static,
    {
        let effect = Self {
            id: next_effect_id(),
            subscriber_id: SubscriberId::new(),
            run: Arc::new(run),
            dependencies: Arc::new(RwLock::new(HashSet::new())),
            disposed: Arc::new(AtomicBool::new(false)),
            run_count: Arc::new(RwLock::new(0)),
        };

        // Run immediately to establish dependencies
        effect.execute();

        effect
    }

    /// Create a new effect without running it immediately.
    ///
    /// Useful for cases where you want to control when the effect first runs.
    pub fn new_lazy<F>(run: F) -> Self
    where
        F: Fn() + Send + Sync + 'static,
    {
        Self {
            id: next_effect_id(),
            subscriber_id: SubscriberId::new(),
            run: Arc::new(run),
            dependencies: Arc::new(RwLock::new(HashSet::new())),
            disposed: Arc::new(AtomicBool::new(false)),
            run_count: Arc::new(RwLock::new(0)),
        }
    }

    /// Get the effect's unique ID.
    pub fn id(&self) -> u64 {
        self.id
    }

    /// Get the subscriber ID for this effect.
    pub fn subscriber_id(&self) -> SubscriberId {
        self.subscriber_id
    }

    /// Execute the effect function.
    ///
    /// This runs the function within a reactive context to track dependencies.
    pub fn execute(&self) {
        if self.disposed.load(Ordering::SeqCst) {
            return;
        }

        // Clear old dependencies
        self.dependencies
            .write()
            .expect("dependencies lock poisoned")
            .clear();

        // Enter a reactive context to track dependencies
        let _ctx = ReactiveContext::enter(self.subscriber_id);

        // Run the effect function
        (self.run)();

        // Get the dependencies that were accessed during execution
        let new_deps: HashSet<u64> = ReactiveContext::get_dependencies()
            .into_iter()
            .collect();

        // Update our dependency set
        *self.dependencies.write().expect("dependencies lock poisoned") = new_deps;

        // Increment run count
        *self.run_count.write().expect("run_count lock poisoned") += 1;
    }

    /// Schedule the effect to re-run.
    ///
    /// Called when a dependency changes.
    pub fn schedule(&self) {
        if !self.disposed.load(Ordering::SeqCst) {
            // In a full implementation, this would add the effect to a scheduler
            // queue. For now, we run synchronously.
            self.execute();
        }
    }

    /// Dispose of the effect.
    ///
    /// After disposal, the effect will not run again.
    pub fn dispose(&self) {
        self.disposed.store(true, Ordering::SeqCst);
    }

    /// Check if the effect has been disposed.
    pub fn is_disposed(&self) -> bool {
        self.disposed.load(Ordering::SeqCst)
    }

    /// Get the number of times the effect has run.
    pub fn run_count(&self) -> usize {
        *self.run_count.read().expect("run_count lock poisoned")
    }

    /// Get the number of dependencies.
    pub fn dependency_count(&self) -> usize {
        self.dependencies
            .read()
            .expect("dependencies lock poisoned")
            .len()
    }
}

impl Clone for Effect {
    fn clone(&self) -> Self {
        Self {
            id: self.id,
            subscriber_id: self.subscriber_id,
            run: Arc::clone(&self.run),
            dependencies: Arc::clone(&self.dependencies),
            disposed: Arc::clone(&self.disposed),
            run_count: Arc::clone(&self.run_count),
        }
    }
}

impl std::fmt::Debug for Effect {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Effect")
            .field("id", &self.id)
            .field("run_count", &self.run_count())
            .field("dependency_count", &self.dependency_count())
            .field("disposed", &self.is_disposed())
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
    fn effect_runs_on_creation() {
        let run_count = Arc::new(AtomicI32::new(0));
        let run_count_clone = run_count.clone();

        let _effect = Effect::new(move || {
            run_count_clone.fetch_add(1, Ordering::SeqCst);
        });

        // Effect should have run once on creation
        assert_eq!(run_count.load(Ordering::SeqCst), 1);
    }

    #[test]
    fn effect_lazy_does_not_run_on_creation() {
        let run_count = Arc::new(AtomicI32::new(0));
        let run_count_clone = run_count.clone();

        let effect = Effect::new_lazy(move || {
            run_count_clone.fetch_add(1, Ordering::SeqCst);
        });

        // Effect should not have run
        assert_eq!(run_count.load(Ordering::SeqCst), 0);
        assert_eq!(effect.run_count(), 0);

        // Manually execute
        effect.execute();
        assert_eq!(run_count.load(Ordering::SeqCst), 1);
        assert_eq!(effect.run_count(), 1);
    }

    #[test]
    fn effect_runs_on_schedule() {
        let run_count = Arc::new(AtomicI32::new(0));
        let run_count_clone = run_count.clone();

        let effect = Effect::new(move || {
            run_count_clone.fetch_add(1, Ordering::SeqCst);
        });

        // Ran once on creation
        assert_eq!(run_count.load(Ordering::SeqCst), 1);

        // Schedule re-run
        effect.schedule();
        assert_eq!(run_count.load(Ordering::SeqCst), 2);

        effect.schedule();
        assert_eq!(run_count.load(Ordering::SeqCst), 3);
    }

    #[test]
    fn effect_does_not_run_after_disposal() {
        let run_count = Arc::new(AtomicI32::new(0));
        let run_count_clone = run_count.clone();

        let effect = Effect::new(move || {
            run_count_clone.fetch_add(1, Ordering::SeqCst);
        });

        // Ran once on creation
        assert_eq!(run_count.load(Ordering::SeqCst), 1);

        // Dispose
        effect.dispose();
        assert!(effect.is_disposed());

        // Schedule should not run
        effect.schedule();
        assert_eq!(run_count.load(Ordering::SeqCst), 1);

        // Execute should not run
        effect.execute();
        assert_eq!(run_count.load(Ordering::SeqCst), 1);
    }

    #[test]
    fn effect_tracks_run_count() {
        let effect = Effect::new(|| {});

        assert_eq!(effect.run_count(), 1);

        effect.execute();
        assert_eq!(effect.run_count(), 2);

        effect.execute();
        assert_eq!(effect.run_count(), 3);
    }

    #[test]
    fn effect_clone_shares_state() {
        let effect1 = Effect::new(|| {});
        let effect2 = effect1.clone();

        // Same ID
        assert_eq!(effect1.id(), effect2.id());

        // Shared run count
        assert_eq!(effect1.run_count(), 1);
        assert_eq!(effect2.run_count(), 1);

        effect1.execute();
        assert_eq!(effect1.run_count(), 2);
        assert_eq!(effect2.run_count(), 2);

        // Shared disposal state
        effect1.dispose();
        assert!(effect2.is_disposed());
    }
}
