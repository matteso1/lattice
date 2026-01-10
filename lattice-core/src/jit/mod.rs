//! JIT Compilation Module
//!
//! This module provides JIT compilation of traced Python operations
//! using Cranelift for native code generation.
//!
//! # Architecture
//!
//! 1. Python traces operations using `TracedValue`
//! 2. Trace is serialized as IR (list of operations)
//! 3. This module compiles IR to native code via Cranelift
//! 4. Compiled function is called with inputs

mod ir;
mod codegen;

pub use ir::{Op, OpCode, TraceIR};
pub use codegen::{JitCompiler, CompiledFunction};

use pyo3::prelude::*;
use pyo3::exceptions::PyRuntimeError;

/// Python-exposed JIT compiler.
#[pyclass(name = "JitCompiler")]
pub struct PyJitCompiler {
    compiler: JitCompiler,
}

#[pymethods]
impl PyJitCompiler {
    /// Create a new JIT compiler.
    #[new]
    fn new() -> PyResult<Self> {
        let compiler = JitCompiler::new()
            .map_err(|e| PyRuntimeError::new_err(e))?;
        Ok(Self { compiler })
    }
    
    /// Compile IR JSON and run with inputs.
    fn compile_and_run(&self, ir_json: &str, inputs: Vec<f64>) -> PyResult<f64> {
        // Parse IR
        let ir = TraceIR::from_json(ir_json)
            .map_err(|e| PyRuntimeError::new_err(format!("IR parse error: {}", e)))?;
        
        // Compile
        let func = self.compiler.compile(&ir)
            .map_err(|e| PyRuntimeError::new_err(format!("Compile error: {}", e)))?;
        
        // Execute
        if inputs.len() != func.num_inputs() {
            return Err(PyRuntimeError::new_err(format!(
                "Expected {} inputs, got {}", func.num_inputs(), inputs.len()
            )));
        }
        
        Ok(func.call(&inputs))
    }
    
    /// Compile IR and benchmark execution.
    /// Returns (result, time_microseconds).
    fn benchmark(&self, ir_json: &str, inputs: Vec<f64>, iterations: usize) -> PyResult<(f64, f64)> {
        use std::time::Instant;
        
        // Parse and compile
        let ir = TraceIR::from_json(ir_json)
            .map_err(|e| PyRuntimeError::new_err(format!("IR parse error: {}", e)))?;
        let func = self.compiler.compile(&ir)
            .map_err(|e| PyRuntimeError::new_err(format!("Compile error: {}", e)))?;
        
        // Benchmark
        let start = Instant::now();
        let mut result = 0.0;
        for _ in 0..iterations {
            result = func.call(&inputs);
        }
        let elapsed = start.elapsed();
        
        let total_us = elapsed.as_micros() as f64;
        Ok((result, total_us))
    }
}

impl CompiledFunction {
    pub fn num_inputs(&self) -> usize {
        self.num_inputs
    }
}
