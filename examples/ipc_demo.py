#!/usr/bin/env python3
"""
Demo script showing IPC server and client in action

This demonstrates the basic IPC communication layer between
the daemon and CLI.

Usage:
    # Terminal 1 - Run server
    python3 examples/ipc_demo.py server
    
    # Terminal 2 - Run client
    python3 examples/ipc_demo.py client
"""

import sys
import time
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from exostream.daemon.ipc_server import IPCServerManager
from exostream.cli.ipc_client import IPCClientManager
from exostream.common.protocol import Methods

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def run_server():
    """Run a demo IPC server"""
    print("Starting IPC server...")
    print("Socket: /tmp/exostream_demo.sock")
    print("Press Ctrl+C to stop")
    print()
    
    server = IPCServerManager("/tmp/exostream_demo.sock")
    
    # Register demo handlers
    def ping_handler(params):
        print("  [Server] Received ping")
        return {"pong": True}
    
    def echo_handler(params):
        message = params.get("message", "")
        print(f"  [Server] Received echo: {message}")
        return {"echo": message, "length": len(message)}
    
    def status_handler(params):
        print("  [Server] Status requested")
        return {
            "running": True,
            "version": "0.3.0",
            "uptime_seconds": 123.45,
            "pid": 12345
        }
    
    def stream_start_handler(params):
        print(f"  [Server] Stream start requested")
        print(f"    Device: {params.get('device')}")
        print(f"    Name: {params.get('name')}")
        print(f"    Resolution: {params.get('resolution')}")
        return {
            "status": "started",
            "stream_name": params.get('name', 'exostream')
        }
    
    server.register_handler("daemon.ping", ping_handler)
    server.register_handler("echo", echo_handler)
    server.register_handler("daemon.status", status_handler)
    server.register_handler("stream.start", stream_start_handler)
    
    server.start()
    
    print("✓ Server started!")
    print()
    
    try:
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping server...")
        server.stop()
        print("✓ Server stopped")


def run_client():
    """Run demo IPC client"""
    print("Connecting to IPC server...")
    print("Socket: /tmp/exostream_demo.sock")
    print()
    
    client = IPCClientManager("/tmp/exostream_demo.sock")
    
    # Check if daemon is running
    if not client.is_daemon_running():
        print("✗ Daemon is not running!")
        print("  Start the server first: python3 examples/ipc_demo.py server")
        return
    
    print("✓ Daemon is running")
    print()
    
    # Test ping
    print("1. Testing ping...")
    result = client.ping()
    print(f"   Result: {result}")
    print()
    
    # Test echo
    print("2. Testing echo...")
    result = client.client.call("echo", {"message": "Hello, World!"})
    print(f"   Result: {result}")
    print()
    
    # Test status
    print("3. Testing daemon status...")
    status = client.get_daemon_status()
    print(f"   Running: {status['running']}")
    print(f"   Version: {status['version']}")
    print(f"   Uptime: {status['uptime_seconds']} seconds")
    print(f"   PID: {status['pid']}")
    print()
    
    # Test stream start
    print("4. Testing stream start...")
    result = client.start_stream(
        device="/dev/video0",
        name="TestCamera",
        resolution="1920x1080",
        fps=30
    )
    print(f"   Result: {result}")
    print()
    
    print("✓ All tests passed!")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 examples/ipc_demo.py server   # Run server")
        print("  python3 examples/ipc_demo.py client   # Run client")
        sys.exit(1)
    
    mode = sys.argv[1]
    
    if mode == "server":
        run_server()
    elif mode == "client":
        run_client()
    else:
        print(f"Unknown mode: {mode}")
        print("Use 'server' or 'client'")
        sys.exit(1)


if __name__ == '__main__':
    main()

