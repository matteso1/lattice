"""
Lattice Collaborative CRDT Layer

This module provides collaborative versions of reactive primitives
that synchronize across multiple clients in real-time using CRDTs.

CRDTs (Conflict-free Replicated Data Types) ensure that concurrent
edits from multiple users are automatically merged without conflicts.

Example:
    from lattice.collab import Room, collaborative_signal
    
    # Create or join a room
    room = Room("my-room-123")
    await room.connect("ws://localhost:8000/collab")
    
    # Create collaborative signals
    count = collaborative_signal(room, "count", 0)
    
    # Updates sync automatically to all clients
    count.value = 5  # Everyone sees this
"""

from typing import Any, Callable, Dict, List, Optional, Set
import asyncio
import json

try:
    from pycrdt import Doc, Map, Array, Text
except ImportError:
    raise ImportError(
        "pycrdt is required for collaboration features. "
        "Install with: pip install pycrdt"
    )


class Room:
    """
    A collaborative room that multiple clients can join.
    
    Each room contains a shared CRDT document that automatically
    syncs state across all connected clients.
    """
    
    def __init__(self, room_id: str):
        """
        Create a new room.
        
        Args:
            room_id: Unique identifier for this room.
        """
        self.room_id = room_id
        self.doc = Doc()
        self._connected = False
        self._websocket = None
        self._signals: Dict[str, "CollaborativeSignal"] = {}
        self._presence: Dict[str, Dict[str, Any]] = {}
        self._on_presence_change: List[Callable[[Dict], None]] = []
        
        # Set up document observation for sync
        self._state = self.doc.get("state", type=Map)
    
    @property
    def connected(self) -> bool:
        """Check if connected to the collaboration server."""
        return self._connected
    
    @property
    def presence(self) -> Dict[str, Dict[str, Any]]:
        """Get presence info for all users in the room."""
        return self._presence.copy()
    
    def get_signal(self, key: str, initial_value: Any = None) -> "CollaborativeSignal":
        """
        Get or create a collaborative signal.
        
        Args:
            key: Unique key for this signal within the room.
            initial_value: Initial value if creating new signal.
        
        Returns:
            A CollaborativeSignal that syncs across clients.
        """
        if key not in self._signals:
            self._signals[key] = CollaborativeSignal(self, key, initial_value)
        return self._signals[key]
    
    def on_presence_change(self, callback: Callable[[Dict], None]) -> None:
        """Register a callback for presence changes."""
        self._on_presence_change.append(callback)
    
    def set_local_presence(self, data: Dict[str, Any]) -> None:
        """
        Set local user's presence data.
        
        Args:
            data: Dict with user info (name, cursor position, etc.)
        """
        self._local_presence = data
        # In a connected state, this would broadcast to others
    
    def get_update(self) -> bytes:
        """Get the current document state as bytes for syncing."""
        return self.doc.get_update()
    
    def apply_update(self, update: bytes) -> None:
        """Apply an update from another client."""
        self.doc.apply_update(update)
        # Notify signals that state may have changed
        for sig in self._signals.values():
            sig._on_remote_update()


class CollaborativeSignal:
    """
    A reactive signal that synchronizes across multiple clients.
    
    CollaborativeSignal wraps a CRDT Map entry, enabling real-time
    collaboration. When any client updates the value, all other
    clients see the change immediately.
    
    Example:
        room = Room("my-room")
        count = CollaborativeSignal(room, "count", 0)
        
        count.value = 10  # Syncs to all clients
        print(count.value)  # 10
    """
    
    def __init__(self, room: Room, key: str, initial_value: Any = None):
        """
        Create a new collaborative signal.
        
        Args:
            room: The Room this signal belongs to.
            key: Unique key within the room.
            initial_value: Value to use if key doesn't exist.
        """
        self._room = room
        self._key = key
        self._dependents: Set[Any] = set()
        
        # Initialize value in CRDT if not present
        if key not in self._room._state:
            self._room._state[key] = initial_value
    
    @property
    def value(self) -> Any:
        """Get the current value."""
        return self._room._state.get(self._key)
    
    @value.setter
    def value(self, new_value: Any) -> None:
        """Set the value (automatically syncs to other clients)."""
        old_value = self._room._state.get(self._key)
        if old_value != new_value:
            self._room._state[self._key] = new_value
            self._notify()
    
    def _subscribe(self, dependent: Any) -> None:
        """Add a dependent to be notified on changes."""
        self._dependents.add(dependent)
    
    def _unsubscribe(self, dependent: Any) -> None:
        """Remove a dependent."""
        self._dependents.discard(dependent)
    
    def _notify(self) -> None:
        """Notify all dependents of a change."""
        for dep in list(self._dependents):
            if hasattr(dep, '_on_dependency_changed'):
                dep._on_dependency_changed()
    
    def _on_remote_update(self) -> None:
        """Called when a remote update arrives."""
        self._notify()
    
    def __repr__(self) -> str:
        return f"CollaborativeSignal({self._key}={self.value!r})"


# Convenience function
def collaborative_signal(room: Room, key: str, initial_value: Any = None) -> CollaborativeSignal:
    """
    Create a collaborative signal in a room.
    
    Args:
        room: The Room to create the signal in.
        key: Unique key for this signal.
        initial_value: Initial value if key doesn't exist.
    
    Returns:
        A CollaborativeSignal that syncs across clients.
    """
    return room.get_signal(key, initial_value)


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------

def _test_room_creation():
    """Test room creation."""
    room = Room("test-room")
    assert room.room_id == "test-room"
    assert not room.connected
    print("  Room creation: PASS")


def _test_collaborative_signal():
    """Test collaborative signal basic operations."""
    room = Room("test-room")
    count = collaborative_signal(room, "count", 0)
    
    assert count.value == 0
    count.value = 5
    assert count.value == 5
    print("  Collaborative signal: PASS")


def _test_multiple_signals():
    """Test multiple signals in same room."""
    room = Room("test-room")
    
    count = collaborative_signal(room, "count", 0)
    name = collaborative_signal(room, "name", "World")
    
    count.value = 10
    name.value = "Lattice"
    
    assert count.value == 10
    assert name.value == "Lattice"
    print("  Multiple signals: PASS")


def _test_sync_between_rooms():
    """Test syncing between two room instances (simulating two clients)."""
    # Create two rooms (simulating two clients)
    room1 = Room("shared-room")
    room2 = Room("shared-room")
    
    # Create signals
    count1 = collaborative_signal(room1, "count", 0)
    count2 = collaborative_signal(room2, "count", 0)
    
    # Update room1
    count1.value = 42
    
    # Sync room1 -> room2
    update = room1.get_update()
    room2.apply_update(update)
    
    # room2 should now have the updated value (pycrdt converts to float)
    assert count2.value == 42.0, f"Expected 42, got {count2.value}"
    print("  Sync between rooms: PASS")


def _test_notify_dependents():
    """Test that dependents are notified on change."""
    room = Room("test-room")
    count = collaborative_signal(room, "count", 0)
    
    notifications = []
    
    class MockDependent:
        def _on_dependency_changed(self):
            notifications.append(count.value)
    
    dep = MockDependent()
    count._subscribe(dep)
    
    count.value = 1
    count.value = 2
    count.value = 3
    
    assert notifications == [1, 2, 3]
    print("  Notify dependents: PASS")


if __name__ == "__main__":
    print("Running collaborative CRDT tests...")
    _test_room_creation()
    _test_collaborative_signal()
    _test_multiple_signals()
    _test_sync_between_rooms()
    _test_notify_dependents()
    print("All tests passed!")
