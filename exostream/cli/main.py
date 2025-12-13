"""Main CLI entry point for Exostream client"""

import sys
import time
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.text import Text

from exostream.cli.ipc_client import (
    IPCClientManager,
    DaemonNotRunningError,
    DaemonTimeoutError,
    DaemonRPCError
)
from exostream.common.logger import setup_logger, get_logger

console = Console()
logger = get_logger(__name__)

# Default socket path
DEFAULT_SOCKET = "/tmp/exostream.sock"


def get_client(socket_path: str = DEFAULT_SOCKET) -> IPCClientManager:
    """
    Get IPC client and check if daemon is running
    
    Args:
        socket_path: Path to Unix socket
    
    Returns:
        IPCClientManager instance
    
    Raises:
        SystemExit: If daemon is not running
    """
    client = IPCClientManager(socket_path)
    
    if not client.is_daemon_running():
        console.print()
        console.print(Panel(
            "[red]✗ Daemon is not running[/red]\n\n"
            "Start the daemon first:\n"
            f"  [cyan]exostreamd[/cyan]\n\n"
            "Or in background:\n"
            f"  [cyan]exostreamd &[/cyan]",
            title="Error",
            border_style="red"
        ))
        console.print()
        sys.exit(1)
    
    return client


def handle_error(e: Exception, command: str):
    """
    Handle and display errors nicely
    
    Args:
        e: Exception that occurred
        command: Command that failed
    """
    console.print()
    
    if isinstance(e, DaemonNotRunningError):
        console.print(Panel(
            "[red]✗ Daemon is not running[/red]\n\n"
            "Start the daemon first:\n"
            f"  [cyan]exostreamd[/cyan]",
            title="Error",
            border_style="red"
        ))
    elif isinstance(e, DaemonTimeoutError):
        console.print(Panel(
            "[red]✗ Daemon not responding[/red]\n\n"
            "The daemon is running but not responding.\n"
            "It may be stuck or overloaded.",
            title="Timeout Error",
            border_style="red"
        ))
    elif isinstance(e, DaemonRPCError):
        console.print(Panel(
            f"[red]✗ Command failed[/red]\n\n"
            f"Error: {e.message}\n"
            f"Code: {e.code}",
            title=f"Error: {command}",
            border_style="red"
        ))
    else:
        console.print(Panel(
            f"[red]✗ Unexpected error[/red]\n\n"
            f"{type(e).__name__}: {e}",
            title="Error",
            border_style="red"
        ))
    
    console.print()


@click.group()
@click.option('--socket', default=DEFAULT_SOCKET, help='Daemon socket path')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.version_option(version="0.3.0", prog_name="exostream")
@click.pass_context
def cli(ctx, socket, verbose):
    """
    Exostream - Professional NDI streaming from Raspberry Pi
    
    Control the Exostream daemon to stream video over NDI.
    """
    # Store options in context
    ctx.ensure_object(dict)
    ctx.obj['socket'] = socket
    ctx.obj['verbose'] = verbose
    
    # Setup logging if verbose
    if verbose:
        setup_logger("exostream", "DEBUG")


