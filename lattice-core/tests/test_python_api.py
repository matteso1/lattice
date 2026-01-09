"""
Tests for the Lattice Python API.

These tests verify that signals, memos, and effects work correctly
with automatic dependency tracking.
"""

import pytest


class TestSignal:
    """Tests for the Signal primitive."""
    
    def test_signal_holds_value(self):
        """Signal should store and retrieve values."""
        from lattice import signal
        
        s = signal(42)
        assert s.value == 42
    
    def test_signal_updates_value(self):
        """Signal should update its value."""
        from lattice import signal
        
        s = signal(0)
        s.value = 10
        assert s.value == 10
    
    def test_signal_has_unique_id(self):
        """Each signal should have a unique ID."""
        from lattice import signal
        
        s1 = signal(0)
        s2 = signal(0)
        assert s1.id != s2.id


class TestMemo:
    """Tests for the Memo primitive."""
    
    def test_memo_computes_value(self):
        """Memo should compute its value."""
        from lattice import signal, memo
        
        count = signal(5)
        
        @memo
        def doubled():
            return count.value * 2
        
        assert doubled() == 10
    
    def test_memo_caches_value(self):
        """Memo should cache its result."""
        from lattice import memo
        
        call_count = 0
        
        @memo
        def expensive():
            nonlocal call_count
            call_count += 1
            return 42
        
        # First call computes
        assert expensive() == 42
        assert call_count == 1
        
        # Second call uses cache
        assert expensive() == 42
        assert call_count == 1
    
    def test_memo_recomputes_on_dependency_change(self):
        """Memo should recompute when dependencies change."""
        from lattice import signal, memo
        
        count = signal(0)
        
        @memo
        def doubled():
            return count.value * 2
        
        assert doubled() == 0
        
        count.value = 5
        assert doubled() == 10
        
        count.value = 10
        assert doubled() == 20
    
    def test_memo_tracks_multiple_dependencies(self):
        """Memo should track all dependencies."""
        from lattice import signal, memo
        
        a = signal(2)
        b = signal(3)
        
        @memo
        def product():
            return a.value * b.value
        
        assert product() == 6
        
        a.value = 4
        assert product() == 12
        
        b.value = 5
        assert product() == 20


class TestEffect:
    """Tests for the Effect primitive."""
    
    def test_effect_runs_immediately(self):
        """Effect should run immediately on creation."""
        from lattice import signal, effect
        
        results = []
        count = signal(0)
        
        @effect
        def track():
            results.append(count.value)
        
        assert results == [0]
    
    def test_effect_runs_on_dependency_change(self):
        """Effect should run when dependencies change."""
        from lattice import signal, effect
        
        results = []
        count = signal(0)
        
        @effect
        def track():
            results.append(count.value)
        
        count.value = 1
        count.value = 2
        count.value = 3
        
        assert results == [0, 1, 2, 3]
    
    def test_effect_can_be_disposed(self):
        """Disposed effect should not run."""
        from lattice import signal, effect
        
        results = []
        count = signal(0)
        
        @effect
        def track():
            results.append(count.value)
        
        count.value = 1
        track.dispose()
        count.value = 2
        count.value = 3
        
        # Should only have 0 and 1, not 2 and 3
        assert results == [0, 1]


class TestIntegration:
    """Integration tests for the reactive system."""
    
    def test_memo_chain(self):
        """Memos can depend on other memos."""
        from lattice import signal, memo
        
        base = signal(2)
        
        @memo
        def doubled():
            return base.value * 2
        
        @memo
        def quadrupled():
            return doubled() * 2
        
        assert doubled() == 4
        assert quadrupled() == 8
        
        base.value = 5
        assert doubled() == 10
        assert quadrupled() == 20
    
    def test_effect_with_memo(self):
        """Effects can depend on memos."""
        from lattice import signal, memo, effect
        
        results = []
        count = signal(0)
        
        @memo
        def doubled():
            return count.value * 2
        
        @effect
        def track():
            results.append(doubled())
        
        count.value = 5
        
        assert results == [0, 10]
    
    def test_diamond_dependency(self):
        """Diamond dependencies should work correctly."""
        from lattice import signal, memo
        
        #     base
        #    /    \
        #  left  right
        #    \    /
        #     sum
        
        base = signal(1)
        
        @memo
        def left():
            return base.value + 1
        
        @memo
        def right():
            return base.value + 2
        
        @memo
        def total():
            return left() + right()
        
        assert total() == 5  # (1+1) + (1+2) = 5
        
        base.value = 10
        assert total() == 23  # (10+1) + (10+2) = 23


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
