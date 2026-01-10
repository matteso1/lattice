"""
Lattice Stress Test - 1000+ Signals

Push the reactive system to its limits:
- 1000+ signals updating simultaneously
- Derived memos recalculating
- Find the breaking point

Run: python examples/stress_test.py
"""

import sys
import time
sys.path.insert(0, "python")

from lattice import signal, memo, effect


def test_signal_scaling():
    """Test how many signals we can handle."""
    print("=" * 60)
    print("🔥 Lattice Stress Test - Signal Scaling")
    print("=" * 60)
    print()
    
    for num_signals in [100, 500, 1000, 2000, 5000, 10000]:
        # Create signals
        start = time.perf_counter()
        signals = [signal(i) for i in range(num_signals)]
        create_time = time.perf_counter() - start
        
        # Update all signals once
        start = time.perf_counter()
        for i, s in enumerate(signals):
            s.value = i * 2
        update_time = time.perf_counter() - start
        
        # Create a memo that depends on first 100 signals
        @memo
        def sum_first_100():
            return sum(signals[i].value for i in range(min(100, num_signals)))
        
        # Time memo access
        start = time.perf_counter()
        result = sum_first_100()
        memo_time = time.perf_counter() - start
        
        # Time memo with cache hit
        start = time.perf_counter()
        result2 = sum_first_100()
        cache_time = time.perf_counter() - start
        
        print(f"[{num_signals:6,} signals]")
        print(f"  Create: {create_time*1000:8.2f} ms")
        print(f"  Update: {update_time*1000:8.2f} ms ({update_time*1000/num_signals:.3f} ms/signal)")
        print(f"  Memo:   {memo_time*1000:8.2f} ms")
        print(f"  Cache:  {cache_time*1000:8.4f} ms (should be ~0)")
        print()
        
        # Cleanup
        del signals
        del sum_first_100


def test_rapid_updates():
    """Test rapid updates to same signal."""
    print("=" * 60)
    print("⚡ Lattice Stress Test - Rapid Updates")
    print("=" * 60)
    print()
    
    for num_updates in [1000, 10000, 100000, 1000000]:
        s = signal(0)
        
        # Create effect that counts
        effect_count = [0]
        @effect
        def count_effect():
            _ = s.value
            effect_count[0] += 1
        
        # Rapid updates
        start = time.perf_counter()
        for i in range(num_updates):
            s.value = i
        elapsed = time.perf_counter() - start
        
        print(f"[{num_updates:10,} updates]")
        print(f"  Time:     {elapsed*1000:10.2f} ms")
        print(f"  Rate:     {num_updates/elapsed:,.0f} updates/sec")
        print(f"  Effects:  {effect_count[0]:,} calls")
        print()
        
        count_effect.dispose()


def test_memo_chain():
    """Test deep memo chains."""
    print("=" * 60)
    print("🔗 Lattice Stress Test - Deep Memo Chains")
    print("=" * 60)
    print()
    
    for chain_depth in [5, 10, 20, 50, 100]:
        base = signal(1)
        
        # Build chain dynamically
        memos = []
        
        @memo
        def m0():
            return base.value + 1
        memos.append(m0)
        
        for i in range(1, chain_depth):
            prev = memos[-1]
            @memo
            def m(prev=prev, i=i):
                return prev() + 1
            memos.append(m)
        
        # Time chain traversal
        start = time.perf_counter()
        result = memos[-1]()
        chain_time = time.perf_counter() - start
        
        # Time with cache
        start = time.perf_counter()
        result2 = memos[-1]()
        cache_time = time.perf_counter() - start
        
        # Invalidate and recompute
        base.value = 2
        start = time.perf_counter()
        result3 = memos[-1]()
        recompute_time = time.perf_counter() - start
        
        print(f"[{chain_depth:3} deep chain]")
        print(f"  Initial: {chain_time*1000:8.2f} ms (result: {result})")
        print(f"  Cache:   {cache_time*1000:8.4f} ms")
        print(f"  Recomp:  {recompute_time*1000:8.2f} ms (result: {result3})")
        print()


def test_many_effects():
    """Test many effects on same signal."""
    print("=" * 60)
    print("👀 Lattice Stress Test - Many Effects")
    print("=" * 60)
    print()
    
    for num_effects in [10, 50, 100, 500, 1000]:
        s = signal(0)
        effect_calls = [0]
        effects = []
        
        # Create many effects
        for i in range(num_effects):
            @effect
            def e(i=i):
                _ = s.value
                effect_calls[0] += 1
            effects.append(e)
        
        initial_calls = effect_calls[0]
        
        # Update signal
        start = time.perf_counter()
        s.value = 1
        elapsed = time.perf_counter() - start
        
        calls_per_update = effect_calls[0] - initial_calls
        
        print(f"[{num_effects:4} effects]")
        print(f"  Update time: {elapsed*1000:8.2f} ms")
        print(f"  Calls:       {calls_per_update}")
        print()
        
        # Cleanup
        for e in effects:
            e.dispose()


def main():
    test_signal_scaling()
    test_rapid_updates()
    test_memo_chain()
    test_many_effects()
    
    print("=" * 60)
    print("✅ Stress tests complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
