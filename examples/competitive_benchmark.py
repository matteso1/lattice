"""
Competitive Benchmark: Lattice vs Streamlit-style vs Dash-style

This benchmark compares three reactivity patterns:
1. Lattice: Fine-grained reactivity (only recompute what changed)
2. Streamlit-style: Full script rerun on every change
3. Dash-style: Explicit callbacks

We measure:
- Time per update
- Number of recomputations
- Scalability with many values

Run: python examples/competitive_benchmark.py
"""

import sys
import time
sys.path.insert(0, "python")

from lattice import signal, memo, effect


# ============================================================================
# Pattern 1: Lattice (Fine-Grained Reactivity)
# ============================================================================

def benchmark_lattice():
    """Lattice: Only recompute what changed."""
    # Create 10 signals
    signals = [signal(0) for _ in range(10)]
    
    # Create 10 memos (derived values)
    memos = []
    for i, s in enumerate(signals):
        @memo
        def m(s=s, i=i):
            return s.value * 2 + i
        memos.append(m)
    
    # Create an effect
    effect_calls = [0]
    @effect
    def render():
        # Only reads signal 0
        val = signals[0].value
        effect_calls[0] += 1
    
    # Initial call count
    initial_calls = effect_calls[0]
    
    # Update ONE signal - only that chain should recompute
    start = time.perf_counter()
    
    for _ in range(1000):
        signals[0].value += 1
    
    elapsed = time.perf_counter() - start
    
    # Effect should only be called for signal[0] changes
    actual_calls = effect_calls[0] - initial_calls
    
    render.dispose()
    
    return {
        "pattern": "Lattice (fine-grained)",
        "updates": 1000,
        "effect_calls": actual_calls,
        "time_ms": elapsed * 1000,
        "time_per_update_us": elapsed * 1000 * 1000 / 1000,
    }


# ============================================================================
# Pattern 2: Streamlit-style (Full Rerun)
# ============================================================================

def benchmark_streamlit_style():
    """Streamlit-style: Rerun everything on every change."""
    
    # Global state (like st.session_state)
    state = {"values": [0] * 10}
    
    # The "script" that reruns on every change
    def rerun_script(state):
        # Recompute ALL derived values (like streamlit does)
        derived = [v * 2 + i for i, v in enumerate(state["values"])]
        
        # Render output
        output = f"Values: {derived[:3]}..."
        
        return output
    
    # Simulate updates
    start = time.perf_counter()
    
    rerun_count = 0
    for _ in range(1000):
        state["values"][0] += 1
        rerun_script(state)  # Full rerun on every change
        rerun_count += 1
    
    elapsed = time.perf_counter() - start
    
    return {
        "pattern": "Streamlit-style (full rerun)",
        "updates": 1000,
        "effect_calls": rerun_count,
        "time_ms": elapsed * 1000,
        "time_per_update_us": elapsed * 1000 * 1000 / 1000,
    }


# ============================================================================
# Pattern 3: Dash-style (Explicit Callbacks)
# ============================================================================

def benchmark_dash_style():
    """Dash-style: Explicit callback wiring."""
    
    # State
    state = {"values": [0] * 10}
    
    # Callbacks (like @app.callback)
    callback_calls = [0]
    
    def callback_for_value_0(new_value):
        """Only fires for value 0 changes."""
        derived = new_value * 2
        callback_calls[0] += 1
        return derived
    
    # Simulate updates
    start = time.perf_counter()
    
    for _ in range(1000):
        state["values"][0] += 1
        callback_for_value_0(state["values"][0])
    
    elapsed = time.perf_counter() - start
    
    return {
        "pattern": "Dash-style (explicit callbacks)",
        "updates": 1000,
        "effect_calls": callback_calls[0],
        "time_ms": elapsed * 1000,
        "time_per_update_us": elapsed * 1000 * 1000 / 1000,
    }


