#!/usr/bin/env python3
"""
Demo script for dynamic reconfiguration (graceful restart)

This demonstrates how settings can be changed on a live stream
with minimal downtime and automatic rollback on failure.

Usage:
    # Start daemon with network control
    exostreamd --network-control --verbose

    # Run demo (will start/stop stream automatically)
    python3 dynamic_reconfiguration_demo.py

    # Or connect to remote Pi
    python3 dynamic_reconfiguration_demo.py --host 192.168.1.100
"""

import sys
import time
import argparse
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich import box

# Add parent directory to path for imports
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from exostream.cli.network_client import (
    NetworkClientManager,
    NetworkConnectionError,
    NetworkRPCError
)

console = Console()


def print_header():
    """Print demo header"""
    console.print()
    console.print(Panel.fit(
        "[bold cyan]Dynamic Reconfiguration Demo[/bold cyan]\n"
        "[dim]Graceful restart with minimal downtime[/dim]",
        border_style="cyan"
    ))
    console.print()


def show_settings_comparison(old_settings: dict, new_settings: dict):
    """Show before/after settings comparison"""
    table = Table(title="Settings Comparison", box=box.ROUNDED)
    table.add_column("Setting", style="cyan")
    table.add_column("Before", style="yellow")
    table.add_column("After", style="green")
    
    # Compare key settings
    for key in ['resolution', 'fps', 'device']:
        old_val = old_settings.get(key, 'N/A')
        new_val = new_settings.get(key, 'N/A')
        
        # Highlight changes
        if old_val != new_val:
            table.add_row(
                key.title(),
                f"[yellow]{old_val}[/yellow]",
                f"[green bold]{new_val}[/green bold]"
            )
        else:
            table.add_row(
                key.title(),
                str(old_val),
                str(new_val)
            )
    
    console.print(table)


def test_graceful_restart(client: NetworkClientManager):
    """Test graceful restart with different scenarios"""
    
    console.print("\n[bold]Test 1: Resolution Change (1080p → 720p)[/bold]")
    console.print("[dim]This should restart quickly with minimal downtime[/dim]\n")
    
    try:
        # Get current settings
        old_settings = client.get_settings()
        
        # Make sure we're streaming first
        if not old_settings['streaming']:
            console.print("[yellow]Starting initial stream...[/yellow]")
            client.start_stream(
                device=old_settings['device'],
                name="Reconfig Test",
                resolution="1920x1080",
                fps=30
            )
            time.sleep(2)
            old_settings = client.get_settings()
        
        console.print(f"[cyan]Current: {old_settings['resolution']} @ {old_settings['fps']}fps[/cyan]")
        
        # Change resolution
        start_time = time.time()
        console.print("[yellow]Updating to 1280x720...[/yellow]")
        
        result = client.update_settings(
            resolution="1280x720",
            restart_if_streaming=True
        )
        
        downtime = time.time() - start_time
        
        # Show results
        new_settings = result.get('settings', {})
        restart_info = result.get('stream_info', {}).get('restart_info', {})
        
        console.print(f"[green]✓ Restart completed in {downtime:.2f}s[/green]")
        
        if restart_info:
            actual_downtime = restart_info.get('downtime_seconds', 0)
            console.print(f"[dim]Actual stream downtime: {actual_downtime:.2f}s[/dim]")
        
        show_settings_comparison(old_settings, new_settings)
        
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        return False
    
    # Wait a bit
    time.sleep(2)
    
    # Test 2: FPS change
    console.print("\n[bold]Test 2: FPS Change (30fps → 60fps)[/bold]")
    console.print("[dim]Testing framerate adjustment[/dim]\n")
    
    try:
        old_settings = client.get_settings()
        console.print(f"[cyan]Current: {old_settings['resolution']} @ {old_settings['fps']}fps[/cyan]")
        
        start_time = time.time()
        console.print("[yellow]Updating to 60fps...[/yellow]")
        
        result = client.update_settings(
            fps=60,
            restart_if_streaming=True
        )
        
        downtime = time.time() - start_time
        new_settings = result.get('settings', {})
        
        console.print(f"[green]✓ FPS updated in {downtime:.2f}s[/green]")
        console.print(f"[cyan]New: {new_settings['resolution']} @ {new_settings['fps']}fps[/cyan]")
        
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        return False
    
    # Wait a bit
    time.sleep(2)
    
    # Test 3: Multiple settings at once
    console.print("\n[bold]Test 3: Multiple Settings (720p @ 30fps)[/bold]")
    console.print("[dim]Changing resolution and FPS together[/dim]\n")
    
    try:
        old_settings = client.get_settings()
        
        start_time = time.time()
        console.print("[yellow]Updating to 1280x720 @ 30fps...[/yellow]")
        
        result = client.update_settings(
            resolution="1280x720",
            fps=30,
            restart_if_streaming=True
        )
        
        downtime = time.time() - start_time
        new_settings = result.get('settings', {})
        
        console.print(f"[green]✓ Multiple settings updated in {downtime:.2f}s[/green]")
        
        show_settings_comparison(old_settings, new_settings)
        
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        return False
    
    return True


