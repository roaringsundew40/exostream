#!/usr/bin/env python3
"""
Demo script showing the complete daemon in action

This demonstrates the full daemon with streaming service integration.

Usage:
    # Terminal 1 - Run daemon
    python3 examples/daemon_demo.py daemon
    
    # Terminal 2 - Run client commands
    python3 examples/daemon_demo.py client
"""

import sys
import time
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from exostream.daemon.main import ExostreamDaemon
from exostream.cli.ipc_client import IPCClientManager, DaemonNotRunningError

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def run_daemon():
    """Run the daemon"""
    print("=" * 70)
    print("EXOSTREAM DAEMON DEMO")
    print("=" * 70)
    print()
    print("Starting daemon...")
    print("Socket: /tmp/exostream_demo.sock")
    print("State: ~/.exostream/")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 70)
    print()
    
    # Create daemon
    daemon = ExostreamDaemon(
        socket_path="/tmp/exostream_demo.sock"
    )
    
    # Start daemon (blocks until stopped)
    try:
        daemon.start()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        daemon.stop()
        print("Daemon stopped")


def run_client():
    """Run client commands to interact with daemon"""
    print("=" * 70)
    print("EXOSTREAM CLIENT DEMO")
    print("=" * 70)
    print()
    
    # Create client
    client = IPCClientManager("/tmp/exostream_demo.sock")
    
    # Check if daemon is running
    print("1. Checking if daemon is running...")
    if not client.is_daemon_running():
        print("   ✗ Daemon is not running!")
        print("   Start the daemon first: python3 examples/daemon_demo.py daemon")
        return
    print("   ✓ Daemon is running")
    print()
    
    # Test ping
    print("2. Testing ping...")
    try:
        result = client.ping()
        print(f"   ✓ Pong: {result}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    print()
    
    # Get daemon status
    print("3. Getting daemon status...")
    try:
        status = client.get_daemon_status()
        print(f"   Version: {status['version']}")
        print(f"   PID: {status['pid']}")
        print(f"   Uptime: {status['uptime_seconds']:.1f} seconds")
        print(f"   Healthy: {status['health']['healthy']}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    print()
    
    # List devices
    print("4. Listing video devices...")
    try:
        devices = client.list_devices()
        if devices:
            for device in devices:
                status_icon = "🔴" if device['in_use'] else "🟢"
                print(f"   {status_icon} {device['path']}: {device['name']}")
        else:
            print("   (No video devices found)")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    print()
    
    # Get stream status
    print("5. Getting stream status...")
    try:
        status = client.get_stream_status()
        if status['streaming']:
            print(f"   ✓ Streaming: {status['stream_name']}")
            print(f"     Device: {status['device']}")
            print(f"     Resolution: {status['resolution']}")
            print(f"     FPS: {status['fps']}")
            print(f"     Uptime: {status['uptime_seconds']:.1f} seconds")
        else:
            print("   Not streaming")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    print()
    
    # Interactive menu
    print("=" * 70)
    print("Interactive Commands:")
    print("=" * 70)
    print()
    
    while True:
        print("\nOptions:")
        print("  1. Start streaming (mock - will fail without camera)")
        print("  2. Stop streaming")
        print("  3. Get status")
        print("  4. List devices")
        print("  5. Shutdown daemon")
        print("  6. Exit client")
        print()
        
        choice = input("Enter choice (1-6): ").strip()
        print()
        
        if choice == "1":
            print("Starting stream...")
            try:
                result = client.start_stream(
                    device="/dev/video0",
                    name="DemoCamera",
                    resolution="1920x1080",
                    fps=30
                )
                print(f"✓ Stream started: {result['stream_name']}")
                print(f"  PID: {result['pid']}")
            except Exception as e:
                print(f"✗ Error: {e}")
        
        elif choice == "2":
            print("Stopping stream...")
            try:
                result = client.stop_stream()
                print(f"✓ Stream stopped")
            except Exception as e:
                print(f"✗ Error: {e}")
        
        elif choice == "3":
            print("Getting status...")
            try:
                status = client.get_stream_status()
                if status['streaming']:
                    print(f"✓ Streaming: {status['stream_name']}")
                    print(f"  Device: {status['device']}")
                    print(f"  Resolution: {status['resolution']}")
                    print(f"  FPS: {status['fps']}")
                    print(f"  Uptime: {status['uptime_seconds']:.1f} seconds")
                    print(f"  PID: {status['pid']}")
                else:
                    print("Not streaming")
                print(f"  State: {status['state']}")
            except Exception as e:
                print(f"✗ Error: {e}")
        
        elif choice == "4":
            print("Listing devices...")
            try:
                devices = client.list_devices()
                if devices:
                    for device in devices:
                        status_icon = "🔴" if device['in_use'] else "🟢"
                        print(f"{status_icon} {device['path']}: {device['name']}")
                else:
                    print("(No video devices found)")
            except Exception as e:
                print(f"✗ Error: {e}")
        
        elif choice == "5":
            print("Shutting down daemon...")
            try:
                result = client.shutdown_daemon()
                print(f"✓ Daemon shutting down...")
                time.sleep(1)
                break
            except Exception as e:
                print(f"✗ Error: {e}")
        
        elif choice == "6":
            print("Exiting client...")
            break
        
        else:
            print("Invalid choice")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 examples/daemon_demo.py daemon   # Run daemon")
        print("  python3 examples/daemon_demo.py client   # Run client")
        sys.exit(1)
    
    mode = sys.argv[1]
    
    if mode == "daemon":
        run_daemon()
    elif mode == "client":
        run_client()
    else:
        print(f"Unknown mode: {mode}")
        print("Use 'daemon' or 'client'")
        sys.exit(1)


if __name__ == '__main__':
    main()