@cli.command()
@click.option('--device', '-d', default='/dev/video0', help='Video device path')
@click.option('--name', '-n', required=True, help='Stream name (visible to NDI clients)')
@click.option('--resolution', '-r', default='1920x1080', help='Video resolution')
@click.option('--fps', '-f', default=30, type=int, help='Frames per second')
@click.option('--raw-input', is_flag=True, help='Use raw YUYV input (720p recommended)')
@click.option('--groups', '-g', help='NDI groups (comma-separated)')
@click.pass_context
def start(ctx, device, name, resolution, fps, raw_input, groups):
    """Start streaming to NDI"""
    
    console.print()
    console.print(Panel.fit(
        "[bold cyan]Starting NDI Stream[/bold cyan]",
        border_style="cyan"
    ))
    console.print()
    
    try:
        socket_path = ctx.obj.get('socket', DEFAULT_SOCKET) if ctx.obj else DEFAULT_SOCKET
        client = get_client(socket_path)
        
        # Show configuration
        console.print("[yellow]Configuration:[/yellow]")
        console.print(f"  Stream Name: [cyan]{name}[/cyan]")
        console.print(f"  Device: [cyan]{device}[/cyan]")
        console.print(f"  Resolution: [cyan]{resolution}[/cyan]")
        console.print(f"  FPS: [cyan]{fps}[/cyan]")
        if groups:
            console.print(f"  Groups: [cyan]{groups}[/cyan]")
        if raw_input:
            console.print(f"  Input: [cyan]Raw YUYV[/cyan]")
        else:
            console.print(f"  Input: [cyan]MJPEG[/cyan]")
        console.print()
        
        # Start streaming
        with console.status("[yellow]Starting stream...[/yellow]"):
            result = client.start_stream(
                device=device,
                name=name,
                resolution=resolution,
                fps=fps,
                raw_input=raw_input,
                groups=groups
            )
        
        # Success!
        console.print(Panel(
            f"[green]✓ Stream started successfully[/green]\n\n"
            f"Stream Name: [cyan]{result['stream_name']}[/cyan]\n"
            f"Resolution: [cyan]{result['resolution']}[/cyan]\n"
            f"FPS: [cyan]{result['fps']}[/cyan]\n"
            f"Process ID: [cyan]{result['pid']}[/cyan]\n\n"
            f"[dim]The stream is now discoverable on your network via NDI.[/dim]",
            title="✓ Success",
            border_style="green"
        ))
        console.print()
        
        # Show next steps
        console.print("[dim]To stop this stream:[/dim]")
        console.print(f"  [cyan]exostream stop --device {device}[/cyan]")
        console.print("[dim]To stop all streams:[/dim]")
        console.print(f"  [cyan]exostream stop[/cyan]")
        console.print()
        
    except Exception as e:
        handle_error(e, "start")
        sys.exit(1)


@cli.command()
@click.option('--device', '-d', help='Device to stop (stops all streams if not specified)')
@click.option('--all', '-a', 'stop_all', is_flag=True, help='Stop all streams')
@click.pass_context
def stop(ctx, device, stop_all):
    """Stop streaming on one or all devices"""
    
    console.print()
    if device:
        console.print(Panel.fit(
            f"[bold yellow]Stopping Stream on {device}[/bold yellow]",
            border_style="yellow"
        ))
    else:
        console.print(Panel.fit(
            "[bold yellow]Stopping All Streams[/bold yellow]",
            border_style="yellow"
        ))
    console.print()
    
    try:
        socket_path = ctx.obj.get('socket', DEFAULT_SOCKET) if ctx.obj else DEFAULT_SOCKET
        client = get_client(socket_path)
        
        with console.status("[yellow]Stopping stream(s)...[/yellow]"):
            result = client.stop_stream(device=device)
        
        # Display result
        if result.get('count'):
            # Multiple streams stopped
            message = f"[green]✓ Stopped {result['count']} stream(s)[/green]"
            if result.get('errors'):
                message += f"\n\n[yellow]Errors:[/yellow]"
                for error in result['errors']:
                    message += f"\n  • {error}"
        else:
            # Single stream stopped
            if device:
                message = f"[green]✓ Stream stopped on {device}[/green]"
            else:
                message = "[green]✓ Stream stopped successfully[/green]"
        
        console.print(Panel(
            message,
            title="Success",
            border_style="green"
        ))
        console.print()
        
    except Exception as e:
        handle_error(e, "stop")
        sys.exit(1)


