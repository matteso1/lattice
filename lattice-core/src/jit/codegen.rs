//! Cranelift Code Generation
//!
//! Compiles TraceIR to native code via Cranelift.
//! 
//! Cranelift is a fast, pure-Rust code generator used by:
//! - The Rust compiler (for debug builds)
//! - Firefox (for WebAssembly)
//! - Wasmtime (WASM runtime)

use std::collections::HashMap;

use cranelift::prelude::*;
use cranelift_jit::{JITBuilder, JITModule};
use cranelift_module::{Module, Linkage, FuncId};
use target_lexicon::Triple;

use super::ir::{Op, OpCode, Operand, TraceIR};

/// Type alias for JIT-compiled functions: fn(*const f64) -> f64
type JitFn = unsafe extern "C" fn(*const f64) -> f64;

/// A compiled function that can be called with f64 inputs
pub struct CompiledFunction {
    /// The JIT module (keeps code alive)
    _module: JITModule,
    /// Function pointer
    func_ptr: JitFn,
    /// Number of inputs
    pub num_inputs: usize,
}

impl CompiledFunction {
    /// Call the compiled function
    pub fn call(&self, inputs: &[f64]) -> f64 {
        assert_eq!(inputs.len(), self.num_inputs, "Wrong number of inputs");
        unsafe { (self.func_ptr)(inputs.as_ptr()) }
    }
}

/// JIT compiler using Cranelift
pub struct JitCompiler {
    /// ISA for the current platform
    isa: isa::OwnedTargetIsa,
}

impl JitCompiler {
    /// Create a new JIT compiler for the host platform
    pub fn new() -> Result<Self, String> {
        let mut flag_builder = settings::builder();
        flag_builder.set("opt_level", "speed").map_err(|e| e.to_string())?;
        
        let isa_builder = cranelift_native::builder()
            .map_err(|e| format!("Failed to create ISA builder: {}", e))?;
        
        let flags = settings::Flags::new(flag_builder);
        let isa = isa_builder.finish(flags)
            .map_err(|e| format!("Failed to build ISA: {}", e))?;
        
        Ok(Self { isa })
    }
    
    /// Compile a trace to native code
    pub fn compile(&self, ir: &TraceIR) -> Result<CompiledFunction, String> {
        // Create JIT module
        let builder = JITBuilder::with_isa(
            self.isa.clone(),
            cranelift_module::default_libcall_names(),
        );
        let mut module = JITModule::new(builder);
        
        // Create function signature: fn(*i64) -> f64
        let mut ctx = module.make_context();
        let ptr_type = module.target_config().pointer_type();
        
        ctx.func.signature.params.push(AbiParam::new(ptr_type));
        ctx.func.signature.returns.push(AbiParam::new(types::F64));
        
        // Declare the function
        let func_id = module.declare_function(
            "jit_fn",
            Linkage::Local,
            &ctx.func.signature,
        ).map_err(|e| e.to_string())?;
        
        // Build the function
        let mut builder_ctx = FunctionBuilderContext::new();
        let mut builder = FunctionBuilder::new(&mut ctx.func, &mut builder_ctx);
        
        let entry_block = builder.create_block();
        builder.append_block_params_for_function_params(entry_block);
        builder.switch_to_block(entry_block);
        builder.seal_block(entry_block);
        
        // Get input pointer
        let input_ptr = builder.block_params(entry_block)[0];
        
        // Map value IDs to Cranelift values
        let mut values: HashMap<usize, Value> = HashMap::new();
        
        // Process each operation
        for op in &ir.ops {
            let result = match op.op {
                OpCode::Load => {
                    // Load from input array
                    let name = match &op.operands[0] {
                        Operand::String(s) => s.clone(),
                        _ => return Err("Load expects string operand".into()),
                    };
                    let idx = *ir.inputs.get(&name)
                        .ok_or_else(|| format!("Unknown input: {}", name))?;
                    
                    // Calculate offset: (idx - 1) * 8 bytes
                    let offset = ((idx - 1) * 8) as i32;
                    builder.ins().load(types::F64, MemFlags::new(), input_ptr, offset)
                }
                
                OpCode::Const => {
                    let val = match &op.operands[0] {
                        Operand::Float(f) => *f,
                        Operand::Ref(r) => *r as f64,
                        _ => return Err("Const expects numeric operand".into()),
                    };
                    builder.ins().f64const(val)
                }
                
                OpCode::Add => {
                    let lhs = self.get_operand(&op.operands[0], &values, &mut builder)?;
                    let rhs = self.get_operand(&op.operands[1], &values, &mut builder)?;
                    builder.ins().fadd(lhs, rhs)
                }
                
                OpCode::Sub => {
                    let lhs = self.get_operand(&op.operands[0], &values, &mut builder)?;
                    let rhs = self.get_operand(&op.operands[1], &values, &mut builder)?;
                    builder.ins().fsub(lhs, rhs)
                }
                
                OpCode::Mul => {
                    let lhs = self.get_operand(&op.operands[0], &values, &mut builder)?;
                    let rhs = self.get_operand(&op.operands[1], &values, &mut builder)?;
                    builder.ins().fmul(lhs, rhs)
                }
                
                OpCode::Div => {
                    let lhs = self.get_operand(&op.operands[0], &values, &mut builder)?;
                    let rhs = self.get_operand(&op.operands[1], &values, &mut builder)?;
                    builder.ins().fdiv(lhs, rhs)
                }
                
                OpCode::Neg => {
                    let val = self.get_operand(&op.operands[0], &values, &mut builder)?;
                    builder.ins().fneg(val)
                }
                
                // Comparison ops return 0.0 or 1.0
                OpCode::Lt | OpCode::Le | OpCode::Gt | OpCode::Ge | OpCode::Eq | OpCode::Ne => {
                    let lhs = self.get_operand(&op.operands[0], &values, &mut builder)?;
                    let rhs = self.get_operand(&op.operands[1], &values, &mut builder)?;
                    let cond = match op.op {
                        OpCode::Lt => FloatCC::LessThan,
                        OpCode::Le => FloatCC::LessThanOrEqual,
                        OpCode::Gt => FloatCC::GreaterThan,
                        OpCode::Ge => FloatCC::GreaterThanOrEqual,
                        OpCode::Eq => FloatCC::Equal,
                        OpCode::Ne => FloatCC::NotEqual,
                        _ => unreachable!(),
                    };
                    let cmp = builder.ins().fcmp(cond, lhs, rhs);
                    // Convert i8 bool to f64 (0.0 or 1.0)
                    let int_val = builder.ins().uextend(types::I64, cmp);
                    builder.ins().fcvt_from_uint(types::F64, int_val)
                }
                
                OpCode::Mod | OpCode::Call => {
                    return Err(format!("Unsupported opcode: {:?}", op.op));
                }
            };
            
            values.insert(op.result, result);
        }
        
        // Return the output value
        let output = values.get(&ir.output)
            .ok_or("Output value not found")?;
        builder.ins().return_(&[*output]);
        
        builder.finalize();
        
        // Compile the function
        module.define_function(func_id, &mut ctx)
            .map_err(|e| e.to_string())?;
        module.clear_context(&mut ctx);
        module.finalize_definitions()
            .map_err(|e| e.to_string())?;
        
        // Get the function pointer
        let code_ptr = module.get_finalized_function(func_id);
        let func_ptr: JitFn = unsafe { std::mem::transmute(code_ptr) };
        
        Ok(CompiledFunction {
            _module: module,
            func_ptr,
            num_inputs: ir.num_inputs(),
        })
    }
    
