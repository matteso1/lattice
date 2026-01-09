"""
Lattice Interactive Demo Server (Simplified)

A single-file demo that runs everything on one port using aiohttp.

Run:
    cd lattice-core
    .\.venv\Scripts\pip.exe install aiohttp
    .\.venv\Scripts\python.exe ..\examples\interactive_demo.py
    
Then open http://localhost:8000 in your browser.
"""

import asyncio
import json
import sys
import os

# Add lattice to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lattice-core', 'python'))

from lattice import signal
from lattice.component import div, h1, h2, p, button, VNode

# Reactive state
count = signal(0)

# Event handlers
handlers = {
    "increment": lambda: setattr(count, 'value', count.value + 1),
    "decrement": lambda: setattr(count, 'value', count.value - 1),
    "reset": lambda: setattr(count, 'value', 0),
}


def render_app() -> VNode:
    """Render the counter application."""
    return div(
        h1("Lattice Interactive Counter"),
        p("Click the buttons to update the count in real-time!"),
        
        div(
            h2(f"Count: {count.value}"),
            
            div(
                button("-", id="btn-dec", data_handler="decrement"),
                button("Reset", id="btn-reset", data_handler="reset"),  
                button("+", id="btn-inc", data_handler="increment"),
                style="display: flex; gap: 10px; justify-content: center;"
            ),
            
            div(
                p(f"Doubled: {count.value * 2}"),
                p(f"Squared: {count.value ** 2}"),
                style="margin-top: 20px; color: #666;"
            ),
            
            style="text-align: center; padding: 30px; border: 2px solid #4CAF50; border-radius: 12px; margin: 20px 0; background: white;"
        ),
        
        class_="container"
    )


def vnode_to_html(node) -> str:
    """Convert VNode to HTML string."""
    if isinstance(node, str):
        return node
    
    attrs = []
    for key, value in node.attrs.items():
        if key == "class_":
            attrs.append(f'class="{value}"')
        elif key.startswith("data_"):
            # Convert data_handler to data-handler for HTML
            html_key = key.replace("_", "-")
            attrs.append(f'{html_key}="{value}"')
        elif not key.startswith("on_"):
            attrs.append(f'{key}="{value}"')
    
    attr_str = " " + " ".join(attrs) if attrs else ""
    
    if node.tag in ("br", "hr", "img", "input"):
        return f"<{node.tag}{attr_str} />"
    
    children_html = "".join(vnode_to_html(c) for c in node.children)
    return f"<{node.tag}{attr_str}>{children_html}</{node.tag}>"



HTML_PAGE = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lattice Interactive Demo</title>
    <style>
        * { box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            max-width: 600px; margin: 40px auto; padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container { 
            background: rgba(255,255,255,0.95);
            padding: 30px; border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 { color: #333; text-align: center; margin-bottom: 10px; }
        h2 { color: #4CAF50; font-size: 2.5em; margin: 20px 0; }
        p { color: #666; text-align: center; }
        button {
            padding: 15px 30px; font-size: 20px; font-weight: bold;
            border: none; border-radius: 8px; cursor: pointer;
            color: white; transition: all 0.2s;
        }
        button:hover { transform: scale(1.05); }
        button:active { transform: scale(0.95); }
        #btn-dec { background: linear-gradient(135deg, #f44336, #e91e63); }
        #btn-reset { background: linear-gradient(135deg, #2196F3, #03A9F4); }
        #btn-inc { background: linear-gradient(135deg, #4CAF50, #8BC34A); }
        #status { 
            position: fixed; top: 10px; right: 10px;
            padding: 8px 16px; background: #333; color: white;
            border-radius: 20px; font-size: 12px;
        }
        #status.connected { background: #4CAF50; }
    </style>
</head>
<body>
    <div id="app">Loading...</div>
    <div id="status">Connecting...</div>
    <script>
        const app = document.getElementById('app');
        const status = document.getElementById('status');
        let ws;
        
        function connect() {
            ws = new WebSocket('ws://' + location.host + '/ws');
            ws.onopen = () => { status.textContent = 'Connected'; status.className = 'connected'; };
            ws.onclose = () => { status.textContent = 'Reconnecting...'; status.className = ''; setTimeout(connect, 1000); };
            ws.onmessage = (e) => {
                const msg = JSON.parse(e.data);
                if (msg.type === 'html') {
                    app.innerHTML = msg.data;
                    document.querySelectorAll('[data-handler]').forEach(el => {
                        el.onclick = () => ws.send(JSON.stringify({ type: 'event', handler: el.dataset.handler }));
                    });
                }
            };
        }
        connect();
    </script>
</body>
</html>'''


async def main():
    try:
        from aiohttp import web
    except ImportError:
        print("Installing aiohttp...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "aiohttp"])
        from aiohttp import web
    
    clients = set()
    
    async def handle_index(request):
        return web.Response(text=HTML_PAGE, content_type='text/html')
    
    async def handle_websocket(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        clients.add(ws)
        
        # Send initial render
        html = vnode_to_html(render_app())
        await ws.send_json({"type": "html", "data": html})
        
        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    if data.get("type") == "event":
                        handler = handlers.get(data.get("handler"))
                        if handler:
                            handler()
                            # Broadcast update to all clients
                            html = vnode_to_html(render_app())
                            for client in clients:
                                await client.send_json({"type": "html", "data": html})
        finally:
            clients.discard(ws)
        
        return ws
    
    app = web.Application()
    app.router.add_get('/', handle_index)
    app.router.add_get('/ws', handle_websocket)
    
    print("=" * 60)
    print("  LATTICE INTERACTIVE DEMO")
    print("=" * 60)
    print()
    print("  Open in browser: http://localhost:8000")
    print()
    print("  Click the buttons to see real-time updates!")
    print("  Press Ctrl+C to stop.")
    print()
    print("=" * 60)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8000)
    await site.start()
    
    await asyncio.Future()  # Run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped")