@cli.command()
@click.option('--watch', '-w', is_flag=True, help='Watch status (refresh every 2s)')
@click.pass_context
def status(ctx, watch):
    """Show streaming status"""
    
    try:
        socket_path = ctx.obj.get('socket', DEFAULT_SOCKET) if ctx.obj else DEFAULT_SOCKET
        client = get_client(socket_path)
        
        while True:
            # Clear screen if watching
            if watch:
                console.clear()
            
            console.print()
            console.print(Panel.fit(
                "[bold cyan]Exostream Status[/bold cyan]",
                border_style="cyan"
            ))
            console.print()
            
            # Get daemon status
            daemon_status = client.get_daemon_status()
            
            # Daemon info table
            daemon_table = Table(title="Daemon", box=box.ROUNDED, show_header=False)
            daemon_table.add_column("Property", style="cyan")
            daemon_table.add_column("Value", style="yellow")
            
            daemon_table.add_row("Status", "✓ Running" if daemon_status['running'] else "✗ Stopped")
            daemon_table.add_row("Version", daemon_status['version'])
            daemon_table.add_row("PID", str(daemon_status['pid']))
            uptime = daemon_status.get('uptime_seconds', 0)
            daemon_table.add_row("Uptime", format_uptime(uptime))
            
            # Health status
            health = daemon_status.get('health', {})
            health_icon = "✓" if health.get('healthy', False) else "✗"
            health_color = "green" if health.get('healthy', False) else "red"
            daemon_table.add_row("Health", f"[{health_color}]{health_icon} {health_color.title()}[/{health_color}]")
            
            console.print(daemon_table)
            console.print()
            
            # Get stream status
            stream_status = client.get_stream_status()
            
            # Check if we have multiple streams
            if 'streams' in stream_status and isinstance(stream_status['streams'], list):
                # Multiple streams
                if stream_status['streams']:
                    # Create table for each stream
                    for idx, stream in enumerate(stream_status['streams']):
                        stream_table = Table(
                            title=f"Stream {idx + 1} - {stream['device']}", 
                            box=box.ROUNDED, 
                            show_header=False
                        )
                        stream_table.add_column("Property", style="cyan")
                        stream_table.add_column("Value", style="yellow")
                        
                        stream_table.add_row("Status", "[green]✓ Streaming[/green]")
                        stream_table.add_row("Device", stream['device'])
                        stream_table.add_row("Name", stream['stream_name'])
                        stream_table.add_row("Resolution", stream['resolution'])
                        stream_table.add_row("FPS", str(stream['fps']))
                        if stream.get('groups'):
                            stream_table.add_row("Groups", stream['groups'])
                        stream_uptime = stream.get('uptime_seconds', 0)
                        stream_table.add_row("Uptime", format_uptime(stream_uptime))
                        stream_table.add_row("PID", str(stream.get('pid', 'N/A')))
                        
                        console.print(stream_table)
                        console.print()
                        
                        # Show errors if any
                        if stream.get('errors'):
                            console.print(f"[red]Recent Errors for {stream['device']}:[/red]")
                            for error in stream['errors'][-3:]:
                                console.print(f"  [red]•[/red] {error}")
                            console.print()
                    
                    # Show summary
                    console.print(f"[cyan]Total Active Streams:[/cyan] {stream_status['stream_count']}/{stream_status.get('max_streams', 3)}")
                    console.print()
                else:
                    # No streams
                    stream_table = Table(title="Streams", box=box.ROUNDED, show_header=False)
                    stream_table.add_column("Property", style="cyan")
                    stream_table.add_column("Value", style="yellow")
                    stream_table.add_row("Status", "[dim]Not streaming[/dim]")
                    console.print(stream_table)
                    console.print()
            else:
                # Single stream (legacy format or specific device)
                stream_table = Table(title="Stream", box=box.ROUNDED, show_header=False)
                stream_table.add_column("Property", style="cyan")
                stream_table.add_column("Value", style="yellow")
                
                if stream_status.get('streaming'):
                    stream_table.add_row("Status", "[green]✓ Streaming[/green]")
                    stream_table.add_row("Name", stream_status['stream_name'])
                    stream_table.add_row("Device", stream_status['device'])
                    stream_table.add_row("Resolution", stream_status['resolution'])
                    stream_table.add_row("FPS", str(stream_status['fps']))
                    if stream_status.get('groups'):
                        stream_table.add_row("Groups", stream_status['groups'])
                    stream_uptime = stream_status.get('uptime_seconds', 0)
                    stream_table.add_row("Uptime", format_uptime(stream_uptime))
                    stream_table.add_row("PID", str(stream_status.get('pid', 'N/A')))
                else:
                    stream_table.add_row("Status", "[dim]Not streaming[/dim]")
                
                console.print(stream_table)
                console.print()
                
                # Show errors if any
                if stream_status.get('errors'):
                    console.print("[red]Recent Errors:[/red]")
                    for error in stream_status['errors'][-3:]:
                        console.print(f"  [red]•[/red] {error}")
                    console.print()
            
            if not watch:
                break
            
            # Wait before refreshing
            console.print("[dim]Refreshing in 2 seconds... (Ctrl+C to stop)[/dim]")
            time.sleep(2)
            
    except KeyboardInterrupt:
        console.print("\n[dim]Stopped watching[/dim]\n")
    except Exception as e:
        handle_error(e, "status")
        sys.exit(1)


