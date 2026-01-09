"""
Lattice Server

Simple WebSocket server that serves a Lattice application.
Handles rendering, diffing, and patching in real-time.
"""

import asyncio
import json
import http.server
import socketserver
import threading
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass

from .component import VNode, Component
from .diff import diff, Patch


# Simple in-memory event handler registry
_event_handlers: Dict[int, Callable[[], None]] = {}


def _register_handler(handler: Callable[[], None]) -> int:
    """Register an event handler and return its ID."""
    handler_id = id(handler)
    _event_handlers[handler_id] = handler
    return handler_id


def _call_handler(handler_id: int) -> bool:
    """Call an event handler by ID. Returns True if found."""
    handler = _event_handlers.get(handler_id)
    if handler:
        handler()
        return True
    return False


@dataclass
class AppState:
    """State for a running Lattice application."""
    component: Component
    current_vnode: Optional[VNode] = None
    clients: List["ClientConnection"] = None
    
    def __post_init__(self):
        if self.clients is None:
            self.clients = []
    
    def render_and_diff(self) -> List[Patch]:
        """Render the component and return patches."""
        new_vnode = self.component.render()
        patches = diff(self.current_vnode, new_vnode)
        self.current_vnode = new_vnode
        return patches
    
    def handle_event(self, handler_id: int) -> List[Patch]:
        """Handle an event and return resulting patches."""
        if _call_handler(handler_id):
            self.component.mark_dirty()
            return self.render_and_diff()
        return []


class ClientConnection:
    """Represents a connected browser client."""
    
    def __init__(self, send_fn: Callable[[str], None]):
        self.send = send_fn
    
    def send_patches(self, patches: List[Patch]) -> None:
        """Send patches to the client."""
        data = [p.to_dict() for p in patches]
        self.send(json.dumps({"type": "patches", "data": data}))
    
    def send_full_render(self, vnode: VNode) -> None:
        """Send a full render to the client."""
        self.send(json.dumps({"type": "render", "data": vnode.to_dict()}))


class LatticeApp:
    """
    A Lattice application that can be run as a server.
    
    Example:
        from lattice.server import LatticeApp
        from lattice.component import component, div, button
        from lattice import signal
        
        count = signal(0)
        
        @component
        def counter():
            return div(
                f"Count: {count.value}",
                button("Increment", on_click=lambda: setattr(count, 'value', count.value + 1))
            )
        
        app = LatticeApp(counter)
        app.run()
    """
    
    def __init__(self, root_component: Component):
        self.state = AppState(component=root_component)
        self._html_template = self._generate_html()
    
    def _generate_html(self) -> str:
        """Generate the HTML page that hosts the app."""
        return '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lattice App</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 20px; }
        button { padding: 8px 16px; margin: 4px; cursor: pointer; }
        .container { max-width: 800px; margin: 0 auto; }
    </style>
</head>
<body>
    <div id="app" class="container"></div>
    <script>
        const app = document.getElementById('app');
        let ws = null;
        
        // Connect to WebSocket
        function connect() {
            ws = new WebSocket('ws://' + location.host + '/ws');
            
            ws.onopen = () => console.log('Connected to Lattice server');
            ws.onclose = () => setTimeout(connect, 1000);
            ws.onerror = (e) => console.error('WebSocket error:', e);
            
            ws.onmessage = (event) => {
                const msg = JSON.parse(event.data);
                if (msg.type === 'render') {
                    app.innerHTML = '';
                    app.appendChild(renderNode(msg.data));
                } else if (msg.type === 'patches') {
                    applyPatches(msg.data);
                }
            };
        }
        
        // Render a VNode to DOM
        function renderNode(vnode) {
            if (typeof vnode === 'string') return document.createTextNode(vnode);
            
            const el = document.createElement(vnode.tag);
            
            // Apply attributes
            if (vnode.attrs) {
                for (const [key, value] of Object.entries(vnode.attrs)) {
                    if (key === 'class_') {
                        el.className = value;
                    } else {
                        el.setAttribute(key, value);
                    }
                }
            }
            
            // Apply event handlers
            if (vnode.events) {
                for (const [event, handlerId] of Object.entries(vnode.events)) {
                    el.addEventListener(event, () => {
                        ws.send(JSON.stringify({ type: 'event', handlerId }));
                    });
                }
            }
            
            // Render children
            if (vnode.children) {
                for (const child of vnode.children) {
                    el.appendChild(renderNode(child));
                }
            }
            
            return el;
        }
        
        // Apply patches to DOM
        function applyPatches(patches) {
            for (const patch of patches) {
                const el = getElementByPath(patch.path);
                switch (patch.type) {
                    case 'create':
                        const parent = patch.path.length > 0 
                            ? getElementByPath(patch.path.slice(0, -1)) 
                            : app;
                        parent.appendChild(renderNode(patch.data.node || patch.data.text));
                        break;
                    case 'remove':
                        el?.remove();
                        break;
                    case 'replace':
                        el?.replaceWith(renderNode(patch.data.node));
                        break;
                    case 'text':
                        if (el) el.textContent = patch.data.text;
                        break;
                    case 'update':
                        if (el) {
                            for (const [k, v] of Object.entries(patch.data.add_attrs || {})) {
                                el.setAttribute(k === 'class_' ? 'class' : k, v);
                            }
                            for (const k of patch.data.remove_attrs || []) {
                                el.removeAttribute(k);
                            }
                        }
                        break;
                }
            }
        }
        
        // Get element by path (array of child indices)
        function getElementByPath(path) {
            let el = app;
            for (const i of path) {
                if (!el || !el.childNodes[i]) return null;
                el = el.childNodes[i];
            }
            return el;
        }
        
        connect();
    </script>
</body>
</html>'''
    
    def run(self, host: str = "localhost", port: int = 8000):
        """Run the application server."""
        print(f"Starting Lattice server at http://{host}:{port}")
        print("Press Ctrl+C to stop")
        
        # This is a simplified synchronous server for demo purposes
        # A production version would use asyncio + websockets
        
        class Handler(http.server.SimpleHTTPRequestHandler):
            app_instance = self
            
            def do_GET(self):
                if self.path == "/" or self.path == "/index.html":
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(self.app_instance._html_template.encode())
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def log_message(self, format, *args):
                pass  # Suppress logs
        
        with socketserver.TCPServer((host, port), Handler) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nServer stopped")


# Helper function to run an app
def run_app(component: Component, host: str = "localhost", port: int = 8000):
    """Run a Lattice component as a web application."""
    app = LatticeApp(component)
    app.run(host, port)
