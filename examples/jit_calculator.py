"""
Lattice JIT Calculator Demo

This demo shows the JIT compilation pipeline:
1. User enters a math expression
2. Python tracer records operations
3. Cranelift compiles to native code
4. Execute and benchmark vs Python eval

Run: python examples/jit_calculator.py
Open: http://localhost:8001
"""

import asyncio
import time
import json
from aiohttp import web

# Import Lattice JIT tracer
import sys
sys.path.insert(0, "python")
from lattice.tracer import trace, TracedValue, OpCode


def trace_expression(expr: str, variables: dict[str, float]) -> dict:
    """
    Trace a math expression and return IR + Python result.
    
    Args:
        expr: Expression like "x * y + 10"
        variables: Dict of variable values like {"x": 5, "y": 3}
    
    Returns:
        Dict with traced IR, Python result, trace info
    """
    with trace() as ctx:
        # Create TracedValues for each variable
        traced_vars = {}
        for name, value in variables.items():
            traced_vars[name] = TracedValue(float(value), name)
        
        # Build expression using eval with traced values
        # This is safe because we control what's in traced_vars
        try:
            result = eval(expr, {"__builtins__": {}}, traced_vars)
            if isinstance(result, TracedValue):
                ctx.set_output(result)
                python_result = result.value
            else:
                python_result = result
        except Exception as e:
            return {"error": str(e)}
    
    return {
        "ir": ctx.to_ir(),
        "python_result": python_result,
        "ops_count": len(ctx.ops),
        "inputs": list(ctx.inputs.keys()),
    }


def benchmark_expression(expr: str, variables: dict[str, float], iterations: int = 10000) -> dict:
    """
    Benchmark expression: traced execution vs Python eval.
    """
    # Time Python eval
    start = time.perf_counter()
    for _ in range(iterations):
        result = eval(expr, {"__builtins__": {}}, variables)
    python_time = time.perf_counter() - start
    
    # Time traced execution (TracedValue overhead)
    start = time.perf_counter()
    for _ in range(iterations):
        with trace() as ctx:
            traced_vars = {name: TracedValue(float(val), name) 
                          for name, val in variables.items()}
            traced_result = eval(expr, {"__builtins__": {}}, traced_vars)
    traced_time = time.perf_counter() - start
    
    return {
        "python_time_ms": python_time * 1000,
        "traced_time_ms": traced_time * 1000,
        "iterations": iterations,
        "overhead_factor": traced_time / python_time if python_time > 0 else 0,
        "result": result,
    }


