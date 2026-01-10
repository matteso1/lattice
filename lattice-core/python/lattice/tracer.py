"""
Lattice JIT - Python Operation Tracer

This module traces Python operations during execution, recording them
for later compilation to native code via LLVM.

The tracer captures:
- Arithmetic operations (+, -, *, /, %)
- Comparisons (<, >, ==, etc.)
- Function calls
- Variable accesses

Example:
    from lattice.tracer import trace, TracedValue
    
    with trace() as ctx:
        x = TracedValue(5, "x")
        y = TracedValue(3, "y")
        result = x * y + 10
    
    print(ctx.ops)  # [Mul(x, y), Add(tmp0, 10)]
"""

from typing import Any, List, Tuple, Union, Optional, Dict
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager
import threading


class OpCode(Enum):
    """Operation codes for traced operations."""
    # Arithmetic
    ADD = "add"
    SUB = "sub"
    MUL = "mul"
    DIV = "div"
    MOD = "mod"
    NEG = "neg"
    
    # Comparison
    LT = "lt"
    LE = "le"
    GT = "gt"
    GE = "ge"
    EQ = "eq"
    NE = "ne"
    
    # Other
    CONST = "const"
    LOAD = "load"
    CALL = "call"


@dataclass
class TracedOp:
    """A single traced operation."""
    opcode: OpCode
    result_id: int
    operands: Tuple[Any, ...]
    dtype: str = "f64"  # Default to float64
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "op": self.opcode.value,
            "result": self.result_id,
            "operands": [
                op.value_id if isinstance(op, TracedValue) else op
                for op in self.operands
            ],
            "dtype": self.dtype,
        }


class TracedValue:
    """
    A value that records operations performed on it.
    
    When arithmetic or other operations are performed on TracedValues,
    the operation is recorded and a new TracedValue is returned.
    """
    
    def __init__(self, value: Any, name: Optional[str] = None, ctx: Optional["TraceContext"] = None, _skip_op: bool = False):
        """
        Create a traced value.
        
        Args:
            value: The actual Python value.
            name: Optional name for debugging.
            ctx: Trace context (auto-detected if not provided).
            _skip_op: If True, don't emit a const/load op (for intermediate results).
        """
        self._value = value
        self._name = name
        self._ctx = ctx or _get_current_context()
        
        if self._ctx:
            self.value_id = self._ctx.next_id()
            # Record as a constant or load (unless this is an intermediate result)
            if not _skip_op:
                if name:
                    self._ctx.add_op(TracedOp(
                        opcode=OpCode.LOAD,
                        result_id=self.value_id,
                        operands=(name,),
                        dtype=_infer_type(value),
                    ))
                else:
                    self._ctx.add_op(TracedOp(
                        opcode=OpCode.CONST,
                        result_id=self.value_id,
                        operands=(value,),
                        dtype=_infer_type(value),
                    ))
        else:
            self.value_id = -1
    
    @property
    def value(self) -> Any:
        """Get the underlying Python value."""
        return self._value
    
    def _binop(self, other: Any, opcode: OpCode) -> "TracedValue":
        """Perform a binary operation and record it."""
        other_val = other._value if isinstance(other, TracedValue) else other
        result_val = {
            OpCode.ADD: lambda a, b: a + b,
            OpCode.SUB: lambda a, b: a - b,
            OpCode.MUL: lambda a, b: a * b,
            OpCode.DIV: lambda a, b: a / b,
            OpCode.MOD: lambda a, b: a % b,
            OpCode.LT: lambda a, b: a < b,
            OpCode.LE: lambda a, b: a <= b,
            OpCode.GT: lambda a, b: a > b,
            OpCode.GE: lambda a, b: a >= b,
            OpCode.EQ: lambda a, b: a == b,
            OpCode.NE: lambda a, b: a != b,
        }[opcode](self._value, other_val)
        
        # Create result without emitting const (we'll emit the real op below)
        result = TracedValue(result_val, ctx=self._ctx, _skip_op=True)
        
        # Wrap non-TracedValue operands
        if not isinstance(other, TracedValue):
            other = TracedValue(other, ctx=self._ctx)
        
        if self._ctx:
            self._ctx.add_op(TracedOp(
                opcode=opcode,
                result_id=result.value_id,
                operands=(self, other),
                dtype=_infer_type(result_val),
            ))
        
        return result

    
    def __add__(self, other): return self._binop(other, OpCode.ADD)
    def __radd__(self, other): return TracedValue(other, ctx=self._ctx)._binop(self, OpCode.ADD)
    def __sub__(self, other): return self._binop(other, OpCode.SUB)
    def __rsub__(self, other): return TracedValue(other, ctx=self._ctx)._binop(self, OpCode.SUB)
    def __mul__(self, other): return self._binop(other, OpCode.MUL)
    def __rmul__(self, other): return TracedValue(other, ctx=self._ctx)._binop(self, OpCode.MUL)
    def __truediv__(self, other): return self._binop(other, OpCode.DIV)
    def __rtruediv__(self, other): return TracedValue(other, ctx=self._ctx)._binop(self, OpCode.DIV)
    def __mod__(self, other): return self._binop(other, OpCode.MOD)
    def __rmod__(self, other): return TracedValue(other, ctx=self._ctx)._binop(self, OpCode.MOD)
    
    def __lt__(self, other): return self._binop(other, OpCode.LT)
    def __le__(self, other): return self._binop(other, OpCode.LE)
    def __gt__(self, other): return self._binop(other, OpCode.GT)
    def __ge__(self, other): return self._binop(other, OpCode.GE)
    def __eq__(self, other): return self._binop(other, OpCode.EQ)
    def __ne__(self, other): return self._binop(other, OpCode.NE)
    
    def __neg__(self):
        result_val = -self._value
        result = TracedValue(result_val, ctx=self._ctx)
        if self._ctx:
            self._ctx.add_op(TracedOp(
                opcode=OpCode.NEG,
                result_id=result.value_id,
                operands=(self,),
                dtype=_infer_type(result_val),
            ))
        return result
    
    def __repr__(self):
        if self._name:
            return f"TracedValue({self._name}={self._value})"
        return f"TracedValue({self._value})"


