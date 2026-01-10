//! JIT Compilation Module
//!
//! This module provides JIT compilation of traced Python operations
//! using LLVM via the inkwell crate.
//!
//! # Architecture
//!
//! 1. Python traces operations using `TracedValue`
//! 2. Trace is serialized as IR (list of operations)
//! 3. This module compiles IR to LLVM bitcode
//! 4. LLVM optimizes and generates native code
//! 5. Compiled function is called from Python
//!
//! # Example
//!
//! ```ignore
//! use lattice_core::jit::{JitCompiler, CompiledFn};
//!
//! let compiler = JitCompiler::new();
//! let ir = r#"{"inputs": {"x": 1}, "output": 2, "ops": [...]}"#;
//! let func = compiler.compile(ir)?;
//! let result = func.call(&[5.0]);
//! ```

mod ir;
mod codegen;

pub use ir::{Op, OpCode, TraceIR};
pub use codegen::{JitCompiler, CompiledFunction};
