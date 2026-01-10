"""
Lattice Real-Time Dashboard Demo

Stress test for the reactive system:
- 100+ signals updating simultaneously
- Multiple derived memos
- WebSocket broadcasting to browser
- Performance metrics display

Run: python examples/realtime_dashboard.py
Open: http://localhost:8002
"""

import asyncio
import random
import time
import json
from aiohttp import web

# Import Lattice reactive primitives
import sys
sys.path.insert(0, "python")
from lattice import signal, memo, effect


# ============================================================================
# Reactive State - 100+ Signals
# ============================================================================

class DashboardState:
    """State manager with 100+ reactive signals."""
    
    def __init__(self, num_metrics: int = 100):
        self.num_metrics = num_metrics
        
        # Create 100+ signals for metrics
        self.metrics = [signal(random.uniform(0, 100)) for _ in range(num_metrics)]
        
        # Category signals
        self.categories = {
            "cpu": [signal(random.uniform(0, 100)) for _ in range(10)],
            "memory": [signal(random.uniform(0, 100)) for _ in range(10)],
            "network": [signal(random.uniform(0, 1000)) for _ in range(10)],
            "disk": [signal(random.uniform(0, 100)) for _ in range(10)],
        }
        
        # Derived values using memos
        self._setup_memos()
        
        # Track updates for performance metrics
        self.update_count = 0
        self.last_update_time = time.time()
    
    def _setup_memos(self):
        """Create memoized derived values."""
        # These will only recompute when dependencies change
        
        @memo
        def cpu_average():
            total = sum(s.value for s in self.categories["cpu"])
            return total / len(self.categories["cpu"])
        self.cpu_average = cpu_average
        
        @memo
        def memory_average():
            total = sum(s.value for s in self.categories["memory"])
            return total / len(self.categories["memory"])
        self.memory_average = memory_average
        
        @memo
        def network_total():
            return sum(s.value for s in self.categories["network"])
        self.network_total = network_total
        
        @memo
        def disk_average():
            total = sum(s.value for s in self.categories["disk"])
            return total / len(self.categories["disk"])
        self.disk_average = disk_average
        
        @memo
        def system_health():
            cpu = cpu_average()
            mem = memory_average()
            disk = disk_average()
            # Health score: lower is better
            return 100 - (cpu * 0.4 + mem * 0.4 + disk * 0.2)
        self.system_health = system_health
        
        @memo
        def all_metrics_average():
            total = sum(s.value for s in self.metrics)
            return total / len(self.metrics)
        self.all_metrics_average = all_metrics_average
    
    def update_random_metrics(self, count: int = 10):
        """Update random metrics to simulate live data."""
        # Update random general metrics
        for _ in range(count):
            idx = random.randint(0, self.num_metrics - 1)
            self.metrics[idx].value = random.uniform(0, 100)
        
        # Update category metrics
        for category in self.categories.values():
            for sig in random.sample(category, min(3, len(category))):
                if "network" in str(category):
                    sig.value = random.uniform(0, 1000)
                else:
                    sig.value = random.uniform(0, 100)
        
        self.update_count += count
    
    def to_dict(self) -> dict:
        """Serialize state for WebSocket."""
        return {
            "timestamp": time.time(),
            "update_count": self.update_count,
            "metrics": [s.value for s in self.metrics[:20]],  # First 20 for display
            "categories": {
                "cpu": [s.value for s in self.categories["cpu"]],
                "memory": [s.value for s in self.categories["memory"]],
                "network": [s.value for s in self.categories["network"]],
                "disk": [s.value for s in self.categories["disk"]],
            },
            "derived": {
                "cpu_avg": self.cpu_average(),
                "memory_avg": self.memory_average(),
                "network_total": self.network_total(),
                "disk_avg": self.disk_average(),
                "system_health": self.system_health(),
                "all_avg": self.all_metrics_average(),
            },
        }


# Global state
state = DashboardState(num_metrics=100)
clients = set()


# ============================================================================
# WebSocket Handler
# ============================================================================

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    clients.add(ws)
    print(f"Client connected. Total: {len(clients)}")
    
    try:
        async for msg in ws:
            pass  # We only send, not receive
    finally:
        clients.discard(ws)
        print(f"Client disconnected. Total: {len(clients)}")
    
    return ws


async def broadcast_state():
    """Broadcast current state to all connected clients."""
    if not clients:
        return
    
    data = json.dumps(state.to_dict())
    
    # Send to all clients
    dead_clients = set()
    for ws in clients:
        try:
            await ws.send_str(data)
        except:
            dead_clients.add(ws)
    
    # Cleanup dead connections
    for ws in dead_clients:
        clients.discard(ws)


