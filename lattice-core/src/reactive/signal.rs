//! Signal Implementation
//!
//! A Signal is the fundamental reactive primitive. It holds a value and
//! tracks which computations depend on it.
//!
//! # How Signals Work
//!
//! 1. When a signal is read within a reactive context (memo/effect), the
//!    signal registers that context as a subscriber.
//!
//! 2. When a signal's value changes, all subscribers are notified.
//!
//! 3. Notifications trigger re-execution of dependent computations.
//!
//! # Thread Safety
//!
//! Signals are designed to be thread-safe. The value is protected by a
//! RwLock, and subscriber management uses a concurrent data structure.
//!
//! # Memory Layout
//!
//! Each signal consists of:
//! - A unique ID (8 bytes)
//! - The value (size depends on type, stored behind Arc)
//! - A set of subscriber IDs (grows with number of dependents)

use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, RwLock};
use std::collections::HashSet;
use std::fmt::Debug;

use pyo3::prelude::*;
use pyo3::types::PyAny;

use super::context::ReactiveContext;
use super::runtime::Runtime;
use super::SubscriberId;

/// Counter for generating unique signal IDs.
static SIGNAL_ID_COUNTER: AtomicU64 = AtomicU64::new(0);

/// Generate a new unique signal ID.
fn next_signal_id() -> u64 {
    SIGNAL_ID_COUNTER.fetch_add(1, Ordering::Relaxed)
}

/// A reactive signal holding a value of type T.
///
/// # Type Parameters
///
/// - `T`: The type of value stored in the signal. Must be Clone + Send + Sync.
///
/// # Example
///
/// ```rust,ignore
/// let count = Signal::new(0);
/// 
/// // Read the value
/// let value = count.get();
///
/// // Update the value (notifies subscribers)
/// count.set(5);
/// ```
pub struct Signal<T>
where
    T: Clone + Send + Sync + 'static,
{
    /// Unique identifier for this signal.
    id: u64,

    /// The current value, protected by RwLock for thread safety.
    value: Arc<RwLock<T>>,

    /// Set of subscriber IDs that depend on this signal.
    /// Using RwLock<HashSet> for simplicity; could optimize with DashSet later.
    subscribers: Arc<RwLock<HashSet<SubscriberId>>>,

    /// Notification callback registry.
    /// Maps subscriber IDs to their notification callbacks.
    notifiers: Arc<RwLock<Vec<(SubscriberId, Box<dyn Fn() + Send + Sync>)>>>,
}

impl<T> Signal<T>
where
    T: Clone + Send + Sync + 'static,
{
    /// Create a new signal with the given initial value.
    pub fn new(value: T) -> Self {
        Self {
            id: next_signal_id(),
            value: Arc::new(RwLock::new(value)),
            subscribers: Arc::new(RwLock::new(HashSet::new())),
            notifiers: Arc::new(RwLock::new(Vec::new())),
        }
    }

    /// Get the signal's unique ID.
    pub fn id(&self) -> u64 {
        self.id
    }

    /// Get the current value.
    ///
    /// If called within a reactive context, this also registers the
    /// current computation as a subscriber.
    pub fn get(&self) -> T {
        // Track this signal as a dependency of the current computation
        if ReactiveContext::is_active() {
            ReactiveContext::track_dependency(self.id);

            // Register the current subscriber with both local and global tracking
            if let Some(subscriber_id) = ReactiveContext::current_subscriber() {
                // Local tracking (for signal-specific notification)
                self.subscribers
                    .write()
                    .expect("subscriber lock poisoned")
                    .insert(subscriber_id);
                
                // Global tracking (for runtime-managed updates)
                Runtime::add_dependency(self.id, subscriber_id);
            }
        }

        // Return a clone of the value
        self.value
            .read()
            .expect("value lock poisoned")
            .clone()
    }

    /// Get the current value without tracking dependencies.
    ///
    /// Use this when you need to read the value without establishing
    /// a reactive dependency.
    pub fn get_untracked(&self) -> T {
        self.value
            .read()
            .expect("value lock poisoned")
            .clone()
    }

    /// Set a new value and notify subscribers.
    ///
    /// This will trigger re-execution of all dependent computations.
    pub fn set(&self, value: T) {
        // Update the value
        {
            let mut guard = self.value.write().expect("value lock poisoned");
            *guard = value;
        }

        // Notify local subscribers
        self.notify_subscribers();
        
        // Notify the global runtime
        Runtime::notify_signal_change(self.id);
    }

    /// Update the value using a function.
    ///
    /// This is useful for updates that depend on the current value.
    pub fn update<F>(&self, f: F)
    where
        F: FnOnce(&T) -> T,
    {
        let new_value = {
            let guard = self.value.read().expect("value lock poisoned");
            f(&*guard)
        };
        self.set(new_value);
    }

    /// Register a notification callback for a subscriber.
    ///
    /// The callback will be invoked when the signal's value changes.
    pub fn subscribe<F>(&self, subscriber_id: SubscriberId, notify: F)
    where
        F: Fn() + Send + Sync + 'static,
    {
        self.subscribers
            .write()
            .expect("subscriber lock poisoned")
            .insert(subscriber_id);

        self.notifiers
            .write()
            .expect("notifiers lock poisoned")
            .push((subscriber_id, Box::new(notify)));
    }

    /// Remove a subscriber.
    pub fn unsubscribe(&self, subscriber_id: SubscriberId) {
        self.subscribers
            .write()
            .expect("subscriber lock poisoned")
            .remove(&subscriber_id);

        self.notifiers
            .write()
            .expect("notifiers lock poisoned")
            .retain(|(id, _)| *id != subscriber_id);
    }

    /// Notify all subscribers that the value has changed.
    fn notify_subscribers(&self) {
        let notifiers = self.notifiers.read().expect("notifiers lock poisoned");
        for (_, notify) in notifiers.iter() {
            notify();
        }
    }

    /// Get the number of subscribers.
    pub fn subscriber_count(&self) -> usize {
        self.subscribers
            .read()
            .expect("subscriber lock poisoned")
            .len()
    }
}

