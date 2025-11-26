"""FFmpeg-based encoder for hardware H.264 encoding"""

import subprocess
import signal
import sys
import shlex
from typing import Optional, Callable
from exostream.common.logger import get_logger
from exostream.common.config import VideoConfig, SRTConfig

logger = get_logger(__name__)


class FFmpegEncoder:
    """Handles video encoding using FFmpeg with hardware acceleration"""
    
    def __init__(
        self,
        device_path: str,
        video_config: VideoConfig,
        srt_config: SRTConfig,
        on_error: Optional[Callable] = None,
        use_hardware: bool = True
    ):
        """
        Initialize the FFmpeg encoder
        
        Args:
            device_path: Path to video device (e.g., /dev/video0)
            video_config: Video encoding configuration
            srt_config: SRT streaming configuration
            on_error: Callback function for errors
            use_hardware: Use h264_v4l2m2m hardware encoder
        """
        self.device_path = device_path
        self.video_config = video_config
        self.srt_config = srt_config
        self.on_error = on_error
        self.use_hardware = use_hardware
        
        self.process: Optional[subprocess.Popen] = None
        
        # Determine encoder
        self.encoder = "h264_v4l2m2m" if use_hardware else "libx264"
        
        if use_hardware:
            logger.info("Using FFmpeg with hardware encoder (h264_v4l2m2m)")
        else:
            logger.info("Using FFmpeg with software encoder (libx264)")
    
    def build_command(self) -> list:
        """
        Build the FFmpeg command
        
        Returns:
            List of command arguments
        """
        srt_url = f"srt://0.0.0.0:{self.srt_config.port}?mode=listener&latency={self.srt_config.latency * 1000}"
        
        if self.srt_config.passphrase:
            srt_url += f"&passphrase={self.srt_config.passphrase}"
        
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "info",
            
            # Input from V4L2 device (MJPEG from Logitech camera)
            "-f", "v4l2",
            "-input_format", "mjpeg",
            "-video_size", f"{self.video_config.width}x{self.video_config.height}",
            "-framerate", str(self.video_config.fps),
            "-i", self.device_path,
        ]
        
        # Encoder-specific settings
        if self.use_hardware:
            # Hardware encoder (h264_v4l2m2m)
            # CRITICAL: Hardware encoder requires yuv420p pixel format
            cmd.extend([
                "-pix_fmt", "yuv420p",  # Convert from yuvj422p (MJPEG) to yuv420p
                "-c:v", "h264_v4l2m2m",
                "-b:v", f"{self.video_config.bitrate}k",
                "-g", str(self.video_config.fps * 2),  # Keyframe every 2 seconds
                # Don't set profile - h264_v4l2m2m handles this automatically
                # Don't set maxrate/bufsize - can cause issues with hardware encoder
                # Don't set bf - hardware encoder decides this
            ])
        else:
            # Software encoder (libx264)
            cmd.extend([
                "-c:v", "libx264",
                "-b:v", f"{self.video_config.bitrate}k",
                "-maxrate", f"{self.video_config.bitrate}k",
                "-bufsize", f"{self.video_config.bitrate * 2}k",
                "-preset", "veryfast",
                "-tune", "zerolatency",
                "-g", str(self.video_config.fps * 2),
                "-bf", "0",
                "-profile:v", "baseline",
                "-x264-params", "keyint=%d:min-keyint=%d:scenecut=0" % (
                    self.video_config.fps * 2,
                    self.video_config.fps
                ),
            ])
        
        # Output format and optimization
        # Try raw H.264 first - sometimes works better with SRT
        cmd.extend([
            "-f", "h264",  # Raw H.264 stream
            srt_url
        ])
        
        return cmd
    
    def start(self):
        """Start the FFmpeg encoding process"""
        cmd = self.build_command()
        
        logger.info(f"Starting FFmpeg encoder...")
        logger.debug(f"Command: {' '.join(cmd)}")
        
        try:
            # Start FFmpeg process
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            logger.info(f"FFmpeg encoder started (PID: {self.process.pid})")
            logger.info(f"Stream is available at: srt://0.0.0.0:{self.srt_config.port}")
            logger.info(f"Full command: {' '.join(cmd)}")
            
            # Monitor stderr in real-time
            try:
                for line in self.process.stderr:
                    line = line.strip()
                    
                    # Log important FFmpeg messages
                    if "error" in line.lower() or "failed" in line.lower():
                        logger.error(f"FFmpeg: {line}")
                        if self.on_error:
                            self.on_error(line)
                    elif "warning" in line.lower():
                        logger.warning(f"FFmpeg: {line}")
                    elif any(x in line for x in ["frame=", "fps=", "bitrate=", "speed="]):
                        # Progress info - only log periodically
                        logger.debug(f"FFmpeg: {line}")
                    elif line:
                        logger.info(f"FFmpeg: {line}")
                
            except KeyboardInterrupt:
                logger.info("Interrupted by user")
            finally:
                self.stop()
                
        except FileNotFoundError:
            error_msg = "FFmpeg not found! Install with: sudo apt-get install ffmpeg"
            logger.error(error_msg)
            if self.on_error:
                self.on_error(error_msg)
            raise RuntimeError(error_msg)
        
        except Exception as e:
            logger.error(f"Failed to start FFmpeg: {e}")
            if self.on_error:
                self.on_error(str(e))
            raise
    
    def stop(self):
        """Stop the FFmpeg encoding process"""
        if self.process and self.process.poll() is None:
            logger.info("Stopping FFmpeg encoder...")
            
            try:
                # Send SIGINT (like Ctrl+C) for graceful shutdown
                self.process.send_signal(signal.SIGINT)
                
                # Wait up to 5 seconds for graceful shutdown
                try:
                    self.process.wait(timeout=5)
                    logger.info("FFmpeg stopped gracefully")
                except subprocess.TimeoutExpired:
                    # Force kill if not responding
                    logger.warning("FFmpeg not responding, forcing termination")
                    self.process.kill()
                    self.process.wait()
                    logger.info("FFmpeg terminated")
                    
            except Exception as e:
                logger.error(f"Error stopping FFmpeg: {e}")
    
    def get_stats(self) -> dict:
        """
        Get streaming statistics
        
        Returns:
            Dictionary with statistics
        """
        stats = {
            'bitrate': self.video_config.bitrate,
            'resolution': self.video_config.resolution,
            'fps': self.video_config.fps,
            'encoder': self.encoder,
            'device': self.device_path,
            'backend': 'ffmpeg',
        }
        
        return stats

