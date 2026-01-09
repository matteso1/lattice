"""Test pycrdt sync mechanism."""
from pycrdt import Doc, Map

# Test basic pycrdt sync
doc1 = Doc()
doc2 = Doc()

# Get map from both docs
state1 = doc1.get('state', type=Map)
state2 = doc2.get('state', type=Map)

# Set value in doc1
state1['count'] = 42

print(f"Before sync - doc1 count: {state1.get('count')}")
print(f"Before sync - doc2 count: {state2.get('count')}")

# Get update from doc1 and apply to doc2
update = doc1.get_update()
print(f"Update bytes: {len(update)}")
doc2.apply_update(update)

print(f"After sync - doc2 count: {state2.get('count')}")
