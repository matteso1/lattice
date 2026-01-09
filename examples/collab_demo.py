"""
Lattice Collaborative Counter Demo

This demo shows multiple users editing the same counter in real-time.
Open the demo in multiple browser tabs to simulate multiple users.

Run:
    cd lattice-core
    .\.venv\Scripts\python.exe ..\examples\collab_demo.py
    
Then open http://localhost:8000 in multiple browser tabs.
"""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lattice-core', 'python'))

from lattice.collab import Room, collaborative_signal
from lattice.component import div, h1, h2, p, button, span, VNode


# Create a shared room for all clients
room = Room("shared-counter-room")

# Collaborative signal - syncs across all clients
count = collaborative_signal(room, "count", 0)


def render_app(user_id: str) -> VNode:
    """Render the counter app for a specific user."""
    return div(
        h1("Collaborative Counter"),
        p("Open this page in multiple tabs - they all share the same count!"),
        
        div(
            h2(f"Count: {int(count.value or 0)}"),
            
            div(
                button("-", id="btn-dec", data_handler="decrement"),
                button("Reset", id="btn-reset", data_handler="reset"),
                button("+", id="btn-inc", data_handler="increment"),
                style="display: flex; gap: 10px; justify-content: center;"
            ),
            
            p(f"Your user ID: {user_id}", style="color: #888; font-size: 12px;"),
            
            style="text-align: center; padding: 30px; border: 2px solid #9C27B0; border-radius: 12px; margin: 20px 0; background: white;"
        ),
        
        div(
            h2("How CRDT Sync Works:"),
            p("1. Each tab has its own copy of the state"),
            p("2. When you click, your change is sent to the server"),
            p("3. Server broadcasts the update to all tabs"),
            p("4. CRDTs automatically merge concurrent changes"),
            style="background: #f3e5f5; padding: 15px; border-radius: 8px;"
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
    <title>Lattice Collaborative Demo</title>
    <style>
        * { box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            max-width: 600px; margin: 40px auto; padding: 20px;
            background: linear-gradient(135deg, #9C27B0 0%, #673AB7 100%);
            min-height: 100vh;
        }
        .container { 
            background: rgba(255,255,255,0.95);
            padding: 30px; border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 { color: #333; text-align: center; }
        h2 { color: #9C27B0; font-size: 2.5em; margin: 20px 0; }
        p { color: #666; text-align: center; }
        button {
            padding: 15px 30px; font-size: 20px; font-weight: bold;
            border: none; border-radius: 8px; cursor: pointer;
            color: white; transition: all 0.2s;
        }
        button:hover { transform: scale(1.05); }
        #btn-dec { background: linear-gradient(135deg, #f44336, #e91e63); }
        #btn-reset { background: linear-gradient(135deg, #9C27B0, #673AB7); }
        #btn-inc { background: linear-gradient(135deg, #4CAF50, #8BC34A); }
        #status { 
            position: fixed; top: 10px; right: 10px;
            padding: 8px 16px; background: #333; color: white;
            border-radius: 20px; font-size: 12px;
        }
        #status.connected { background: #9C27B0; }
        #users {
            position: fixed; top: 10px; left: 10px;
            padding: 8px 16px; background: #673AB7; color: white;
            border-radius: 20px; font-size: 12px;
        }
    </style>
</head>
<body>
    <div id="app">Loading...</div>
    <div id="status">Connecting...</div>
    <div id="users">Users: 1</div>
    <script>
        const app = document.getElementById('app');
        const status = document.getElementById('status');
        const usersEl = document.getElementById('users');
        let ws;
        
        // Generate a random user ID for this tab
        const userId = Math.random().toString(36).substring(2, 8).toUpperCase();
        
        function connect() {
            ws = new WebSocket('ws://' + location.host + '/ws?user=' + userId);
            ws.onopen = () => { 
                status.textContent = 'Connected'; 
                status.className = 'connected'; 
            };
            ws.onclose = () => { 
                status.textContent = 'Reconnecting...'; 
                status.className = ''; 
                setTimeout(connect, 1000); 
            };
            ws.onmessage = (e) => {
                const msg = JSON.parse(e.data);
                if (msg.type === 'html') {
                    app.innerHTML = msg.data;
                    document.querySelectorAll('[data-handler]').forEach(el => {
                        el.onclick = () => ws.send(JSON.stringify({ 
                            type: 'event', 
                            handler: el.dataset.handler,
                            user: userId
                        }));
                    });
                } else if (msg.type === 'users') {
                    usersEl.textContent = 'Users: ' + msg.count;
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
    
    clients = {}
    
    # Event handlers
    def handle_increment():
        count.value = (count.value or 0) + 1
    
    def handle_decrement():
        count.value = (count.value or 0) - 1
    
    def handle_reset():
        count.value = 0
    
    handlers = {
        "increment": handle_increment,
        "decrement": handle_decrement,
        "reset": handle_reset,
    }
    
    async def broadcast_state():
        """Broadcast current state to all connected clients."""
        for user_id, ws in list(clients.items()):
            try:
                html = vnode_to_html(render_app(user_id))
                await ws.send_json({"type": "html", "data": html})
                await ws.send_json({"type": "users", "count": len(clients)})
            except:
                clients.pop(user_id, None)
    
    async def handle_index(request):
        return web.Response(text=HTML_PAGE, content_type='text/html')
    
    async def handle_websocket(request):
        user_id = request.query.get('user', 'unknown')
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        clients[user_id] = ws
        print(f"User {user_id} connected. Total users: {len(clients)}")
        
        # Send initial state
        html = vnode_to_html(render_app(user_id))
        await ws.send_json({"type": "html", "data": html})
        await ws.send_json({"type": "users", "count": len(clients)})
        
        # Broadcast user count to all
        for uid, client in clients.items():
            if uid != user_id:
                try:
                    await client.send_json({"type": "users", "count": len(clients)})
                except:
                    pass
        
        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    if data.get("type") == "event":
                        handler = handlers.get(data.get("handler"))
                        if handler:
                            handler()
                            print(f"User {data.get('user')} clicked {data.get('handler')}, count is now {int(count.value or 0)}")
                            await broadcast_state()
        finally:
            clients.pop(user_id, None)
            print(f"User {user_id} disconnected. Total users: {len(clients)}")
            # Broadcast updated user count
            for uid, client in clients.items():
                try:
                    await client.send_json({"type": "users", "count": len(clients)})
                except:
                    pass
        
        return ws
    
    app = web.Application()
    app.router.add_get('/', handle_index)
    app.router.add_get('/ws', handle_websocket)
    
    print("=" * 60)
    print("  LATTICE COLLABORATIVE DEMO")
    print("=" * 60)
    print()
    print("  Open in MULTIPLE browser tabs: http://localhost:8000")
    print()
    print("  Each tab is a separate 'user'")
    print("  Click buttons in any tab - ALL tabs update!")
    print()
    print("  Press Ctrl+C to stop.")
    print("=" * 60)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8000)
    await site.start()
    
    await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped")