async def update_loop():
    """Continuously update metrics and broadcast."""
    update_interval = 0.05  # 20 updates per second
    log_interval = 1.0  # Log every second
    last_log_time = time.time()
    last_log_count = 0
    
    while True:
        # Update random metrics
        state.update_random_metrics(count=15)
        
        # Broadcast to clients
        await broadcast_state()
        
        # Log performance every second
        now = time.time()
        if now - last_log_time >= log_interval:
            updates_per_sec = state.update_count - last_log_count
            print(f"[{state.update_count:8,} updates] "
                  f"{updates_per_sec:4} ups | "
                  f"CPU: {state.cpu_average():.1f}% | "
                  f"Mem: {state.memory_average():.1f}% | "
                  f"Health: {state.system_health():.1f} | "
                  f"Clients: {len(clients)}")
            last_log_time = now
            last_log_count = state.update_count
        
        await asyncio.sleep(update_interval)


# ============================================================================
# HTML Dashboard
# ============================================================================

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Lattice Real-Time Dashboard</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            padding: 20px;
            min-height: 100vh;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        h1 {
            font-size: 1.8rem;
            background: linear-gradient(90deg, #00d4ff, #7c3aed);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .stats {
            display: flex;
            gap: 20px;
        }
        .stat-pill {
            background: rgba(255,255,255,0.1);
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.9rem;
        }
        .stat-pill span {
            color: #00d4ff;
            font-weight: bold;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 16px;
        }
        .card {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 16px;
        }
        .card h2 {
            font-size: 1rem;
            color: #94a3b8;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .health-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
        }
        .health-good { background: #10b981; }
        .health-warning { background: #f59e0b; }
        .health-bad { background: #ef4444; }
        .metric-value {
            font-size: 2.5rem;
            font-weight: bold;
            color: #00d4ff;
        }
        .metric-unit {
            font-size: 1rem;
            color: #64748b;
            margin-left: 4px;
        }
        .bar-container {
            margin-top: 8px;
        }
        .bar {
            height: 8px;
            background: rgba(255,255,255,0.1);
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 4px;
        }
        .bar-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.2s ease;
        }
        .bar-fill.cpu { background: linear-gradient(90deg, #10b981, #f59e0b); }
        .bar-fill.memory { background: linear-gradient(90deg, #3b82f6, #8b5cf6); }
        .bar-fill.disk { background: linear-gradient(90deg, #f59e0b, #ef4444); }
        .bar-fill.network { background: linear-gradient(90deg, #00d4ff, #00ff88); }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 8px;
        }
        .mini-metric {
            background: rgba(0,0,0,0.2);
            border-radius: 6px;
            padding: 8px;
            text-align: center;
        }
        .mini-metric .value {
            font-size: 1.2rem;
            font-weight: bold;
            color: #00d4ff;
        }
        .mini-metric .label {
            font-size: 0.7rem;
            color: #64748b;
        }
        .log {
            background: rgba(0,0,0,0.3);
            border-radius: 8px;
            padding: 12px;
            font-family: 'Fira Code', monospace;
            font-size: 0.8rem;
            max-height: 200px;
            overflow-y: auto;
        }
        .log-entry {
            padding: 2px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .status {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #10b981;
            animation: pulse 1s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .mega-card {
            grid-column: span 2;
        }
        @media (max-width: 768px) {
            .mega-card { grid-column: span 1; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>⚡ Lattice Real-Time Dashboard</h1>
        <div class="stats">
            <div class="stat-pill">
                <span id="signals">100+</span> Signals
            </div>
            <div class="stat-pill">
                <span id="updates">0</span> Updates
            </div>
            <div class="stat-pill">
                <span id="ups">0</span> Updates/sec
            </div>
            <div class="stat-pill status">
                <div class="status-dot"></div>
                Live
            </div>
        </div>
    </div>
    
    <div class="grid">
        <div class="card">
            <h2>System Health</h2>
            <div class="metric-value" id="health">-</div>
            <div class="bar-container">
                <div class="bar"><div class="bar-fill cpu" id="health-bar" style="width: 0%"></div></div>
            </div>
        </div>
        
        <div class="card">
            <h2>🖥️ CPU Average</h2>
            <div class="metric-value" id="cpu-avg">-<span class="metric-unit">%</span></div>
            <div class="bar-container" id="cpu-bars"></div>
        </div>
        
        <div class="card">
            <h2>💾 Memory Average</h2>
            <div class="metric-value" id="mem-avg">-<span class="metric-unit">%</span></div>
            <div class="bar-container" id="mem-bars"></div>
        </div>
        
        <div class="card">
            <h2>💽 Disk Average</h2>
            <div class="metric-value" id="disk-avg">-<span class="metric-unit">%</span></div>
            <div class="bar-container" id="disk-bars"></div>
        </div>
        
        <div class="card">
            <h2>🌐 Network Total</h2>
            <div class="metric-value" id="net-total">-<span class="metric-unit">MB/s</span></div>
            <div class="bar-container" id="net-bars"></div>
        </div>
        
        <div class="card">
            <h2>📊 All Metrics Average</h2>
            <div class="metric-value" id="all-avg">-</div>
        </div>
        
        <div class="card mega-card">
            <h2>📈 Live Metrics (first 20 of 100+)</h2>
            <div class="metrics-grid" id="metrics-grid"></div>
        </div>
    </div>
    
    <script>
        const ws = new WebSocket('ws://localhost:8002/ws');
        let lastUpdateCount = 0;
        let lastTime = Date.now();
        
        ws.onopen = () => console.log('Connected to Lattice Dashboard');
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            // Update stats
            document.getElementById('updates').textContent = data.update_count.toLocaleString();
            
            // Calculate updates per second
            const now = Date.now();
            const elapsed = (now - lastTime) / 1000;
            if (elapsed > 0.5) {
                const ups = (data.update_count - lastUpdateCount) / elapsed;
                document.getElementById('ups').textContent = ups.toFixed(0);
                lastUpdateCount = data.update_count;
                lastTime = now;
            }
            
            // Update derived values
            const health = data.derived.system_health;
            document.getElementById('health').textContent = health.toFixed(1);
            document.getElementById('health-bar').style.width = health + '%';
            
            document.getElementById('cpu-avg').innerHTML = data.derived.cpu_avg.toFixed(1) + '<span class="metric-unit">%</span>';
            document.getElementById('mem-avg').innerHTML = data.derived.memory_avg.toFixed(1) + '<span class="metric-unit">%</span>';
            document.getElementById('disk-avg').innerHTML = data.derived.disk_avg.toFixed(1) + '<span class="metric-unit">%</span>';
            document.getElementById('net-total').innerHTML = (data.derived.network_total / 1000).toFixed(2) + '<span class="metric-unit">GB/s</span>';
            document.getElementById('all-avg').textContent = data.derived.all_avg.toFixed(1);
            
            // Update category bars
            updateBars('cpu-bars', data.categories.cpu, 'cpu');
            updateBars('mem-bars', data.categories.memory, 'memory');
            updateBars('disk-bars', data.categories.disk, 'disk');
            updateBars('net-bars', data.categories.network.map(v => v / 10), 'network');
            
            // Update metrics grid
            const grid = document.getElementById('metrics-grid');
            grid.innerHTML = data.metrics.map((v, i) => 
                `<div class="mini-metric">
                    <div class="value">${v.toFixed(0)}</div>
                    <div class="label">m${i}</div>
                </div>`
            ).join('');
        };
        
        function updateBars(containerId, values, className) {
            const container = document.getElementById(containerId);
            container.innerHTML = values.map(v => 
                `<div class="bar"><div class="bar-fill ${className}" style="width: ${Math.min(v, 100)}%"></div></div>`
            ).join('');
        }
    </script>
</body>
</html>
"""


async def handle_index(request):
    return web.Response(text=HTML, content_type='text/html')


async def handle_stats(request):
    """Return current stats as JSON."""
    return web.json_response(state.to_dict())


async def on_startup(app):
    """Start the update loop when server starts."""
    asyncio.create_task(update_loop())


def main():
    app = web.Application()
    app.router.add_get('/', handle_index)
    app.router.add_get('/ws', websocket_handler)
    app.router.add_get('/stats', handle_stats)
    app.on_startup.append(on_startup)
    
    print("=" * 60)
    print("🚀 Lattice Real-Time Dashboard")
    print("=" * 60)
    print()
    print("Open: http://localhost:8002")
    print()
    print("Stress test parameters:")
    print(f"  • 100+ reactive signals")
    print(f"  • 5 memoized derived values")
    print(f"  • 20 updates per second")
    print(f"  • 15 signals updated per tick")
    print()
    print("Press Ctrl+C to stop")
    print()
    
    web.run_app(app, host='localhost', port=8002, print=None)


if __name__ == "__main__":
    main()
