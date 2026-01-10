//! Intermediate Representation for JIT Compilation
//!
//! Defines the IR types that represent traced Python operations.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Operation codes matching the Python tracer
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum OpCode {
    // Arithmetic
    Add,
    Sub,
    Mul,
    Div,
    Mod,
    Neg,
    
    // Comparison
    Lt,
    Le,
    Gt,
    Ge,
    Eq,
    Ne,
    
    // Other
    Const,
    Load,
    Call,
}

/// A single operation in the trace
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Op {
    /// Operation type
    pub op: OpCode,
    /// Result value ID
    pub result: usize,
    /// Operand value IDs or literal values
    pub operands: Vec<Operand>,
    /// Data type (e.g., "f64", "i64")
    #[serde(default = "default_dtype")]
    pub dtype: String,
}

fn default_dtype() -> String {
    "f64".to_string()
}

/// An operand can be a value reference or a literal
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(untagged)]
pub enum Operand {
    /// Reference to a value by ID
    Ref(usize),
    /// Literal float value
    Float(f64),
    /// Literal string (e.g., variable name)
    String(String),
}

/// Complete trace IR for compilation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TraceIR {
    /// Input variable names mapped to value IDs
    pub inputs: HashMap<String, usize>,
    /// Output value ID
    pub output: usize,
    /// List of operations
    pub ops: Vec<Op>,
}

impl TraceIR {
    /// Parse IR from JSON string
    pub fn from_json(json: &str) -> Result<Self, serde_json::Error> {
        serde_json::from_str(json)
    }
    
    /// Get all unique value IDs
    pub fn value_ids(&self) -> Vec<usize> {
        self.ops.iter().map(|op| op.result).collect()
    }
    
    /// Get the number of inputs
    pub fn num_inputs(&self) -> usize {
        self.inputs.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_parse_simple_ir() {
        let json = r#"{
            "inputs": {"x": 1, "y": 2},
            "output": 3,
            "ops": [
                {"op": "load", "result": 1, "operands": ["x"], "dtype": "f64"},
                {"op": "load", "result": 2, "operands": ["y"], "dtype": "f64"},
                {"op": "add", "result": 3, "operands": [1, 2], "dtype": "f64"}
            ]
        }"#;
        
        let ir = TraceIR::from_json(json).unwrap();
        assert_eq!(ir.inputs.len(), 2);
        assert_eq!(ir.output, 3);
        assert_eq!(ir.ops.len(), 3);
    }
}