impl<T> Clone for Signal<T>
where
    T: Clone + Send + Sync + 'static,
{
    fn clone(&self) -> Self {
        Self {
            id: self.id,
            value: Arc::clone(&self.value),
            subscribers: Arc::clone(&self.subscribers),
            notifiers: Arc::clone(&self.notifiers),
        }
    }
}

impl<T> Debug for Signal<T>
where
    T: Clone + Send + Sync + Debug + 'static,
{
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Signal")
            .field("id", &self.id)
            .field("value", &self.get_untracked())
            .field("subscriber_count", &self.subscriber_count())
            .finish()
    }
}

// ----------------------------------------------------------------------------
// Python Bindings
// ----------------------------------------------------------------------------

/// Python-exposed Signal type.
///
/// This is a standalone implementation for Python that handles PyO3's
/// reference counting properly. We use Py<PyAny> which is Send+Sync safe.
#[pyclass(name = "Signal")]
pub struct PySignal {
    /// Unique identifier for this signal.
    id: u64,

    /// The current value, stored as a GIL-independent reference.
    /// Py<PyAny> is Send+Sync and can be safely shared across threads.
    value: Arc<RwLock<Py<PyAny>>>,

    /// Number of subscribers (simplified for now).
    subscriber_count: Arc<RwLock<usize>>,
}

#[pymethods]
impl PySignal {
    /// Create a new signal with the given initial value.
    #[new]
    fn new(value: PyObject) -> Self {
        Self {
            id: next_signal_id(),
            value: Arc::new(RwLock::new(value)),
            subscriber_count: Arc::new(RwLock::new(0)),
        }
    }

    /// Get the current value.
    #[getter]
    fn value(&self, py: Python<'_>) -> PyObject {
        let guard = self.value.read().expect("value lock poisoned");
        guard.clone_ref(py).into()
    }

    /// Set a new value.
    #[setter]
    fn set_value(&self, value: PyObject) {
        let mut guard = self.value.write().expect("value lock poisoned");
        *guard = value;
    }

    /// Get the signal's unique ID.
    #[getter]
    fn id(&self) -> u64 {
        self.id
    }

    /// Get the number of subscribers.
    fn subscriber_count(&self) -> usize {
        *self.subscriber_count.read().expect("subscriber_count lock poisoned")
    }

    fn __repr__(&self, py: Python<'_>) -> String {
        let value = self.value.read().expect("value lock poisoned");
        let repr = value
            .bind(py)
            .repr()
            .map(|r| r.to_string())
            .unwrap_or_else(|_| "?".to_string());
        format!(
            "Signal(id={}, value={}, subscribers={})",
            self.id,
            repr,
            self.subscriber_count()
        )
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
    fn signal_get_and_set() {
        let signal = Signal::new(0);
        assert_eq!(signal.get(), 0);

        signal.set(42);
        assert_eq!(signal.get(), 42);
    }

    #[test]
    fn signal_update() {
        let signal = Signal::new(10);
        signal.update(|v| v + 5);
        assert_eq!(signal.get(), 15);
    }

    #[test]
    fn signal_notifies_subscribers() {
        let signal = Signal::new(0);
        let call_count = Arc::new(AtomicI32::new(0));
        let call_count_clone = call_count.clone();

        let subscriber_id = SubscriberId::new();
        signal.subscribe(subscriber_id, move || {
            call_count_clone.fetch_add(1, Ordering::SeqCst);
        });

        assert_eq!(call_count.load(Ordering::SeqCst), 0);

        signal.set(1);
        assert_eq!(call_count.load(Ordering::SeqCst), 1);

        signal.set(2);
        assert_eq!(call_count.load(Ordering::SeqCst), 2);
    }

    #[test]
    fn signal_unsubscribe() {
        let signal = Signal::new(0);
        let call_count = Arc::new(AtomicI32::new(0));
        let call_count_clone = call_count.clone();

        let subscriber_id = SubscriberId::new();
        signal.subscribe(subscriber_id, move || {
            call_count_clone.fetch_add(1, Ordering::SeqCst);
        });

        signal.set(1);
        assert_eq!(call_count.load(Ordering::SeqCst), 1);

        signal.unsubscribe(subscriber_id);
        signal.set(2);
        // Should not have been called again
        assert_eq!(call_count.load(Ordering::SeqCst), 1);
    }

    #[test]
    fn signal_clone_shares_state() {
        let signal1 = Signal::new(0);
        let signal2 = signal1.clone();

        signal1.set(42);
        assert_eq!(signal2.get(), 42);

        signal2.set(100);
        assert_eq!(signal1.get(), 100);
    }

    #[test]
    fn signal_ids_are_unique() {
        let s1 = Signal::new(0);
        let s2 = Signal::new(0);
        let s3 = Signal::new(0);

        assert_ne!(s1.id(), s2.id());
        assert_ne!(s2.id(), s3.id());
        assert_ne!(s1.id(), s3.id());
    }
}
