"""
Lattice Component Model

This module provides the component decorator and element builders
for defining reactive UI components.

Example:
    @component
    def counter():
        count = signal(0)
        return div(
            h1(f"Count: {count.value}"),
            button("Increment", on_click=lambda: count.value += 1)
        )
"""

from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass, field


@dataclass
class VNode:
    """
    Virtual DOM node representing a UI element.
    
    This is the Python representation that will be serialized
    and sent to the browser for rendering.
    """
    tag: str
    attrs: Dict[str, Any] = field(default_factory=dict)
    children: List[Union["VNode", str]] = field(default_factory=list)
    key: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON/MessagePack serialization."""
        result: Dict[str, Any] = {"tag": self.tag}
        
        if self.attrs:
            # Separate event handlers from regular attributes
            attrs = {}
            events = {}
            for k, v in self.attrs.items():
                if k.startswith("on_"):
                    # Convert on_click to onclick format
                    event_name = k[3:]  # Remove "on_" prefix
                    events[event_name] = id(v)  # Use function id as reference
                else:
                    attrs[k] = v
            if attrs:
                result["attrs"] = attrs
            if events:
                result["events"] = events
        
        if self.children:
            result["children"] = [
                c.to_dict() if isinstance(c, VNode) else c
                for c in self.children
            ]
        
        if self.key:
            result["key"] = self.key
        
        return result


def _create_element(tag: str) -> Callable[..., VNode]:
    """
    Factory function to create element builders.
    
    Returns a function that creates VNodes for the given tag.
    """
    def element(*children: Union[VNode, str], key: Optional[str] = None, **attrs: Any) -> VNode:
        """
        Create a VNode with the given children and attributes.
        
        Args:
            *children: Child elements or text strings.
            key: Optional key for efficient diffing.
            **attrs: HTML attributes and event handlers.
        
        Returns:
            A VNode representing this element.
        """
        # Flatten any nested lists in children
        flat_children: List[Union[VNode, str]] = []
        for child in children:
            if isinstance(child, (list, tuple)):
                flat_children.extend(child)
            else:
                flat_children.append(child)
        
        return VNode(tag=tag, attrs=attrs, children=flat_children, key=key)
    
    return element


# HTML element builders
div = _create_element("div")
span = _create_element("span")
p = _create_element("p")
h1 = _create_element("h1")
h2 = _create_element("h2")
h3 = _create_element("h3")
h4 = _create_element("h4")
button = _create_element("button")
input_ = _create_element("input")  # Underscore to avoid conflict with builtin
label = _create_element("label")
form = _create_element("form")
table = _create_element("table")
thead = _create_element("thead")
tbody = _create_element("tbody")
tr = _create_element("tr")
th = _create_element("th")
td = _create_element("td")
ul = _create_element("ul")
ol = _create_element("ol")
li = _create_element("li")
a = _create_element("a")
img = _create_element("img")
br = _create_element("br")
hr = _create_element("hr")


class Component:
    """
    A reactive UI component.
    
    Components wrap a render function and track when they need to re-render.
    When any reactive dependencies change, the component marks itself dirty
    and will re-render on the next frame.
    """
    
    def __init__(self, render_fn: Callable[[], VNode]) -> None:
        """
        Create a new component.
        
        Args:
            render_fn: A function that returns a VNode tree.
        """
        self._render_fn = render_fn
        self._vnode: Optional[VNode] = None
        self._dirty = True
    
    def render(self) -> VNode:
        """
        Render the component, returning its VNode tree.
        
        If the component is clean, returns the cached VNode.
        If dirty, re-runs the render function.
        """
        if self._dirty or self._vnode is None:
            self._vnode = self._render_fn()
            self._dirty = False
        return self._vnode
    
    def mark_dirty(self) -> None:
        """Mark the component as needing re-render."""
        self._dirty = True
    
    def _on_dependency_changed(self) -> None:
        """Called when a reactive dependency changes."""
        self.mark_dirty()


def component(fn: Callable[[], VNode]) -> Component:
    """
    Decorator to create a reactive component.
    
    Example:
        @component
        def my_component():
            return div("Hello, World!")
    """
    return Component(fn)


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------

def _test_vnode_creation():
    """Test basic VNode creation."""
    node = div(
        h1("Hello"),
        p("World"),
        class_="container"
    )
    
    assert node.tag == "div"
    assert node.attrs == {"class_": "container"}
    assert len(node.children) == 2
    assert node.children[0].tag == "h1"
    print("  VNode creation: PASS")


def _test_vnode_serialization():
    """Test VNode to_dict serialization."""
    node = button("Click me", on_click=lambda: None, disabled=True)
    d = node.to_dict()
    
    assert d["tag"] == "button"
    assert d["attrs"]["disabled"] is True
    assert "events" in d
    assert "click" in d["events"]
    assert d["children"] == ["Click me"]
    print("  VNode serialization: PASS")


def _test_nested_elements():
    """Test nested element structure."""
    node = div(
        ul(
            li("Item 1"),
            li("Item 2"),
            li("Item 3"),
        )
    )
    
    assert node.tag == "div"
    assert node.children[0].tag == "ul"
    assert len(node.children[0].children) == 3
    assert all(c.tag == "li" for c in node.children[0].children)
    print("  Nested elements: PASS")


def _test_component():
    """Test component creation and rendering."""
    call_count = 0
    
    @component
    def test_comp():
        nonlocal call_count
        call_count += 1
        return div("Test")
    
    # First render
    vnode = test_comp.render()
    assert vnode.tag == "div"
    assert call_count == 1
    
    # Second render (cached)
    vnode2 = test_comp.render()
    assert call_count == 1  # Should use cache
    
    # Mark dirty and re-render
    test_comp.mark_dirty()
    vnode3 = test_comp.render()
    assert call_count == 2  # Should re-render
    
    print("  Component caching: PASS")


if __name__ == "__main__":
    print("Running component tests...")
    _test_vnode_creation()
    _test_vnode_serialization()
    _test_nested_elements()
    _test_component()
    print("All tests passed!")
