"""
Counter Demo: Lattice vs Streamlit Comparison

This demo shows how Lattice's reactive system differs from Streamlit's
full-rerun model using a simple counter application.

Key difference:
- Streamlit: Re-runs the ENTIRE script on every button click
- Lattice: Only updates the values that actually changed

Run this demo:
    python examples/counter_demo.py
"""

import time
from typing import List

# Import Lattice primitives
from lattice import signal, memo, effect

# Track how many times each computation runs
computation_log: List[str] = []


def log(msg: str) -> None:
    """Log a computation event."""
    computation_log.append(f"{time.time():.3f}: {msg}")
    print(f"  [LOG] {msg}")


print("=" * 60)
print("Lattice Counter Demo")
print("=" * 60)
print()

# Create reactive state
count = signal(0)
name = signal("World")

print("Creating reactive primitives...")
print()


# Create a memo that depends on count
@memo
def doubled():
    log("Computing doubled()")
    return count.value * 2


# Create a memo that depends on name
@memo
def greeting():
    log("Computing greeting()")
    return f"Hello, {name.value}!"


# Create a memo that depends on both
@memo
def summary():
    log("Computing summary()")
    return f"{greeting()} Count is {count.value}, doubled is {doubled()}"


# Create an effect that logs when summary changes
@effect
def on_summary_change():
    log(f"Effect: summary = '{summary()}'")


print("-" * 60)
print("Initial state created. Computation log:")
for entry in computation_log:
    print(f"  {entry}")
print()

# Clear log for next round
computation_log.clear()

print("-" * 60)
print("Incrementing count (count.value += 1)...")
print("Only count-dependent memos should recompute:")
print()

count.value = count.value + 1

print()
print("Computation log (should NOT include greeting):")
for entry in computation_log:
    print(f"  {entry}")
print()

# Clear log for next round  
computation_log.clear()

print("-" * 60)
print("Changing name (name.value = 'Lattice')...")
print("Only name-dependent memos should recompute:")
print()

name.value = "Lattice"

print()
print("Computation log (should NOT include doubled):")
for entry in computation_log:
    print(f"  {entry}")
print()

print("-" * 60)
print("Summary:")
print()
print("  In Streamlit, EVERY computation would run on EVERY change.")
print("  In Lattice, only the affected computations run.")
print()
print("  This is O(delta) vs O(n) - proportional to what changed,")
print("  not the total program size.")
print()
print("=" * 60)
