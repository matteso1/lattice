"""
Tests for Lattice CRDT Collaboration System (Phase 3).

These tests verify Room, CollaborativeSignal, and sync functionality.
"""

import pytest


class TestRoom:
    """Tests for collaborative Room."""
    
    def test_room_creation(self):
        """Room should be created with ID."""
        from lattice.collab import Room
        
        room = Room("test-room")
        
        assert room.room_id == "test-room"
        assert not room.connected
    
    def test_room_creates_signals(self):
        """Room should create collaborative signals."""
        from lattice.collab import Room
        
        room = Room("test-room")
        signal = room.get_signal("count", 0)
        
        assert signal.value == 0
    
    def test_room_reuses_signals(self):
        """Same key should return same signal."""
        from lattice.collab import Room
        
        room = Room("test-room")
        s1 = room.get_signal("count", 0)
        s2 = room.get_signal("count", 0)
        
        assert s1 is s2


class TestCollaborativeSignal:
    """Tests for CollaborativeSignal."""
    
    def test_signal_holds_value(self):
        """CollaborativeSignal should store value."""
        from lattice.collab import Room, collaborative_signal
        
        room = Room("test-room")
        count = collaborative_signal(room, "count", 42)
        
        assert count.value == 42
    
    def test_signal_updates_value(self):
        """CollaborativeSignal should update value."""
        from lattice.collab import Room, collaborative_signal
        
        room = Room("test-room")
        count = collaborative_signal(room, "count", 0)
        
        count.value = 10
        assert count.value == 10
    
    def test_signal_notifies_dependents(self):
        """CollaborativeSignal should notify on change."""
        from lattice.collab import Room, collaborative_signal
        
        room = Room("test-room")
        count = collaborative_signal(room, "count", 0)
        
        notifications = []
        
        class MockDependent:
            def _on_dependency_changed(self):
                notifications.append(count.value)
        
        count._subscribe(MockDependent())
        count.value = 1
        count.value = 2
        
        assert notifications == [1, 2]


class TestCRDTSync:
    """Tests for CRDT synchronization between rooms."""
    
    def test_sync_updates_value(self):
        """Sync should update values between rooms."""
        from lattice.collab import Room, collaborative_signal
        
        # Two rooms simulating two clients
        room1 = Room("shared-room")
        room2 = Room("shared-room")
        
        # Create signal in room1 and set value
        count1 = collaborative_signal(room1, "count", 0)
        count1.value = 42
        
        # Sync room1 -> room2 BEFORE creating signal in room2
        update = room1.get_update()
        room2.apply_update(update)
        
        # Now create signal in room2 - should have synced value
        count2 = collaborative_signal(room2, "count", 0)
        
        # room2 should have the value (pycrdt uses float)
        assert count2.value == 42.0
    
    def test_sync_multiple_signals(self):
        """Multiple signals should sync correctly."""
        from lattice.collab import Room, collaborative_signal
        
        room1 = Room("shared-room")
        room2 = Room("shared-room")
        
        a1 = collaborative_signal(room1, "a", 0)
        b1 = collaborative_signal(room1, "b", 0)
        
        a2 = collaborative_signal(room2, "a", 0)
        b2 = collaborative_signal(room2, "b", 0)
        
        # Update room1
        a1.value = 10
        b1.value = 20
        
        # Sync
        room2.apply_update(room1.get_update())
        
        assert a2.value == 10.0
        assert b2.value == 20.0
    
    def test_sync_bidirectional(self):
        """Sync should work in both directions."""
        from lattice.collab import Room, collaborative_signal
        
        room1 = Room("shared-room")
        room2 = Room("shared-room")
        
        # Create signal in room1
        count1 = collaborative_signal(room1, "count", 0)
        count1.value = 5
        
        # Sync to room2 and create signal there
        room2.apply_update(room1.get_update())
        count2 = collaborative_signal(room2, "count", 0)
        
        assert count2.value == 5.0
        
        # Room2 updates
        count2.value = 10
        room1.apply_update(room2.get_update())
        assert count1.value == 10.0


class TestCRDTTypes:
    """Tests for different data types in CRDT."""
    
    def test_integer_values(self):
        """Integer values should sync."""
        from lattice.collab import Room, collaborative_signal
        
        room = Room("test")
        count = collaborative_signal(room, "count", 42)
        
        assert count.value == 42
    
    def test_float_values(self):
        """Float values should sync."""
        from lattice.collab import Room, collaborative_signal
        
        room = Room("test")
        price = collaborative_signal(room, "price", 19.99)
        
        assert price.value == 19.99
    
    def test_string_values(self):
        """String values should sync."""
        from lattice.collab import Room, collaborative_signal
        
        room = Room("test")
        name = collaborative_signal(room, "name", "Lattice")
        
        assert name.value == "Lattice"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