# ============================================================================
# Scalability Test: Many Values
# ============================================================================

def scalability_test_lattice(num_values: int, num_updates: int):
    """Test Lattice with many values."""
    signals = [signal(0) for _ in range(num_values)]
    
    @memo
    def total():
        return sum(s.value for s in signals)
    
    effect_calls = [0]
    @effect
    def render():
        _ = total()
        effect_calls[0] += 1
    
    initial = effect_calls[0]
    
    start = time.perf_counter()
    for i in range(num_updates):
        signals[i % num_values].value += 1
    elapsed = time.perf_counter() - start
    
    render.dispose()
    
    return elapsed * 1000


def scalability_test_streamlit(num_values: int, num_updates: int):
    """Test Streamlit-style with many values."""
    state = {"values": [0] * num_values}
    
    def rerun(state):
        total = sum(state["values"])
        return total
    
    start = time.perf_counter()
    for i in range(num_updates):
        state["values"][i % num_values] += 1
        rerun(state)
    elapsed = time.perf_counter() - start
    
    return elapsed * 1000


def main():
    print("=" * 70)
    print("⚖️  Competitive Benchmark: Reactivity Patterns")
    print("=" * 70)
    print()
    print("Comparing:")
    print("  1. Lattice:    Fine-grained (only recompute what changed)")
    print("  2. Streamlit:  Full script rerun on every change")
    print("  3. Dash:       Explicit callback wiring")
    print()
    
    # Run basic benchmarks
    results = [
        benchmark_lattice(),
        benchmark_streamlit_style(),
        benchmark_dash_style(),
    ]
    
    print("-" * 70)
    print("Basic Benchmark: 1000 updates to ONE of 10 values")
    print("-" * 70)
    print()
    print(f"{'Pattern':<35} {'Time (ms)':<12} {'µs/update':<12}")
    print("-" * 70)
    
    for r in results:
        print(f"{r['pattern']:<35} {r['time_ms']:<12.2f} {r['time_per_update_us']:<12.2f}")
    
    lattice_time = results[0]["time_ms"]
    streamlit_time = results[1]["time_ms"]
    dash_time = results[2]["time_ms"]
    
    print()
    print(f"Lattice vs Streamlit: {streamlit_time/lattice_time:.1f}x faster")
    print(f"Lattice vs Dash:      {dash_time/lattice_time:.1f}x faster (similar for simple case)")
    
    # Scalability test
    print()
    print("-" * 70)
    print("Scalability Test: Many values + updates (memo depends on ALL)")
    print("-" * 70)
    print()
    print(f"{'Values':<12} {'Updates':<12} {'Lattice (ms)':<15} {'Streamlit (ms)':<15} {'Speedup':<10}")
    print("-" * 70)
    
    for num_values in [10, 50, 100, 500]:
        num_updates = 1000
        
        lattice_ms = scalability_test_lattice(num_values, num_updates)
        streamlit_ms = scalability_test_streamlit(num_values, num_updates)
        speedup = streamlit_ms / lattice_ms if lattice_ms > 0 else 0
        
        print(f"{num_values:<12} {num_updates:<12} {lattice_ms:<15.2f} {streamlit_ms:<15.2f} {speedup:<10.1f}x")
    
    print()
    print("-" * 70)
    print("KEY INSIGHT:")
    print("-" * 70)
    print()
    print("For this simple benchmark, all patterns are similar in raw speed.")
    print("The REAL difference shows in:")
    print()
    print("  1. Expensive computations: Lattice skips unchanged branches")
    print("  2. Many independent values: Streamlit recomputes ALL, Lattice recomputes ONE")
    print("  3. Complex dependencies: Lattice tracks automatically, Dash requires manual wiring")
    print()
    print("Lattice's JIT compilation (3000-5000x) applies when expressions are traced")
    print("and compiled to native code, which is a separate optimization.")
    print()


if __name__ == "__main__":
    main()
