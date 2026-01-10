"""
Lattice CRDT Load Test - Multi-Tab Sync

Test CRDT synchronization under heavy load:
- 10+ simulated clients
- Concurrent updates
- Conflict resolution

Run: python examples/crdt_load_test.py
"""

import sys
import time
import random
import threading
sys.path.insert(0, "python")

from lattice.collab import Room, collaborative_signal


def test_many_rooms_sync():
    """Test syncing many rooms with updates."""
    print("=" * 60)
    print("🌐 CRDT Load Test - Multi-Room Sync")
    print("=" * 60)
    print()
    
    num_rooms = 10
    updates_per_room = 100
    
    # Create 10 rooms (simulating 10 browser tabs)
    rooms = [Room(f"load-test") for _ in range(num_rooms)]
    
    # Create a collaborative signal in each room
    signals = []
    for i, room in enumerate(rooms):
        sig = collaborative_signal(room, "counter", 0)
        signals.append(sig)
    
    print(f"Created {num_rooms} rooms with collaborative signals")
    
    # Sync all rooms to start
    print("Initial sync...")
    for i in range(1, num_rooms):
        rooms[i].apply_update(rooms[0].get_update())
    
    # Now perform concurrent-ish updates
    print(f"\nPerforming {updates_per_room} updates per room...")
    
    start = time.perf_counter()
    
    for update_num in range(updates_per_room):
        # Each room makes an update
        for i, sig in enumerate(signals):
            sig.value = update_num * 100 + i
        
        # Sync updates (all-to-all convergence)
        for i in range(num_rooms):
            for j in range(num_rooms):
                if i != j:
                    update = rooms[i].get_update()
                    if update:  # Only apply if there's an update
                        rooms[j].apply_update(update)
    
    elapsed = time.perf_counter() - start
    
    print(f"\n✅ {num_rooms * updates_per_room:,} updates completed in {elapsed*1000:.2f} ms")
    print(f"   Rate: {num_rooms * updates_per_room / elapsed:,.0f} updates/sec")
    
    # Verify convergence
    print("\nVerifying convergence...")
    final_values = [sig.value for sig in signals]
    if len(set(final_values)) == 1:
        print(f"✅ All {num_rooms} rooms converged to value: {final_values[0]}")
    else:
        print(f"⚠️  Values differ: {final_values[:5]}...")
    
    print()


def test_high_frequency_updates():
    """Test high-frequency updates between two rooms."""
    print("=" * 60)
    print("⚡ CRDT Load Test - High Frequency Updates")
    print("=" * 60)
    print()
    
    room1 = Room("hf-test")
    room2 = Room("hf-test")
    
    counter1 = collaborative_signal(room1, "counter", 0)
    
    # Sync room2
    room2.apply_update(room1.get_update())
    counter2 = collaborative_signal(room2, "counter", 0)
    
    num_updates = 1000
    
    print(f"Alternating updates between 2 rooms, {num_updates} each...")
    
    start = time.perf_counter()
    
    for i in range(num_updates):
        # Room 1 updates
        counter1.value = i * 2
        room2.apply_update(room1.get_update())
        
        # Room 2 updates
        counter2.value = i * 2 + 1
        room1.apply_update(room2.get_update())
    
    elapsed = time.perf_counter() - start
    
    print(f"\n✅ {num_updates * 2:,} updates + syncs in {elapsed*1000:.2f} ms")
    print(f"   Rate: {num_updates * 2 / elapsed:,.0f} sync ops/sec")
    print(f"   Final: room1={counter1.value}, room2={counter2.value}")
    print()


def test_concurrent_increments():
    """Test concurrent increments (potential conflicts)."""
    print("=" * 60)
    print("🔄 CRDT Load Test - Concurrent Increments")
    print("=" * 60)
    print()
    
    room1 = Room("inc-test")
    room2 = Room("inc-test")
    
    counter1 = collaborative_signal(room1, "counter", 0)
    room2.apply_update(room1.get_update())
    counter2 = collaborative_signal(room2, "counter", 0)
    
    print("Both rooms increment simultaneously (no sync between)...")
    
    # Both increment without syncing (conflict scenario)
    for i in range(10):
        counter1.value += 1
        counter2.value += 1
    
    print(f"  Room1: {counter1.value}")
    print(f"  Room2: {counter2.value}")
    
    print("\nSyncing bidirectionally...")
    room2.apply_update(room1.get_update())
    room1.apply_update(room2.get_update())
    
    print(f"  Room1: {counter1.value}")
    print(f"  Room2: {counter2.value}")
    
    # Verify they converged (CRDT property)
    if counter1.value == counter2.value:
        print(f"\n✅ CRDT resolved conflict! Both converged to {counter1.value}")
    else:
        print(f"\n⚠️  Values still differ after sync")
    
    print()


def test_many_signals_per_room():
    """Test many collaborative signals in one room."""
    print("=" * 60)
    print("📊 CRDT Load Test - Many Signals Per Room")
    print("=" * 60)
    print()
    
    for num_signals in [10, 50, 100, 500]:
        room1 = Room(f"many-{num_signals}")
        room2 = Room(f"many-{num_signals}")
        
        # Create many signals in room1
        signals1 = []
        for i in range(num_signals):
            sig = collaborative_signal(room1, f"sig-{i}", i)
            signals1.append(sig)
        
        # Sync to room2
        room2.apply_update(room1.get_update())
        
        # Create matching signals in room2
        signals2 = []
        for i in range(num_signals):
            sig = collaborative_signal(room2, f"sig-{i}", 0)
            signals2.append(sig)
        
        # Update all in room1
        start = time.perf_counter()
        for i, sig in enumerate(signals1):
            sig.value = i * 100
        
        # Sync to room2
        room2.apply_update(room1.get_update())
        elapsed = time.perf_counter() - start
        
        # Verify
        match = sum(1 for s1, s2 in zip(signals1, signals2) if s1.value == s2.value)
        
        print(f"[{num_signals:4} signals] {elapsed*1000:8.2f} ms | {match}/{num_signals} match")
    
    print()


def main():
    test_many_rooms_sync()
    test_high_frequency_updates()
    test_concurrent_increments()
    test_many_signals_per_room()
    
    print("=" * 60)
    print("✅ CRDT load tests complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