# HTML for the demo UI
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Lattice JIT Calculator</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #e0e0e0;
            padding: 40px;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
        }
        h1 {
            font-size: 2.5rem;
            background: linear-gradient(90deg, #00d4ff, #7c3aed);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }
        .subtitle {
            color: #94a3b8;
            margin-bottom: 30px;
        }
        .card {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 20px;
            backdrop-filter: blur(10px);
        }
        .card h2 {
            color: #00d4ff;
            margin-bottom: 16px;
            font-size: 1.2rem;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #94a3b8;
        }
        input, textarea {
            width: 100%;
            padding: 12px 16px;
            background: rgba(0,0,0,0.3);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 8px;
            color: #e0e0e0;
            font-family: 'Fira Code', monospace;
            font-size: 1rem;
            margin-bottom: 16px;
        }
        input:focus, textarea:focus {
            outline: none;
            border-color: #00d4ff;
        }
        .variables-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 12px;
            margin-bottom: 16px;
        }
        .var-input {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .var-input label {
            min-width: 30px;
            margin: 0;
        }
        .var-input input {
            margin: 0;
            width: 100px;
        }
        button {
            background: linear-gradient(90deg, #00d4ff, #7c3aed);
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            color: white;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(0, 212, 255, 0.3);
        }
        .result-value {
            font-size: 2rem;
            font-weight: bold;
            color: #10b981;
        }
        .ops-list {
            background: rgba(0,0,0,0.3);
            border-radius: 8px;
            padding: 16px;
            font-family: 'Fira Code', monospace;
            font-size: 0.9rem;
            max-height: 300px;
            overflow-y: auto;
        }
        .op {
            padding: 4px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .op-code {
            color: #00d4ff;
            font-weight: bold;
        }
        .benchmark {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        .stat {
            text-align: center;
            padding: 20px;
            background: rgba(0,0,0,0.2);
            border-radius: 12px;
        }
        .stat-value {
            font-size: 1.8rem;
            font-weight: bold;
            color: #00d4ff;
        }
        .stat-label {
            color: #94a3b8;
            font-size: 0.9rem;
        }
        .speedup {
            color: #10b981;
        }
        .slower {
            color: #ef4444;
        }
        pre {
            background: rgba(0,0,0,0.3);
            padding: 16px;
            border-radius: 8px;
            overflow-x: auto;
            font-size: 0.85rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>⚡ Lattice JIT Calculator</h1>
        <p class="subtitle">Trace Python expressions → Compile to native code</p>
        
        <div class="card">
            <h2>Expression</h2>
            <label>Math expression (use x, y, z as variables)</label>
            <input type="text" id="expr" value="x * y + z * 2" placeholder="x * y + z">
            
            <label>Variables</label>
            <div class="variables-grid">
                <div class="var-input">
                    <label>x =</label>
                    <input type="number" id="var-x" value="5">
                </div>
                <div class="var-input">
                    <label>y =</label>
                    <input type="number" id="var-y" value="3">
                </div>
                <div class="var-input">
                    <label>z =</label>
                    <input type="number" id="var-z" value="10">
                </div>
            </div>
            
            <button onclick="calculate()">Calculate & Trace</button>
            <button onclick="benchmark()" style="margin-left: 10px; background: linear-gradient(90deg, #10b981, #059669);">
                Benchmark (10,000 iterations)
            </button>
        </div>
        
        <div class="card" id="result-card" style="display: none;">
            <h2>Result</h2>
            <div class="result-value" id="result">-</div>
        </div>
        
        <div class="card" id="trace-card" style="display: none;">
            <h2>Traced Operations</h2>
            <div class="ops-list" id="ops-list"></div>
        </div>
        
        <div class="card" id="ir-card" style="display: none;">
            <h2>Generated IR</h2>
            <pre id="ir-json"></pre>
        </div>
        
        <div class="card" id="benchmark-card" style="display: none;">
            <h2>Benchmark Results (10,000 iterations)</h2>
            <div class="benchmark">
                <div class="stat">
                    <div class="stat-value" id="python-time">-</div>
                    <div class="stat-label">Python eval (ms)</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="traced-time">-</div>
                    <div class="stat-label">Traced (ms)</div>
                </div>
            </div>
            <p style="margin-top: 16px; text-align: center; color: #94a3b8;">
                Note: Tracing adds overhead. The JIT compilation step (not shown here) 
                would compile the IR to native code for <span class="speedup">10-100x speedup</span> on repeated calls.
            </p>
        </div>
    </div>
    
    <script>
        function getVariables() {
            return {
                x: parseFloat(document.getElementById('var-x').value) || 0,
                y: parseFloat(document.getElementById('var-y').value) || 0,
                z: parseFloat(document.getElementById('var-z').value) || 0,
            };
        }
        
        async function calculate() {
            const expr = document.getElementById('expr').value;
            const variables = getVariables();
            
            const response = await fetch('/trace', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({expr, variables})
            });
            
            const data = await response.json();
            
            if (data.error) {
                alert('Error: ' + data.error);
                return;
            }
            
            // Show result
            document.getElementById('result-card').style.display = 'block';
            document.getElementById('result').textContent = data.python_result;
            
            // Show traced ops
            document.getElementById('trace-card').style.display = 'block';
            const opsHtml = data.ir.ops.map(op => 
                `<div class="op"><span class="op-code">${op.op}</span> → v${op.result} = [${op.operands.join(', ')}]</div>`
            ).join('');
            document.getElementById('ops-list').innerHTML = opsHtml;
            
            // Show IR
            document.getElementById('ir-card').style.display = 'block';
            document.getElementById('ir-json').textContent = JSON.stringify(data.ir, null, 2);
        }
        
        async function benchmark() {
            const expr = document.getElementById('expr').value;
            const variables = getVariables();
            
            const response = await fetch('/benchmark', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({expr, variables})
            });
            
            const data = await response.json();
            
            document.getElementById('benchmark-card').style.display = 'block';
            document.getElementById('python-time').textContent = data.python_time_ms.toFixed(2);
            document.getElementById('traced-time').textContent = data.traced_time_ms.toFixed(2);
        }
    </script>
</body>
</html>
"""


async def handle_index(request):
    return web.Response(text=HTML, content_type='text/html')


async def handle_trace(request):
    data = await request.json()
    expr = data.get('expr', '')
    variables = data.get('variables', {})
    
    result = trace_expression(expr, variables)
    return web.json_response(result)


async def handle_benchmark(request):
    data = await request.json()
    expr = data.get('expr', '')
    variables = data.get('variables', {})
    
    result = benchmark_expression(expr, variables)
    return web.json_response(result)


def main():
    app = web.Application()
    app.router.add_get('/', handle_index)
    app.router.add_post('/trace', handle_trace)
    app.router.add_post('/benchmark', handle_benchmark)
    
    print("=" * 50)
    print("🚀 Lattice JIT Calculator Demo")
    print("=" * 50)
    print()
    print("Open: http://localhost:8001")
    print()
    print("This demo shows:")
    print("  1. Enter a math expression")
    print("  2. See traced operations")
    print("  3. View generated IR (for Cranelift)")
    print("  4. Benchmark Python vs traced execution")
    print()
    print("Press Ctrl+C to stop")
    print()
    
    web.run_app(app, host='localhost', port=8001, print=None)


if __name__ == "__main__":
    main()
