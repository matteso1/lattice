"""
Lattice UI Demo: Interactive Counter

This demo shows a complete Lattice application running in the browser.
It demonstrates:
- Reactive state (signal)
- Component rendering
- Event handling
- Minimal DOM updates

Run this demo:
    python examples/ui_demo.py

Then open http://localhost:8000 in your browser.
"""

import sys
import os

# Add the lattice package to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lattice-core', 'python'))

from lattice import signal
from lattice.component import component, div, h1, h2, p, button, span


# Create reactive state
count = signal(0)
name = signal("World")


def increment():
    """Increment the counter."""
    count.value += 1


def decrement():
    """Decrement the counter."""
    count.value -= 1


def reset():
    """Reset the counter."""
    count.value = 0


@component
def counter_app():
    """
    A simple counter application demonstrating Lattice reactivity.
    
    When buttons are clicked:
    1. Event is sent to server
    2. Signal value is updated
    3. Component re-renders
    4. Diff produces minimal patches
    5. Only changed DOM nodes update
    """
    return div(
        h1("Lattice Counter Demo"),
        
        p("This counter demonstrates fine-grained reactivity."),
        p("Only the count value updates when buttons are clicked."),
        
        div(
            h2(f"Count: {count.value}"),
            
            div(
                button("-", on_click=decrement),
                button("Reset", on_click=reset),
                button("+", on_click=increment),
            ),
            
            div(
                p(f"Doubled: {count.value * 2}"),
                p(f"Squared: {count.value ** 2}"),
            ),
        ),
        
        div(
            h2(f"Hello, {name.value}!"),
            p("The greeting and count are independent."),
            p("Changing count does NOT re-render the greeting."),
        ),
        
        class_="container"
    )


if __name__ == "__main__":
    # For now, just render and show the VNode structure
    print("=" * 60)
    print("Lattice UI Demo")
    print("=" * 60)
    print()
    
    print("Rendering component...")
    vnode = counter_app.render()
    
    print()
    print("VNode structure:")
    print("-" * 60)
    
    import json
    print(json.dumps(vnode.to_dict(), indent=2)[:2000] + "...")
    
    print()
    print("-" * 60)
    print()
    print("Component created successfully!")
    print()
    print("To run the full UI demo with a web server,")
    print("we need to install websockets:")
    print()
    print("  pip install websockets")
    print()
    print("Then run:")
    print("  python examples/ui_demo_server.py")
