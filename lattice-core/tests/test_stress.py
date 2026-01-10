"""
Stress and performance tests for Lattice.

These tests verify the framework handles high load correctly.
"""

import pytest
import time


class TestReactiveStress:
    """Stress tests for reactive system."""
    
    def test_rapid_signal_updates(self):
        """Signal should handle 1000 rapid updates."""
        from lattice import signal
        
        s = signal(0)
        
        for i in range(1000):
            s.value = i
        
        assert s.value == 999
    
    def test_rapid_memo_invalidation(self):
        """Memo should handle rapid invalidation."""
        from lattice import signal, memo
        
        count = signal(0)
        compute_count = 0
        
        @memo
        def doubled():
            nonlocal compute_count
            compute_count += 1
            return count.value * 2
        
        # 100 updates, should only compute when accessed
        for i in range(100):
            count.value = i
            doubled()  # Access to trigger recompute
        
        assert doubled() == 198  # 99 * 2
    
    def test_deep_memo_chain(self):
        """Deep memo chains should work."""
        from lattice import signal, memo
        
        base = signal(1)
        
        # Create chain of 10 memos
        @memo
        def m1(): return base.value + 1
        @memo
        def m2(): return m1() + 1
        @memo
        def m3(): return m2() + 1
        @memo
        def m4(): return m3() + 1
        @memo
        def m5(): return m4() + 1
        @memo
        def m6(): return m5() + 1
        @memo
        def m7(): return m6() + 1
        @memo
        def m8(): return m7() + 1
        @memo
        def m9(): return m8() + 1
        @memo
        def m10(): return m9() + 1
        
        assert m10() == 11  # 1 + 10
        
        base.value = 100
        assert m10() == 110  # 100 + 10
    
    def test_many_signals(self):
        """System should handle many signals."""
        from lattice import signal
        
        signals = [signal(i) for i in range(100)]
        
        for i, s in enumerate(signals):
            assert s.value == i
            s.value = i * 2
            assert s.value == i * 2
    
    def test_many_effects(self):
        """System should handle many effects."""
        from lattice import signal, effect
        
        count = signal(0)
        results = []
        
        # Create 50 effects
        effects = []
        for i in range(50):
            @effect
            def track(idx=i):
                results.append((idx, count.value))
            effects.append(track)
        
        count.value = 1
        
        # Should have 50 initial + 50 updates = 100
        assert len(results) == 100


class TestEffectDisposal:
    """Tests for proper cleanup."""
    
    def test_disposed_effect_stops(self):
        """Disposed effect should not fire."""
        from lattice import signal, effect
        
        count = signal(0)
        calls = []
        
        @effect
        def track():
            calls.append(count.value)
        
        count.value = 1
        track.dispose()
        count.value = 2
        count.value = 3
        
        assert calls == [0, 1]  # Only before dispose


class TestVNodeStress:
    """Stress tests for VNode system."""
    
    def test_deep_nesting(self):
        """VNode should handle deep nesting."""
        from lattice.component import div
        
        # 20 levels deep
        node = div("deep")
        for _ in range(20):
            node = div(node)
        
        # Should not crash
        assert node.tag == "div"
    
    def test_many_children(self):
        """VNode should handle many children."""
        from lattice.component import div, p
        
        children = [p(f"Child {i}") for i in range(100)]
        parent = div(*children)
        
        assert len(parent.children) == 100
    
    def test_many_attributes(self):
        """VNode should handle many attributes."""
        from lattice.component import div
        
        attrs = {f"data-attr-{i}": f"value-{i}" for i in range(50)}
        node = div("Content", **attrs)
        
        assert len(node.attrs) == 50


class TestDiffStress:
    """Stress tests for diff algorithm."""
    
    def test_large_tree_diff(self):
        """Diff should handle large trees."""
        from lattice.component import div, p
        from lattice.diff import diff
        
        old = div(*[p(f"Item {i}") for i in range(100)])
        new = div(*[p(f"Item {i}") for i in range(100)])
        
        patches = diff(old, new)
        
        # Identical trees should have no patches
        assert len(patches) == 0
    
    def test_partial_update_diff(self):
        """Diff should minimize patches for partial updates."""
        from lattice.component import div, p
        from lattice.diff import diff
        
        old = div(*[p(f"Item {i}") for i in range(100)])
        # Only change one item
        children = [p(f"Item {i}") for i in range(100)]
        children[50] = p("CHANGED")
        new = div(*children)
        
        patches = diff(old, new)
        
        # Should only patch one item
        assert len(patches) <= 2  # At most TEXT + UPDATE


class TestTracerStress:
    """Stress tests for JIT tracer."""
    
    def test_long_expression(self):
        """Tracer should handle long expressions."""
        from lattice.tracer import trace, TracedValue
        
        with trace() as ctx:
            x = TracedValue(1.0, "x")
            result = x
            for i in range(50):
                result = result + 1
            ctx.set_output(result)
        
        assert result.value == 51.0
    
    def test_many_inputs(self):
        """Tracer should handle many inputs."""
        from lattice.tracer import trace, TracedValue
        
        with trace() as ctx:
            values = [TracedValue(float(i), f"v{i}") for i in range(20)]
            result = values[0]
            for v in values[1:]:
                result = result + v
            ctx.set_output(result)
        
        # Sum of 0 to 19
        assert result.value == sum(range(20))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