@cli.command()
@click.pass_context
def devices(ctx):
    """List available video devices"""
    
    console.print()
    console.print(Panel.fit(
        "[bold cyan]Available Video Devices[/bold cyan]",
        border_style="cyan"
    ))
    console.print()
    
    try:
        socket_path = ctx.obj.get('socket', DEFAULT_SOCKET) if ctx.obj else DEFAULT_SOCKET
        client = get_client(socket_path)
        
        with console.status("[yellow]Detecting devices...[/yellow]"):
            device_list = client.list_devices()
        
        if not device_list:
            console.print(Panel(
                "[yellow]No video devices found[/yellow]\n\n"
                "Make sure your camera is connected.",
                title="No Devices",
                border_style="yellow"
            ))
            console.print()
            return
        
        # Create table
        table = Table(box=box.ROUNDED)
        table.add_column("Status", style="bold", width=8)
        table.add_column("Device", style="cyan")
        table.add_column("Name", style="yellow")
        table.add_column("Index", style="dim")
        
        for device in device_list:
            status_icon = "🔴 IN USE" if device['in_use'] else "🟢 FREE"
            table.add_row(
                status_icon,
                device['path'],
                device['name'],
                str(device['index'])
            )
        
        console.print(table)
        console.print()
        
        # Show usage hint
        console.print("[dim]To start streaming:[/dim]")
        free_devices = [d for d in device_list if not d['in_use']]
        if free_devices:
            example_device = free_devices[0]['path']
            console.print(f"  [cyan]exostream start --name \"MyCamera\" --device {example_device}[/cyan]")
        
        # Show multi-stream capability
        used_count = len([d for d in device_list if d['in_use']])
        total_devices = len(device_list)
        if total_devices > 1:
            console.print()
            console.print(f"[dim]You can run up to 3 concurrent streams ({used_count} currently active)[/dim]")
        console.print()
        
    except Exception as e:
        handle_error(e, "devices")
        sys.exit(1)


@cli.group()
def daemon():
    """Daemon control commands"""
    pass


