"""
Lattice JIT Benchmark - Native Code vs Python

Demonstrates the JIT compiling Python expressions to native code.
Compares:
1. Python eval
2. Traced execution (Python)
3. JIT compiled (Cranelift native code)

Run: python examples/jit_benchmark.py
"""

import sys
import time
import json
sys.path.insert(0, "python")

from lattice.tracer import trace, TracedValue
from lattice._core import JitCompiler


def python_eval(expr: str, x: float, y: float, z: float) -> float:
    """Pure Python evaluation."""
    return eval(expr, {"__builtins__": {}}, {"x": x, "y": y, "z": z})


def traced_eval(expr: str, x: float, y: float, z: float) -> tuple:
    """Traced execution (captures ops but runs in Python)."""
    with trace() as ctx:
        traced_x = TracedValue(x, "x")
        traced_y = TracedValue(y, "y")
        traced_z = TracedValue(z, "z")
        result = eval(expr, {"__builtins__": {}}, {
            "x": traced_x, "y": traced_y, "z": traced_z
        })
        ctx.set_output(result)
    return result.value, ctx.to_ir()


def main():
    print("=" * 60)
    print("⚡ Lattice JIT Benchmark - Native Code Execution")
    print("=" * 60)
    print()
    
    # Test expressions
    expressions = [
        ("x + y", "simple add"),
        ("x * y + z", "multiply-add"),
        ("(x + y) * (x - y)", "difference of squares"),
        ("x * x + y * y + z * z", "sum of squares"),
    ]
    
    # Test values
    x, y, z = 5.0, 3.0, 10.0
    iterations = 100000
    
    print(f"Test values: x={x}, y={y}, z={z}")
    print(f"Iterations: {iterations:,}")
    print()
    
    # Create JIT compiler
    compiler = JitCompiler()
    
    for expr, name in expressions:
        print(f"Expression: {expr} ({name})")
        print("-" * 50)
        
        # Get expected result
        expected = python_eval(expr, x, y, z)
        print(f"Expected result: {expected}")
        
        # Trace to get IR
        _, ir = traced_eval(expr, x, y, z)
        ir_json = json.dumps(ir)
        
        # Test JIT compile and run
        jit_result = compiler.compile_and_run(ir_json, [x, y, z])
        print(f"JIT result:      {jit_result}")
        
        if abs(jit_result - expected) > 0.0001:
            print(f"  ⚠️  MISMATCH!")
            continue
        
        print(f"  ✓ Results match!")
        
        # Benchmark Python eval
        start = time.perf_counter()
        for _ in range(iterations):
            python_eval(expr, x, y, z)
        python_time = time.perf_counter() - start
        
        # Benchmark JIT (includes compilation)
        jit_result, jit_time_us = compiler.benchmark(ir_json, [x, y, z], iterations)
        jit_time = jit_time_us / 1_000_000  # Convert to seconds
        
        print()
        print(f"  Python:  {python_time*1000:.2f} ms ({iterations/python_time:,.0f} ops/sec)")
        print(f"  JIT:     {jit_time*1000:.2f} ms ({iterations/jit_time:,.0f} ops/sec)")
        
        speedup = python_time / jit_time if jit_time > 0 else 0
        if speedup > 1:
            print(f"  🚀 JIT is {speedup:.1f}x FASTER")
        else:
            print(f"  ⚠️  JIT is {1/speedup:.1f}x slower (overhead)")
        
        print()
    
    print("=" * 60)
    print("✅ JIT Benchmark Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
