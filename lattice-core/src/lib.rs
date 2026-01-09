//! Lattice Core
//!
//! This crate provides the core runtime for the Lattice reactive UI framework.
//! It implements:
//!
//! - Reactive primitives (signals, memos, effects)
//! - Incremental computation engine
//! - Virtual DOM and rendering pipeline
//! - WebSocket transport layer
//!
//! The crate is designed to be used both as a native Rust library and as a
//! Python extension module via PyO3.
//!
//! # Architecture
//!
//! The crate is organized into several modules:
//!
//! - `reactive`: Core reactive primitives and dependency tracking
//! - `graph`: Computational dependency graph implementation
//! - `render`: Virtual DOM and patch generation
//! - `transport`: WebSocket server and protocol implementation
//!
//! # Example
//!
//! ```rust,ignore
//! use lattice_core::reactive::{Signal, Memo, Effect};
//!
//! // Create a signal
//! let count = Signal::new(0);
//!
//! // Create a derived value
//! let doubled = Memo::new(|| count.get() * 2);
//!
//! // Create an effect
//! Effect::new(|| {
//!     println!("Count: {}, Doubled: {}", count.get(), doubled.get());
//! });
//!
//! // Update the signal
//! count.set(5);
//! // Effect automatically runs, prints: "Count: 5, Doubled: 10"
//! ```

pub mod reactive;
pub mod graph;

use pyo3::prelude::*;

/// Python module definition.
///
/// This function is called by Python when importing the module.
/// It registers all Python-exposed types and functions.
#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Register reactive primitives
    m.add_class::<reactive::PySignal>()?;

    // Add version info
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;

    Ok(())
}