@daemon.command(name='start')
@click.option('--socket', default=DEFAULT_SOCKET, help='Daemon socket path')
@click.option('--state-dir', type=click.Path(), help='State directory')
@click.option('--verbose', '-v', is_flag=True, help='Verbose logging')
def daemon_start(socket, state_dir, verbose):
    """Start the daemon in background"""
    
    console.print()
    
    # Check if already running
    client = IPCClientManager(socket)
    if client.is_daemon_running():
        console.print(Panel(
            "[yellow]Daemon is already running[/yellow]\n\n"
            f"Socket: [cyan]{socket}[/cyan]\n\n"
            "Use [cyan]exostream daemon status[/cyan] to check status",
            title="Already Running",
            border_style="yellow"
        ))
        console.print()
        return
    
    # Start daemon in background
    import subprocess
    
    cmd = ['exostreamd', '--socket', socket]
    if state_dir:
        cmd.extend(['--state-dir', state_dir])
    if verbose:
        cmd.append('--verbose')
    
    try:
        with console.status("[yellow]Starting daemon...[/yellow]"):
            # Start daemon in background, detached from terminal
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True  # Detach from terminal
            )
            
            # Wait a moment for it to start
            time.sleep(1.0)
            
            # Check if it's running
            if client.is_daemon_running():
                console.print(Panel(
                    f"[green]✓ Daemon started successfully[/green]\n\n"
                    f"Socket: [cyan]{socket}[/cyan]\n\n"
                    "[dim]The daemon is running in the background.[/dim]",
                    title="Success",
                    border_style="green"
                ))
            else:
                console.print(Panel(
                    "[red]✗ Daemon failed to start[/red]\n\n"
                    "Try starting manually with verbose output:\n"
                    f"  [cyan]exostreamd --verbose[/cyan]",
                    title="Error",
                    border_style="red"
                ))
                sys.exit(1)
    except FileNotFoundError:
        console.print(Panel(
            "[red]✗ exostreamd command not found[/red]\n\n"
            "Make sure exostream is installed:\n"
            "  [cyan]pip3 install -e . --user[/cyan]",
            title="Error",
            border_style="red"
        ))
        sys.exit(1)
    except Exception as e:
        console.print(Panel(
            f"[red]✗ Failed to start daemon[/red]\n\n"
            f"Error: {e}",
            title="Error",
            border_style="red"
        ))
        sys.exit(1)
    
    console.print()


@daemon.command(name='status')
@click.option('--socket', default=DEFAULT_SOCKET, help='Daemon socket path')
def daemon_status(socket):
    """Show daemon status"""
    
    console.print()
    
    try:
        client = IPCClientManager(socket)
        
        if not client.is_daemon_running():
            console.print(Panel(
                "[yellow]✗ Daemon is not running[/yellow]\n\n"
                "Start the daemon:\n"
                f"  [cyan]exostreamd[/cyan]",
                title="Daemon Status",
                border_style="yellow"
            ))
            console.print()
            return
        
        # Get full status
        status = client.get_daemon_status()
        
        # Display status
        console.print(Panel(
            f"[green]✓ Daemon is running[/green]\n\n"
            f"Version: [cyan]{status['version']}[/cyan]\n"
            f"PID: [cyan]{status['pid']}[/cyan]\n"
            f"Uptime: [cyan]{format_uptime(status.get('uptime_seconds', 0))}[/cyan]\n"
            f"Socket: [cyan]{socket}[/cyan]",
            title="Daemon Status",
            border_style="green"
        ))
        console.print()
        
        # Health status
        health = status.get('health', {})
        if health.get('healthy'):
            console.print("[green]✓ Health: Good[/green]")
        else:
            console.print("[red]✗ Health: Issues detected[/red]")
            for issue in health.get('issues', []):
                console.print(f"  [red]•[/red] {issue}")
        console.print()
        
    except Exception as e:
        console.print(Panel(
            f"[red]✗ Could not connect to daemon[/red]\n\n"
            f"Error: {e}",
            title="Error",
            border_style="red"
        ))
        console.print()


@daemon.command(name='stop')
@click.option('--socket', default=DEFAULT_SOCKET, help='Daemon socket path')
def daemon_stop(socket):
    """Stop the daemon"""
    
    console.print()
    
    try:
        client = IPCClientManager(socket)
        
        if not client.is_daemon_running():
            console.print(Panel(
                "[yellow]Daemon is not running[/yellow]",
                title="Info",
                border_style="yellow"
            ))
            console.print()
            return
        
        with console.status("[yellow]Stopping daemon...[/yellow]"):
            client.shutdown_daemon()
            time.sleep(0.5)
        
        console.print(Panel(
            "[green]✓ Daemon stopped[/green]",
            title="Success",
            border_style="green"
        ))
        console.print()
        
    except Exception as e:
        handle_error(e, "stop")
        sys.exit(1)


@daemon.command(name='shutdown')
@click.option('--socket', default=DEFAULT_SOCKET, help='Daemon socket path')
def daemon_shutdown(socket):
    """Shutdown the daemon (alias for stop)"""
    # Just call stop
    import click
    ctx = click.get_current_context()
    ctx.invoke(daemon_stop, socket=socket)