class TraceContext:
    """
    Context for tracing operations.
    
    Collects all operations performed within the trace context.
    """
    
    def __init__(self):
        self.ops: List[TracedOp] = []
        self._id_counter = 0
        self.inputs: Dict[str, int] = {}  # name -> value_id
        self.output_id: Optional[int] = None
    
    def next_id(self) -> int:
        """Get the next unique value ID."""
        self._id_counter += 1
        return self._id_counter
    
    def add_op(self, op: TracedOp) -> None:
        """Add an operation to the trace."""
        self.ops.append(op)
        if op.opcode == OpCode.LOAD and op.operands:
            self.inputs[op.operands[0]] = op.result_id
    
    def set_output(self, value: TracedValue) -> None:
        """Mark a value as the output of this trace."""
        self.output_id = value.value_id
    
    def to_ir(self) -> Dict[str, Any]:
        """Convert trace to IR for compilation."""
        return {
            "inputs": self.inputs,
            "output": self.output_id,
            "ops": [op.to_dict() for op in self.ops],
        }


# Thread-local trace context
_trace_context = threading.local()


def _get_current_context() -> Optional[TraceContext]:
    """Get the current trace context."""
    return getattr(_trace_context, 'ctx', None)


def _set_current_context(ctx: Optional[TraceContext]) -> None:
    """Set the current trace context."""
    _trace_context.ctx = ctx


@contextmanager
def trace():
    """
    Context manager for tracing operations.
    
    Example:
        with trace() as ctx:
            x = TracedValue(5, "x")
            y = TracedValue(3, "y")
            result = x + y
            ctx.set_output(result)
        
        print(ctx.to_ir())
    """
    ctx = TraceContext()
    _set_current_context(ctx)
    try:
        yield ctx
    finally:
        _set_current_context(None)


def _infer_type(value: Any) -> str:
    """Infer LLVM type from Python value."""
    if isinstance(value, bool):
        return "i1"
    elif isinstance(value, int):
        return "i64"
    elif isinstance(value, float):
        return "f64"
    else:
        return "f64"  # Default to float


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------

def _test_basic_tracing():
    """Test basic operation tracing."""
    with trace() as ctx:
        x = TracedValue(5.0, "x")
        y = TracedValue(3.0, "y")
        result = x + y
        ctx.set_output(result)
    
    assert len(ctx.ops) == 3  # load x, load y, add
    assert ctx.ops[-1].opcode == OpCode.ADD
    print("  Basic tracing: PASS")


def _test_complex_expression():
    """Test tracing complex expressions."""
    with trace() as ctx:
        a = TracedValue(2.0, "a")
        b = TracedValue(3.0, "b")
        c = TracedValue(4.0, "c")
        result = a * b + c  # Should be (a*b)+c
        ctx.set_output(result)
    
    # Should have: load a, load b, load c, mul, add
    opcodes = [op.opcode for op in ctx.ops]
    assert OpCode.MUL in opcodes
    assert OpCode.ADD in opcodes
    print("  Complex expression: PASS")


def _test_comparison():
    """Test comparison operators."""
    with trace() as ctx:
        x = TracedValue(5.0, "x")
        y = TracedValue(3.0, "y")
        result = x > y
        ctx.set_output(result)
    
    assert ctx.ops[-1].opcode == OpCode.GT
    assert result.value == True
    print("  Comparison: PASS")


def _test_to_ir():
    """Test IR generation."""
    with trace() as ctx:
        x = TracedValue(5.0, "x")
        y = TracedValue(3.0, "y")
        result = x * y
        ctx.set_output(result)
    
    ir = ctx.to_ir()
    assert "inputs" in ir
    assert "output" in ir
    assert "ops" in ir
    assert ir["output"] is not None
    print("  IR generation: PASS")


if __name__ == "__main__":
    print("Running tracer tests...")
    _test_basic_tracing()
    _test_complex_expression()
    _test_comparison()
    _test_to_ir()
    print("All tests passed!")
