//! Subscriber types for the reactive system.
//!
//! A Subscriber represents any computation that depends on reactive values.
//! This includes memos, effects, and render functions.

use std::sync::atomic::{AtomicU64, Ordering};

/// Unique identifier for a subscriber.
///
/// Each subscriber (memo, effect, or other reactive computation) gets a unique
/// ID when created. This ID is used to track dependencies and avoid duplicate
/// subscriptions.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct SubscriberId(u64);

impl SubscriberId {
    /// Generate a new unique subscriber ID.
    ///
    /// Uses an atomic counter to ensure uniqueness across threads.
    pub fn new() -> Self {
        static COUNTER: AtomicU64 = AtomicU64::new(0);
        Self(COUNTER.fetch_add(1, Ordering::Relaxed))
    }
}

impl Default for SubscriberId {
    fn default() -> Self {
        Self::new()
    }
}

/// A subscriber to reactive values.
///
/// Subscribers are notified when their dependencies change.
/// The notification callback is invoked with the subscriber's ID.
pub struct Subscriber {
    id: SubscriberId,
    /// The callback to invoke when dependencies change.
    /// 
    /// This is stored as a boxed trait object to allow different
    /// subscriber types (memos, effects, etc.) to have different
    /// notification behavior.
    notify: Box<dyn Fn() + Send + Sync>,
}

impl Subscriber {
    /// Create a new subscriber with the given notification callback.
    pub fn new<F>(notify: F) -> Self
    where
        F: Fn() + Send + Sync + 'static,
    {
        Self {
            id: SubscriberId::new(),
            notify: Box::new(notify),
        }
    }

    /// Get the subscriber's unique ID.
    pub fn id(&self) -> SubscriberId {
        self.id
    }

    /// Notify the subscriber that one of its dependencies changed.
    pub fn notify(&self) {
        (self.notify)();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn subscriber_ids_are_unique() {
        let id1 = SubscriberId::new();
        let id2 = SubscriberId::new();
        let id3 = SubscriberId::new();

        assert_ne!(id1, id2);
        assert_ne!(id2, id3);
        assert_ne!(id1, id3);
    }

    #[test]
    fn subscriber_notify_calls_callback() {
        use std::sync::atomic::{AtomicBool, Ordering};
        use std::sync::Arc;

        let called = Arc::new(AtomicBool::new(false));
        let called_clone = called.clone();

        let subscriber = Subscriber::new(move || {
            called_clone.store(true, Ordering::SeqCst);
        });

        assert!(!called.load(Ordering::SeqCst));
        subscriber.notify();
        assert!(called.load(Ordering::SeqCst));
    }
}