@daemon.command(name='ping')
@click.option('--socket', default=DEFAULT_SOCKET, help='Daemon socket path')
def daemon_ping(socket):
    """Ping the daemon (health check)"""
    
    try:
        client = IPCClientManager(socket)
        
        if client.ping():
            console.print("[green]✓ Daemon is responding[/green]")
        else:
            console.print("[red]✗ Daemon did not respond[/red]")
            sys.exit(1)
    except DaemonNotRunningError:
        console.print("[red]✗ Daemon is not running[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option('--verbose', '-v', is_flag=True, help='Show detailed test output')
def test(verbose):
    """Run all Exostream tests"""
    from exostream.testing import run_tests
    
    console.print()
    console.print(Panel.fit(
        "[bold cyan]Running Exostream Tests[/bold cyan]",
        border_style="cyan"
    ))
    console.print()
    
    # Run tests
    with console.status("[yellow]Running tests...[/yellow]", spinner="dots"):
        success, results = run_tests(verbose=verbose)
    
    # Display results
    total = results['total']
    passed = results['passed']
    failed = results['failed']
    errors = results['errors']
    skipped = results['skipped']
    
    # Create summary table
    table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED)
    table.add_column("Category", style="cyan")
    table.add_column("Count", justify="right")
    
    table.add_row("Total Tests", str(total))
    table.add_row("Passed", f"[green]{passed}[/green]")
    
    if failed > 0:
        table.add_row("Failed", f"[red]{failed}[/red]")
    if errors > 0:
        table.add_row("Errors", f"[red]{errors}[/red]")
    if skipped > 0:
        table.add_row("Skipped", f"[yellow]{skipped}[/yellow]")
    
    console.print(table)
    console.print()
    
    # Show detailed results if verbose
    if verbose and results.get('test_results'):
        console.print("[bold]Test Details:[/bold]")
        console.print()
        
        for test_name, status, message in results['test_results']:
            if status == 'PASS':
                console.print(f"  [green]✓[/green] {test_name}")
            elif status == 'FAIL':
                console.print(f"  [red]✗[/red] {test_name}")
                if message:
                    console.print(f"    [dim]{message[:100]}...[/dim]" if len(message) > 100 else f"    [dim]{message}[/dim]")
            elif status == 'ERROR':
                console.print(f"  [red]✗[/red] {test_name} [red](ERROR)[/red]")
                if message:
                    console.print(f"    [dim]{message[:100]}...[/dim]" if len(message) > 100 else f"    [dim]{message}[/dim]")
            elif status == 'SKIP':
                console.print(f"  [yellow]-[/yellow] {test_name} [yellow](SKIPPED)[/yellow]")
        
        console.print()
    
    # Final result
    if success:
        console.print(Panel(
            f"[bold green]✓ All tests passed![/bold green]\n\n"
            f"{passed}/{total} tests successful",
            title="Success",
            border_style="green"
        ))
        console.print()
        sys.exit(0)
    else:
        console.print(Panel(
            f"[bold red]✗ Tests failed[/bold red]\n\n"
            f"Passed: {passed}/{total}\n"
            f"Failed: {failed}\n"
            f"Errors: {errors}",
            title="Failed",
            border_style="red"
        ))
        console.print()
        
        if not verbose:
            console.print("[dim]Run with [cyan]--verbose[/cyan] to see detailed output[/dim]")
            console.print()
        
        sys.exit(1)


def format_uptime(seconds: float) -> str:
    """Format uptime in human-readable form"""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.0f}m"
    elif seconds < 86400:
        hours = seconds / 3600
        minutes = (seconds % 3600) / 60
        return f"{hours:.0f}h {minutes:.0f}m"
    else:
        days = seconds / 86400
        hours = (seconds % 86400) / 3600
        return f"{days:.0f}d {hours:.0f}h"


if __name__ == '__main__':
    cli(obj={})

