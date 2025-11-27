#!/usr/bin/env python3
"""
Demo script for network control of Exostream

This demonstrates how to remotely control an Exostream daemon
running on a Raspberry Pi (or any other machine) via network.

Usage:
    # Connect to daemon on localhost
    python3 network_control_demo.py

    # Connect to daemon on another machine
    python3 network_control_demo.py --host 192.168.1.100
"""

import sys
import time
import argparse
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

# Add parent directory to path for imports
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from exostream.cli.network_client import (
    NetworkClientManager,
    NetworkConnectionError,
    NetworkTimeoutError,
    NetworkRPCError
)

console = Console()


def print_header():
    """Print demo header"""
    console.print()
    console.print(Panel.fit(
        "[bold cyan]Exostream Network Control Demo[/bold cyan]\n"
        "[dim]Remote camera control via TCP[/dim]",
        border_style="cyan"
    ))
    console.print()


def test_connection(client: NetworkClientManager, host: str, port: int):
    """Test connection to server"""
    console.print(f"[yellow]Testing connection to {host}:{port}...[/yellow]")
    
    try:
        if client.ping():
            console.print(f"[green]✓ Connected successfully![/green]")
            return True
        else:
            console.print(f"[red]✗ Server not responding[/red]")
            return False
    except NetworkConnectionError as e:
        console.print(f"[red]✗ Connection failed: {e}[/red]")
        return False
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        return False


def show_daemon_status(client: NetworkClientManager):
    """Show daemon status"""
    console.print("\n[bold]1. Daemon Status[/bold]")
    
    try:
        status = client.get_daemon_status()
        
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="yellow")
        
        table.add_row("Running", "✓ Yes" if status['running'] else "✗ No")
        table.add_row("Version", status['version'])
        table.add_row("PID", str(status['pid']))
        
        uptime = status.get('uptime_seconds', 0)
        if uptime < 60:
            uptime_str = f"{uptime:.0f}s"
        elif uptime < 3600:
            uptime_str = f"{uptime / 60:.0f}m"
        else:
            uptime_str = f"{uptime / 3600:.1f}h"
        table.add_row("Uptime", uptime_str)
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error getting daemon status: {e}[/red]")


def show_current_settings(client: NetworkClientManager):
    """Show current settings"""
    console.print("\n[bold]2. Current Settings[/bold]")
    
    try:
        settings = client.get_settings()
        
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="yellow")
        
        table.add_row("Device", settings.get('device', 'N/A'))
        table.add_row("Stream Name", settings.get('name') or '[dim]Not set[/dim]')
        table.add_row("Resolution", settings.get('resolution', 'N/A'))
        table.add_row("FPS", str(settings.get('fps', 'N/A')))
        table.add_row("Input Format", "Raw YUYV" if settings.get('raw_input') else "MJPEG")
        table.add_row("NDI Groups", settings.get('groups') or '[dim]None[/dim]')
        table.add_row("Streaming", "✓ Yes" if settings.get('streaming') else "✗ No")
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error getting settings: {e}[/red]")


def show_available_options(client: NetworkClientManager):
    """Show available configuration options"""
    console.print("\n[bold]3. Available Options[/bold]")
    
    try:
        options = client.get_available_options()
        
        # Devices
        console.print("\n[cyan]Devices:[/cyan]")
        devices = options.get('devices', [])
        if devices:
            for device in devices:
                status = "🔴 IN USE" if device.get('in_use') else "🟢 FREE"
                console.print(f"  {status} {device['path']} - {device['name']}")
        else:
            console.print("  [dim]No devices found[/dim]")
        
        # Resolutions
        console.print("\n[cyan]Resolutions:[/cyan]")
        resolutions = options.get('resolutions', [])
        console.print(f"  {', '.join(resolutions)}")
        
        # FPS options
        console.print("\n[cyan]FPS Options:[/cyan]")
        fps_options = options.get('fps_options', [])
        console.print(f"  {', '.join(map(str, fps_options))}")
        
    except Exception as e:
        console.print(f"[red]Error getting options: {e}[/red]")


def demo_update_settings(client: NetworkClientManager):
    """Demo updating settings"""
    console.print("\n[bold]4. Update Settings Demo[/bold]")
    
    # Get current settings
    try:
        current = client.get_settings()
        console.print(f"\n[yellow]Current FPS: {current.get('fps')}[/yellow]")
        
        # Update to 60 FPS
        console.print("[yellow]Updating FPS to 60...[/yellow]")
        result = client.update_settings(fps=60, restart_if_streaming=False)
        
        console.print(f"[green]✓ Settings updated: {result['status']}[/green]")
        
        # Show new settings
        new_settings = result.get('settings', {})
        console.print(f"[yellow]New FPS: {new_settings.get('fps')}[/yellow]")
        
        # Revert back
        console.print(f"\n[yellow]Reverting to {current.get('fps')} FPS...[/yellow]")
        client.update_settings(fps=current.get('fps'), restart_if_streaming=False)
        console.print("[green]✓ Settings reverted[/green]")
        
    except Exception as e:
        console.print(f"[red]Error updating settings: {e}[/red]")


def main():
    """Main demo function"""
    parser = argparse.ArgumentParser(
        description="Exostream Network Control Demo"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Daemon hostname or IP (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9023,
        help="Daemon port (default: 9023)"
    )
    
    args = parser.parse_args()
    
    print_header()
    
    # Create client
    client = NetworkClientManager(args.host, args.port)
    
    # Test connection
    if not test_connection(client, args.host, args.port):
        console.print()
        console.print(Panel(
            "[red]Could not connect to daemon[/red]\n\n"
            "Make sure the daemon is running with network control enabled:\n"
            f"  [cyan]exostreamd --network-control --network-port {args.port}[/cyan]",
            title="Connection Failed",
            border_style="red"
        ))
        console.print()
        return 1
    
    # Show daemon info
    show_daemon_status(client)
    
    # Show current settings
    show_current_settings(client)
    
    # Show available options
    show_available_options(client)
    
    # Demo updating settings
    demo_update_settings(client)
    
    console.print()
    console.print(Panel.fit(
        "[green]✓ Demo completed successfully![/green]",
        border_style="green"
    ))
    console.print()
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted by user[/dim]\n")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]\n")
        sys.exit(1)

