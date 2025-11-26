"""CLI interface for the sender application"""

import sys
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from exostream.common.logger import setup_logger, get_logger
from exostream.common.config import StreamConfig, VideoConfig, NDIConfig
from exostream.common.network import get_local_ip
from exostream.sender.webcam import WebcamManager
from exostream.sender.ffmpeg_encoder import FFmpegEncoder

console = Console()


@click.group()
def cli():
    """ExoStream - Stream webcam from Raspberry Pi using NDI"""
    pass


@cli.command()
@click.option('--device', '-d', default='/dev/video0', help='Video device path')
@click.option('--stream-name', '-n', default='ExoStream', help='NDI stream name')
@click.option('--groups', '-g', default=None, help='NDI groups (comma-separated)')
@click.option('--resolution', '-r', default='1920x1080', help='Video resolution (e.g., 1920x1080)')
@click.option('--fps', '-f', default=30, type=int, help='Frames per second')
@click.option('--preset', default=None, help='Quality preset (low, medium, high)')
@click.option('--raw-input', is_flag=True, help='Use raw YUYV input (lower CPU, try if stuttering)')
@click.option('--list-devices', '-l', is_flag=True, help='List available video devices and exit')
@click.option('--verbose', '-v', is_flag=True, help='Verbose logging')
def send(device, stream_name, groups, resolution, fps, preset, raw_input, list_devices, verbose):
    """Start streaming from webcam via NDI (NDI handles compression internally)
    
    Performance Tips:
    - For less stuttering, try lower resolution: --resolution 1280x720
    - Or lower framerate: --fps 25
    - 1080p30 works well on Pi 4, but may stutter on older hardware
    """
    
    # Setup logger
    log_level = "DEBUG" if verbose else "INFO"
    setup_logger("exostream", log_level)
    logger = get_logger(__name__)
    
    # Display banner
    console.print(Panel.fit(
        "[bold cyan]ExoStream Sender[/bold cyan]\n"
        "[dim]Streaming webcam over NDI[/dim]",
        border_style="cyan"
    ))
    
    # Detect webcams
    console.print("\n[yellow]Detecting video devices...[/yellow]")
    webcam_manager = WebcamManager()
    devices = webcam_manager.detect_devices()
    
    if not devices:
        console.print("[red]✗ No video devices found![/red]")
        sys.exit(1)
    
    # List devices if requested
    if list_devices:
        display_devices_table(devices)
        sys.exit(0)
    
    # Display found devices
    display_devices_table(devices)
    
    # Check if requested device exists
    selected_device = webcam_manager.get_device_by_path(device)
    if not selected_device:
        console.print(f"[red]✗ Device {device} not found![/red]")
        sys.exit(1)
    
    console.print(f"[green]✓ Using device: {selected_device.name} ({device})[/green]")
    
    # Create configuration
    try:
        if preset:
            config = StreamConfig.from_preset(preset, stream_name=stream_name)
            config.device = device
            if groups:
                config.ndi.groups = groups
        else:
            video_config = VideoConfig.from_resolution_string(
                resolution,
                fps=fps
            )
            ndi_config = NDIConfig(
                stream_name=stream_name,
                groups=groups
            )
            config = StreamConfig(
                video=video_config,
                ndi=ndi_config,
                device=device
            )
    except Exception as e:
        console.print(f"[red]✗ Invalid configuration: {e}[/red]")
        sys.exit(1)
    
    # Display configuration
    display_stream_config(config)
    
    # Display NDI stream information
    console.print(f"\n[bold green]NDI Stream Information:[/bold green]")
    console.print(f"  Stream Name: [yellow]{config.ndi.stream_name}[/yellow]")
    if config.ndi.groups:
        console.print(f"  Groups: [yellow]{config.ndi.groups}[/yellow]")
    console.print(f"  [dim]Discoverable on local network via NDI[/dim]")
    
    # Performance note
    if config.video.width >= 1920 and config.video.fps >= 30:
        perf_msg = f"\n[dim]Note: Sending raw frames at {config.video.resolution}@{config.video.fps}fps\n"
        if not raw_input:
            perf_msg += "If stuttering occurs, try: --raw-input (lower CPU)\n"
        perf_msg += "Or reduce load with: --resolution 1280x720 or --fps 25[/dim]"
        console.print(perf_msg)
    
    console.print("\n[yellow]Starting stream...[/yellow]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")
    
    # Create and start encoder
    try:
        # Use FFmpeg encoder with NDI (raw frame output)
        encoder = FFmpegEncoder(
            device_path=device,
            video_config=config.video,
            ndi_config=config.ndi,
            on_error=lambda msg: console.print(f"[red]Error: {msg}[/red]"),
            use_raw_input=raw_input
        )
        
        encoder.start()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping stream...[/yellow]")
    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        logger.exception("Unexpected error")
        sys.exit(1)
    
    console.print("[green]✓ Stream stopped[/green]")


def display_devices_table(devices):
    """Display available devices in a table"""
    table = Table(title="Available Video Devices", box=box.ROUNDED)
    table.add_column("Index", style="cyan")
    table.add_column("Device", style="magenta")
    table.add_column("Name", style="green")
    
    for i, device in enumerate(devices):
        table.add_row(str(i), device.path, device.name)
    
    console.print(table)


def display_stream_config(config: StreamConfig):
    """Display streaming configuration"""
    table = Table(title="Stream Configuration", box=box.ROUNDED, show_header=False)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="yellow")
    
    table.add_row("Protocol", "NDI")
    table.add_row("Resolution", config.video.resolution)
    table.add_row("FPS", str(config.video.fps))
    table.add_row("Stream Name", config.ndi.stream_name)
    if config.ndi.groups:
        table.add_row("Groups", config.ndi.groups)
    table.add_row("Compression", "NDI (automatic)")
    
    console.print(table)


if __name__ == '__main__':
    cli()

