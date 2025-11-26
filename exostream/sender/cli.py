"""CLI interface for the sender application"""

import sys
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from exostream.common.logger import setup_logger, get_logger
from exostream.common.config import StreamConfig, VideoConfig, SRTConfig
from exostream.common.network import is_port_available, get_local_ip
from exostream.sender.webcam import WebcamManager
from exostream.sender.encoder import StreamEncoder
from exostream.sender.ffmpeg_encoder import FFmpegEncoder

console = Console()


@click.group()
def cli():
    """ExoStream - Stream webcam from Raspberry Pi using GStreamer and SRT"""
    pass


@cli.command()
@click.option('--device', '-d', default='/dev/video0', help='Video device path')
@click.option('--port', '-p', default=9000, type=int, help='SRT port to listen on')
@click.option('--resolution', '-r', default='1920x1080', help='Video resolution (e.g., 1920x1080)')
@click.option('--fps', '-f', default=30, type=int, help='Frames per second')
@click.option('--bitrate', '-b', default=4000, type=int, help='Video bitrate in kbps')
@click.option('--preset', default=None, help='Quality preset (low, medium, high)')
@click.option('--passphrase', default=None, help='SRT encryption passphrase')
@click.option('--software-encoder', '-s', is_flag=True, help='Use software encoder (GStreamer x264enc)')
@click.option('--use-ffmpeg', is_flag=True, help='Use FFmpeg instead of GStreamer (try hardware encoder first)')
@click.option('--ffmpeg-software', is_flag=True, help='Use FFmpeg with software encoder')
@click.option('--udp', is_flag=True, help='Use UDP instead of SRT (lower latency, recommended for local network)')
@click.option('--list-devices', '-l', is_flag=True, help='List available video devices and exit')
@click.option('--verbose', '-v', is_flag=True, help='Verbose logging')
def send(device, port, resolution, fps, bitrate, preset, passphrase, software_encoder, use_ffmpeg, ffmpeg_software, udp, list_devices, verbose):
    """Start streaming from webcam"""
    
    # Setup logger
    log_level = "DEBUG" if verbose else "INFO"
    setup_logger("exostream", log_level)
    logger = get_logger(__name__)
    
    # Display banner
    console.print(Panel.fit(
        "[bold cyan]ExoStream Sender[/bold cyan]\n"
        "[dim]Streaming webcam over SRT[/dim]",
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
    
    # Check port availability
    if not is_port_available(port):
        console.print(f"[red]✗ Port {port} is already in use![/red]")
        sys.exit(1)
    
    # Create configuration
    try:
        if preset:
            config = StreamConfig.from_preset(preset)
            config.device = device
            config.srt.port = port
        else:
            video_config = VideoConfig.from_resolution_string(
                resolution,
                fps=fps,
                bitrate=bitrate
            )
            srt_config = SRTConfig(
                port=port,
                passphrase=passphrase
            )
            config = StreamConfig(
                video=video_config,
                srt=srt_config,
                device=device
            )
    except Exception as e:
        console.print(f"[red]✗ Invalid configuration: {e}[/red]")
        sys.exit(1)
    
    # Display configuration
    display_stream_config(config)
    
    # Get local IP for display
    local_ip = get_local_ip()
    if local_ip:
        console.print(f"\n[bold green]Stream is available at:[/bold green]")
        console.print(f"  srt://{local_ip}:{port}")
        if passphrase:
            console.print(f"  [dim]Passphrase: {passphrase}[/dim]")
    
    console.print("\n[yellow]Starting stream...[/yellow]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")
    
    # Create and start encoder
    try:
        if use_ffmpeg or ffmpeg_software or udp:
            # Use FFmpeg encoder
            encoder = FFmpegEncoder(
                device_path=device,
                video_config=config.video,
                srt_config=config.srt,
                on_error=lambda msg: console.print(f"[red]Error: {msg}[/red]"),
                use_hardware=not ffmpeg_software,  # Hardware unless --ffmpeg-software
                use_udp=udp  # Use UDP if requested
            )
        else:
            # Use GStreamer encoder
            encoder = StreamEncoder(
                device_path=device,
                video_config=config.video,
                srt_config=config.srt,
                on_error=lambda msg: console.print(f"[red]Error: {msg}[/red]"),
                use_software_encoder=software_encoder
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
    
    table.add_row("Resolution", config.video.resolution)
    table.add_row("FPS", str(config.video.fps))
    table.add_row("Bitrate", f"{config.video.bitrate} kbps")
    table.add_row("SRT Port", str(config.srt.port))
    table.add_row("SRT Latency", f"{config.srt.latency} ms")
    table.add_row("Encryption", "Enabled" if config.srt.passphrase else "Disabled")
    
    console.print(table)


if __name__ == '__main__':
    cli()

