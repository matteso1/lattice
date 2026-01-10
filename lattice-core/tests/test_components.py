"""
Tests for Lattice Component and Rendering System (Phase 2).

These tests verify VNode creation, element builders, and the diff algorithm.
"""

import pytest
import json


class TestVNode:
    """Tests for VNode virtual DOM structure."""
    
    def test_vnode_creation(self):
        """VNode should be created with correct attributes."""
        from lattice.component import VNode
        
        node = VNode(tag="div", attrs={"class": "container"}, children=["Hello"])
        
        assert node.tag == "div"
        assert node.attrs == {"class": "container"}
        assert node.children == ["Hello"]
    
    def test_vnode_to_dict(self):
        """VNode should serialize to dict."""
        from lattice.component import VNode
        
        node = VNode(tag="button", attrs={"id": "submit"}, children=["Click"])
        d = node.to_dict()
        
        assert d["tag"] == "button"
        assert d["attrs"]["id"] == "submit"
    
    def test_vnode_to_json(self):
        """VNode should serialize to JSON via to_dict."""
        from lattice.component import VNode
        
        node = VNode(tag="p", attrs={}, children=["Text"])
        d = node.to_dict()
        j = json.dumps(d)
        
        parsed = json.loads(j)
        assert parsed["tag"] == "p"


class TestElementBuilders:
    """Tests for element builder functions."""
    
    def test_div_builder(self):
        """div() should create a div VNode."""
        from lattice.component import div
        
        node = div("Hello", id="test")
        assert node.tag == "div"
        assert node.attrs["id"] == "test"
        assert node.children == ["Hello"]  # List not tuple
    
    def test_button_builder(self):
        """button() should create a button VNode."""
        from lattice.component import button
        
        node = button("Click Me", type="submit")
        assert node.tag == "button"
        assert node.attrs["type"] == "submit"
    
    def test_nested_elements(self):
        """Elements should nest correctly."""
        from lattice.component import div, p, span
        
        node = div(
            p("Paragraph"),
            span("Span"),
            class_="container"
        )
        
        assert node.tag == "div"
        assert len(node.children) == 2
        assert node.children[0].tag == "p"
        assert node.children[1].tag == "span"
    
    def test_all_element_types(self):
        """All element builders should work."""
        from lattice.component import (
            div, span, p, h1, h2, h3, h4,
            button, input_, a, ul, li
        )
        
        elements = [
            div("div"),
            span("span"),
            p("p"),
            h1("h1"),
            h2("h2"),
            button("button"),
            a("link", href="#"),
            ul(li("item")),
        ]
        
        for el in elements:
            assert el.tag is not None
            assert isinstance(el.children, list)  # List not tuple


class TestDiffAlgorithm:
    """Tests for VNode diff algorithm."""
    
    def test_diff_identical_trees(self):
        """Identical trees should produce no patches."""
        from lattice.component import div, p
        from lattice.diff import diff
        
        old = div(p("Hello"))
        new = div(p("Hello"))
        
        patches = diff(old, new)
        assert len(patches) == 0
    
    def test_diff_text_change(self):
        """Text content change should produce TEXT patch."""
        from lattice.component import p
        from lattice.diff import diff, PatchType
        
        old = p("Hello")
        new = p("World")
        
        patches = diff(old, new)
        assert len(patches) == 1
        assert patches[0].type == PatchType.TEXT
    
    def test_diff_attribute_change(self):
        """Attribute change should produce UPDATE patch."""
        from lattice.component import div
        from lattice.diff import diff, PatchType
        
        old = div("Content", class_="old")
        new = div("Content", class_="new")
        
        patches = diff(old, new)
        assert any(p.type == PatchType.UPDATE for p in patches)
    
    def test_diff_add_child(self):
        """Adding child should produce CREATE patch."""
        from lattice.component import div, p
        from lattice.diff import diff, PatchType
        
        old = div(p("One"))
        new = div(p("One"), p("Two"))
        
        patches = diff(old, new)
        assert any(p.type == PatchType.CREATE for p in patches)
    
    def test_diff_remove_child(self):
        """Removing child should produce REMOVE patch."""
        from lattice.component import div, p
        from lattice.diff import diff, PatchType
        
        old = div(p("One"), p("Two"))
        new = div(p("One"))
        
        patches = diff(old, new)
        assert any(p.type == PatchType.REMOVE for p in patches)
    
    def test_diff_replace_node(self):
        """Different tag should produce REPLACE patch."""
        from lattice.component import div, span
        from lattice.diff import diff, PatchType
        
        old = div("Content")
        new = span("Content")
        
        patches = diff(old, new)
        assert any(p.type == PatchType.REPLACE for p in patches)


class TestComponentDecorator:
    """Tests for @component decorator."""
    
    def test_component_renders(self):
        """Component should return VNode via .render()."""
        from lattice import signal
        from lattice.component import component, div, p
        
        count = signal(0)
        
        @component
        def Counter():
            return div(p(f"Count: {count.value}"))
        
        result = Counter.render()  # Component uses .render()
        assert result.tag == "div"
    
    def test_component_caches(self):
        """Component should cache result."""
        from lattice.component import component, div
        
        call_count = 0
        
        @component
        def Expensive():
            nonlocal call_count
            call_count += 1
            return div("Content")
        
        Expensive.render()
        Expensive.render()
        
        # Should only call once due to caching
        assert call_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