    fn get_operand(
        &self,
        op: &Operand,
        values: &HashMap<usize, Value>,
        builder: &mut FunctionBuilder,
    ) -> Result<Value, String> {
        match op {
            Operand::Ref(id) => values.get(id)
                .copied()
                .ok_or_else(|| format!("Value {} not found", id)),
            Operand::Float(f) => Ok(builder.ins().f64const(*f)),
            Operand::String(s) => Err(format!("Unexpected string operand: {}", s)),
        }
    }
}

impl Default for JitCompiler {
    fn default() -> Self {
        Self::new().expect("Failed to create JIT compiler")
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_simple_add() {
        let ir = TraceIR::from_json(r#"{
            "inputs": {"x": 1, "y": 2},
            "output": 3,
            "ops": [
                {"op": "load", "result": 1, "operands": ["x"], "dtype": "f64"},
                {"op": "load", "result": 2, "operands": ["y"], "dtype": "f64"},
                {"op": "add", "result": 3, "operands": [1, 2], "dtype": "f64"}
            ]
        }"#).unwrap();
        
        let compiler = JitCompiler::new().unwrap();
        let func = compiler.compile(&ir).unwrap();
        
        let result = func.call(&[5.0, 3.0]);
        assert_eq!(result, 8.0);
    }
    
    #[test]
    fn test_complex_expr() {
        // (x + y) * 2
        let ir = TraceIR::from_json(r#"{
            "inputs": {"x": 1, "y": 2},
            "output": 4,
            "ops": [
                {"op": "load", "result": 1, "operands": ["x"], "dtype": "f64"},
                {"op": "load", "result": 2, "operands": ["y"], "dtype": "f64"},
                {"op": "add", "result": 3, "operands": [1, 2], "dtype": "f64"},
                {"op": "const", "result": 5, "operands": [2.0], "dtype": "f64"},
                {"op": "mul", "result": 4, "operands": [3, 5], "dtype": "f64"}
            ]
        }"#).unwrap();
        
        let compiler = JitCompiler::new().unwrap();
        let func = compiler.compile(&ir).unwrap();
        
        let result = func.call(&[5.0, 3.0]);
        assert_eq!(result, 16.0);  // (5 + 3) * 2 = 16
    }
}
