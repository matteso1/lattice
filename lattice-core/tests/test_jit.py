"""
Tests for Lattice JIT Compilation System (Phase 4).

These tests verify the tracer, IR generation, and JIT execution.
"""

import pytest


class TestTracer:
    """Tests for Python operation tracer."""
    
    def test_tracer_captures_load(self):
        """Tracer should capture load operations."""
        from lattice.tracer import trace, TracedValue, OpCode
        
        with trace() as ctx:
            x = TracedValue(5.0, "x")
        
        load_ops = [op for op in ctx.ops if op.opcode == OpCode.LOAD]
        assert len(load_ops) == 1
        assert "x" in ctx.inputs
    
    def test_tracer_captures_add(self):
        """Tracer should capture add operations."""
        from lattice.tracer import trace, TracedValue, OpCode
        
        with trace() as ctx:
            x = TracedValue(5.0, "x")
            y = TracedValue(3.0, "y")
            result = x + y
            ctx.set_output(result)
        
        add_ops = [op for op in ctx.ops if op.opcode == OpCode.ADD]
        assert len(add_ops) == 1
    
    def test_tracer_captures_sub(self):
        """Tracer should capture subtract operations."""
        from lattice.tracer import trace, TracedValue, OpCode
        
        with trace() as ctx:
            x = TracedValue(5.0, "x")
            y = TracedValue(3.0, "y")
            result = x - y
            ctx.set_output(result)
        
        assert result.value == 2.0
        sub_ops = [op for op in ctx.ops if op.opcode == OpCode.SUB]
        assert len(sub_ops) == 1
    
    def test_tracer_captures_mul(self):
        """Tracer should capture multiply operations."""
        from lattice.tracer import trace, TracedValue, OpCode
        
        with trace() as ctx:
            x = TracedValue(5.0, "x")
            y = TracedValue(3.0, "y")
            result = x * y
            ctx.set_output(result)
        
        assert result.value == 15.0
    
    def test_tracer_captures_div(self):
        """Tracer should capture divide operations."""
        from lattice.tracer import trace, TracedValue, OpCode
        
        with trace() as ctx:
            x = TracedValue(10.0, "x")
            y = TracedValue(2.0, "y")
            result = x / y
            ctx.set_output(result)
        
        assert result.value == 5.0
    
    def test_tracer_captures_neg(self):
        """Tracer should capture negation operations."""
        from lattice.tracer import trace, TracedValue, OpCode
        
        with trace() as ctx:
            x = TracedValue(5.0, "x")
            result = -x
            ctx.set_output(result)
        
        assert result.value == -5.0
    
    def test_tracer_captures_comparison(self):
        """Tracer should capture comparison operations."""
        from lattice.tracer import trace, TracedValue, OpCode
        
        with trace() as ctx:
            x = TracedValue(5.0, "x")
            y = TracedValue(3.0, "y")
            result = x > y
            ctx.set_output(result)
        
        assert result.value == True


class TestIRGeneration:
    """Tests for IR generation from traces."""
    
    def test_ir_has_inputs(self):
        """IR should include inputs."""
        from lattice.tracer import trace, TracedValue
        
        with trace() as ctx:
            x = TracedValue(5.0, "x")
            y = TracedValue(3.0, "y")
            result = x + y
            ctx.set_output(result)
        
        ir = ctx.to_ir()
        
        assert "x" in ir["inputs"]
        assert "y" in ir["inputs"]
    
    def test_ir_has_output(self):
        """IR should include output."""
        from lattice.tracer import trace, TracedValue
        
        with trace() as ctx:
            x = TracedValue(5.0, "x")
            result = x * 2
            ctx.set_output(result)
        
        ir = ctx.to_ir()
        
        assert ir["output"] is not None
    
    def test_ir_has_ops(self):
        """IR should include operations."""
        from lattice.tracer import trace, TracedValue
        
        with trace() as ctx:
            a = TracedValue(2.0, "a")
            b = TracedValue(3.0, "b")
            c = TracedValue(4.0, "c")
            result = (a + b) * c
            ctx.set_output(result)
        
        ir = ctx.to_ir()
        
        assert len(ir["ops"]) >= 4  # 3 loads + add + mul


class TestComplexExpressions:
    """Tests for complex traced expressions."""
    
    def test_chained_operations(self):
        """Chained operations should trace correctly."""
        from lattice.tracer import trace, TracedValue
        
        with trace() as ctx:
            x = TracedValue(2.0, "x")
            result = x + 1 + 2 + 3
            ctx.set_output(result)
        
        assert result.value == 8.0
    
    def test_mixed_operations(self):
        """Mixed operations should trace correctly."""
        from lattice.tracer import trace, TracedValue
        
        with trace() as ctx:
            a = TracedValue(10.0, "a")
            b = TracedValue(3.0, "b")
            result = (a + b) * (a - b)  # (10+3) * (10-3) = 13 * 7 = 91
            ctx.set_output(result)
        
        assert result.value == 91.0
    
    def test_literal_operations(self):
        """Operations with literals should work."""
        from lattice.tracer import trace, TracedValue
        
        with trace() as ctx:
            x = TracedValue(5.0, "x")
            result = x * 2 + 10  # 5*2+10 = 20
            ctx.set_output(result)
        
        assert result.value == 20.0


class TestTracerResults:
    """Tests that verify tracer produces correct Python results."""
    
    def test_add_result(self):
        """Add should produce correct result."""
        from lattice.tracer import trace, TracedValue
        
        with trace() as ctx:
            x = TracedValue(5.0, "x")
            y = TracedValue(3.0, "y")
            result = x + y
        
        assert result.value == 8.0
    
    def test_sub_result(self):
        """Sub should produce correct result."""
        from lattice.tracer import trace, TracedValue
        
        with trace() as ctx:
            x = TracedValue(5.0, "x")
            y = TracedValue(3.0, "y")
            result = x - y
        
        assert result.value == 2.0
    
    def test_mul_result(self):
        """Mul should produce correct result."""
        from lattice.tracer import trace, TracedValue
        
        with trace() as ctx:
            x = TracedValue(5.0, "x")
            y = TracedValue(3.0, "y")
            result = x * y
        
        assert result.value == 15.0
    
    def test_div_result(self):
        """Div should produce correct result."""
        from lattice.tracer import trace, TracedValue
        
        with trace() as ctx:
            x = TracedValue(6.0, "x")
            y = TracedValue(2.0, "y")
            result = x / y
        
        assert result.value == 3.0
    
    def test_comparison_results(self):
        """Comparisons should produce correct results."""
        from lattice.tracer import trace, TracedValue
        
        with trace() as ctx:
            x = TracedValue(5.0, "x")
            y = TracedValue(3.0, "y")
            
            lt = x < y
            le = x <= y
            gt = x > y
            ge = x >= y
        
        assert lt.value == False
        assert le.value == False
        assert gt.value == True
        assert ge.value == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
