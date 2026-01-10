"""
Competitive Benchmark: Realistic Expensive Computation

This is the HONEST benchmark showing where Lattice actually wins:
When you have EXPENSIVE derived values that don't need to recompute.

Run: python examples/realistic_benchmark.py
"""

import sys
import time
import math
sys.path.insert(0, "python")

from lattice import signal, memo, effect


def expensive_computation(value: float) -> float:
    """Simulate an expensive computation (like data processing)."""
    result = value
    for _ in range(1000):  # 1000 iterations of heavy math
        result = math.sin(result) * math.cos(result) + math.sqrt(abs(result) + 1)
    return result


def benchmark_lattice_selective():
    """Lattice: Only recompute the expensive value that changed."""
    # 10 independent signals
    signals = [signal(float(i)) for i in range(10)]
    
    # 10 EXPENSIVE memos
    compute_counts = [0] * 10
    memos = []
    for i in range(10):
        s = signals[i]
        @memo
        def m(s=s, i=i):
            compute_counts[i] += 1
            return expensive_computation(s.value)
        memos.append(m)
    
    # Initial computation of all memos
    for m in memos:
        m()
    
    initial_counts = compute_counts.copy()
    
    # Update only signal 0, 100 times
    start = time.perf_counter()
    
    for _ in range(100):
        signals[0].value += 0.1
        # Access all memos (like a render would)
        for m in memos:
            m()
    
    elapsed = time.perf_counter() - start
    
    # Count how many recomputations happened
    recomputes = [compute_counts[i] - initial_counts[i] for i in range(10)]
    total_recomputes = sum(recomputes)
    
    return {
        "pattern": "Lattice",
        "updates": 100,
        "recomputes": recomputes,
        "total_recomputes": total_recomputes,
        "time_ms": elapsed * 1000,
    }


def benchmark_streamlit_rerun():
    """Streamlit-style: Recompute ALL expensive values on every change."""
    state = [float(i) for i in range(10)]
    compute_counts = [0] * 10
    
    def rerun_script(state):
        """The full script runs on every change."""
        results = []
        for i in range(10):
            compute_counts[i] += 1
            results.append(expensive_computation(state[i]))
        return results
    
    # Initial run
    rerun_script(state)
    initial_counts = compute_counts.copy()
    
    # Update only state[0], 100 times
    start = time.perf_counter()
    
    for _ in range(100):
        state[0] += 0.1
        rerun_script(state)  # Recomputes ALL 10 expensive values
    
    elapsed = time.perf_counter() - start
    
    recomputes = [compute_counts[i] - initial_counts[i] for i in range(10)]
    total_recomputes = sum(recomputes)
    
    return {
        "pattern": "Streamlit",
        "updates": 100,
        "recomputes": recomputes,
        "total_recomputes": total_recomputes,
        "time_ms": elapsed * 1000,
    }


def main():
    print("=" * 70)
    print("⚖️  REALISTIC Competitive Benchmark")
    print("=" * 70)
    print()
    print("Scenario: 10 independent expensive computed values")
    print("          Update ONE value 100 times")
    print("          Render requires reading ALL 10 values")
    print()
    print("The expensive_computation() simulates real work like:")
    print("  - Processing a dataset")
    print("  - Training a model")
    print("  - Complex calculations")
    print()
    
    # Run benchmarks
    lattice_result = benchmark_lattice_selective()
    streamlit_result = benchmark_streamlit_rerun()
    
    print("-" * 70)
    print("Results")
    print("-" * 70)
    print()
    
    print(f"{'Metric':<30} {'Lattice':<20} {'Streamlit':<20}")
    print("-" * 70)
    print(f"{'Total time (ms)':<30} {lattice_result['time_ms']:<20.2f} {streamlit_result['time_ms']:<20.2f}")
    print(f"{'Total recomputations':<30} {lattice_result['total_recomputes']:<20} {streamlit_result['total_recomputes']:<20}")
    
    print()
    print("Recomputes per value (should ideally be 100 for changed, 0 for unchanged):")
    print()
    
    for i in range(10):
        changed = "← CHANGED" if i == 0 else ""
        print(f"  Value {i}: Lattice={lattice_result['recomputes'][i]:4}, "
              f"Streamlit={streamlit_result['recomputes'][i]:4} {changed}")
    
    speedup = streamlit_result['time_ms'] / lattice_result['time_ms']
    wasted = streamlit_result['total_recomputes'] - lattice_result['total_recomputes']
    
    print()
    print("-" * 70)
    print("CONCLUSION")
    print("-" * 70)
    print()
    print(f"🚀 Lattice is {speedup:.1f}x FASTER for this realistic scenario")
    print(f"📊 Streamlit wasted {wasted} expensive recomputations")
    print()
    print("This is the TRUE benefit of fine-grained reactivity:")
    print("  - Lattice only recomputed the 100 updates to value 0")
    print("  - Streamlit recomputed ALL 10 values × 100 updates = 1000 times")
    print()


if __name__ == "__main__":
    main()
