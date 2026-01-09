//! Reactive Primitives
//!
//! This module implements the core reactive system: signals, memos, and effects.
//! These primitives form the foundation of Lattice's fine-grained reactivity.
//!
//! # Concepts
//!
//! ## Signals
//!
//! A Signal is a container for mutable state. When a signal's value is read
//! within a tracking context (such as a memo or effect), the signal automatically
//! registers that context as a dependent. When the signal's value changes, all
//! dependents are notified.
//!
//! ## Memos
//!
//! A Memo is a derived value that caches its result. It re-evaluates only when
//! one of its dependencies changes. Memos are useful for expensive computations
//! that should not be repeated unnecessarily.
//!
//! ## Effects
//!
//! An Effect is a side-effecting computation that runs whenever its dependencies
//! change. Effects are used to synchronize reactive state with external systems,
//! such as updating the DOM or logging.
//!
//! # Implementation Notes
//!
//! The reactive system uses a thread-local tracking context to automatically
//! detect dependencies. When a signal is read, we check if there is an active
//! tracking context and, if so, register the dependency.
//!
//! This approach (sometimes called "automatic dependency tracking" or
//! "transparent reactivity") is used by SolidJS, Vue 3, and Leptos.

mod signal;
mod context;
mod subscriber;
mod memo;
mod effect;
mod runtime;

pub use signal::{Signal, PySignal};
pub use context::ReactiveContext;
pub use subscriber::{Subscriber, SubscriberId};
pub use memo::{Memo, MemoState};
pub use effect::Effect;
pub use runtime::{Runtime, Reactive, ReactiveHandle};
