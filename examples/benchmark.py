"""
Performance Benchmark: Lattice vs Streamlit-style Full Reruns

This benchmark compares:
1. Lattice: Fine-grained reactivity (only recompute what changed)
2. Streamlit-style: Full rerun (recompute everything on every change)

The benchmark creates expensive computations and measures how long
it takes to propagate an update.

Run this benchmark:
    python examples/benchmark.py
"""

import time
import math
from typing import List

from lattice import signal, memo


def expensive_computation(value: int) -> float:
    """Simulate an expensive computation like data processing."""
    result = 0.0
    for i in range(1000):
        result += math.sin(value + i) * math.cos(value - i)
    return result


def benchmark_lattice(num_signals: int, num_updates: int) -> float:
    """
    Benchmark Lattice's fine-grained reactivity.
    
    Creates independent chains where each memo depends on one signal,
    then updates just one signal. Only that signal's dependent recomputes.
    """
    # Create independent signals
    signals = [signal(i) for i in range(num_signals)]
    
    # Create a memo for each signal (independent chains)
    memos = []
    for i, s in enumerate(signals):
        @memo
        def compute(sig=s, idx=i):
            return expensive_computation(sig.value)
        memos.append(compute)
    
    # Force initial computation of all memos
    for m in memos:
        m()
    
    # Benchmark: update just the first signal many times
    start = time.perf_counter()
    for _ in range(num_updates):
        signals[0].value += 1
        memos[0]()  # Only first memo needs to recompute
    end = time.perf_counter()
    
    return end - start


def benchmark_full_rerun(num_computations: int, num_updates: int) -> float:
    """
    Benchmark Streamlit-style full reruns.
    
    Simulates what happens when the entire script reruns on every change.
    All computations are re-executed, even if their inputs didn't change.
    """
    # Simulate state
    values = list(range(num_computations))
    
    def run_all() -> List[float]:
        """Simulate a full Streamlit rerun - all computations execute."""
        return [expensive_computation(v) for v in values]
    
    # Force initial computation
    run_all()
    
    # Benchmark: update one value but rerun everything
    start = time.perf_counter()
    for _ in range(num_updates):
        values[0] += 1
        run_all()  # Full rerun - ALL computations re-execute
    end = time.perf_counter()
    
    return end - start


def main():
    print("=" * 70)
    print("Performance Benchmark: Lattice vs Streamlit-style Full Reruns")
    print("=" * 70)
    print()
    
    # Benchmark parameters
    num_signals = 50  # Number of independent computations
    num_updates = 10  # Number of updates to measure
    
    print(f"Setup:")
    print(f"  - {num_signals} expensive computations (each ~1ms)")
    print(f"  - {num_updates} updates to a single value")
    print(f"  - Measuring total time to propagate updates")
    print()
    
    print("Running benchmarks...")
    print()
    
    # Run Lattice benchmark
    lattice_time = benchmark_lattice(num_signals, num_updates)
    print(f"Lattice (fine-grained):  {lattice_time * 1000:.1f} ms")
    print(f"  -> Only 1 computation runs per update")
    print()
    
    # Run full-rerun benchmark
    rerun_time = benchmark_full_rerun(num_signals, num_updates)
    print(f"Full rerun (Streamlit):  {rerun_time * 1000:.1f} ms")
    print(f"  -> All {num_signals} computations run per update")
    print()
    
    print("-" * 70)
    
    speedup = rerun_time / lattice_time if lattice_time > 0 else float('inf')
    print(f"Result: Lattice is {speedup:.1f}x faster")
    print()
    
    per_update_lattice = (lattice_time / num_updates) * 1000
    per_update_rerun = (rerun_time / num_updates) * 1000
    
    print(f"Per-update latency:")
    print(f"  Lattice:   {per_update_lattice:.1f} ms")
    print(f"  Streamlit: {per_update_rerun:.1f} ms")
    print()
    
    print("Why this matters:")
    print()
    print("  In a real dashboard with 50 charts and data transformations,")
    print("  changing a single filter would:")
    print()
    print(f"    Streamlit: Wait {per_update_rerun:.0f} ms (recompute everything)")
    print(f"    Lattice:   Wait {per_update_lattice:.0f} ms (recompute only affected)")
    print()
    print("  Users perceive <100ms as 'instant'. Lattice keeps you there.")
    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