def test_rollback_on_failure(client: NetworkClientManager):
    """Test that rollback works when invalid settings are provided"""
    
    console.print("\n[bold]Test 4: Rollback on Failure[/bold]")
    console.print("[dim]This should fail and rollback to previous settings[/dim]\n")
    
    try:
        # Get current settings
        old_settings = client.get_settings()
        console.print(f"[cyan]Current: {old_settings['resolution']} @ {old_settings['fps']}fps[/cyan]")
        
        # Try to set invalid FPS (will fail validation)
        console.print("[yellow]Attempting invalid FPS (999)...[/yellow]")
        
        try:
            result = client.update_settings(
                fps=999,  # Invalid!
                restart_if_streaming=True
            )
            console.print("[red]✗ Should have failed but didn't![/red]")
            return False
        except NetworkRPCError as e:
            console.print(f"[green]✓ Correctly rejected: {e.message}[/green]")
        
        # Verify stream is still running with old settings
        current_settings = client.get_settings()
        
        if current_settings['streaming']:
            console.print("[green]✓ Stream still running[/green]")
            console.print(f"[cyan]Settings unchanged: {current_settings['resolution']} @ {current_settings['fps']}fps[/cyan]")
        else:
            console.print("[red]✗ Stream was stopped![/red]")
            return False
        
        return True
        
    except Exception as e:
        console.print(f"[red]✗ Unexpected error: {e}[/red]")
        return False


def cleanup(client: NetworkClientManager):
    """Stop the stream"""
    console.print("\n[yellow]Cleaning up...[/yellow]")
    try:
        status = client.get_stream_status()
        if status['streaming']:
            client.stop_stream()
            console.print("[green]✓ Stream stopped[/green]")
    except Exception as e:
        console.print(f"[dim]Cleanup note: {e}[/dim]")


def main():
    """Main demo function"""
    parser = argparse.ArgumentParser(
        description="Dynamic Reconfiguration Demo"
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
    parser.add_argument(
        "--skip-cleanup",
        action="store_true",
        help="Don't stop stream after demo"
    )
    
    args = parser.parse_args()
    
    print_header()
    
    # Create client
    client = NetworkClientManager(args.host, args.port)
    
    # Test connection
    console.print(f"[yellow]Connecting to {args.host}:{args.port}...[/yellow]")
    if not client.is_connected():
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
    
    console.print("[green]✓ Connected![/green]")
    
    try:
        # Run tests
        success = True
        
        # Test graceful restart
        if not test_graceful_restart(client):
            success = False
        
        # Test rollback
        if not test_rollback_on_failure(client):
            success = False
        
        # Summary
        console.print()
        if success:
            console.print(Panel(
                "[green]✓ All tests passed![/green]\n\n"
                "[bold]Key Features Demonstrated:[/bold]\n"
                "• Graceful restart with minimal downtime\n"
                "• Settings validation before restart\n"
                "• Automatic rollback on failure\n"
                "• Stream continuity during changes",
                title="Demo Complete",
                border_style="green"
            ))
        else:
            console.print(Panel(
                "[yellow]⚠ Some tests failed[/yellow]\n\n"
                "Check logs for details",
                title="Demo Incomplete",
                border_style="yellow"
            ))
        
        # Cleanup
        if not args.skip_cleanup:
            cleanup(client)
        
        console.print()
        return 0 if success else 1
        
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted by user[/dim]")
        if not args.skip_cleanup:
            cleanup(client)
        return 0
    
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        console.print(f"\n[red]Fatal error: {e}[/red]\n")
        sys.exit(1)

