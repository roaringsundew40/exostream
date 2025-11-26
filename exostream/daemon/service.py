"""Streaming service - orchestrates camera, encoding, and state management"""

import os
import threading
import time
from typing import Optional, List, Dict, Any
from enum import Enum
import logging

from exostream.common.config import StreamConfig, VideoConfig, NDIConfig
from exostream.sender.ffmpeg_encoder import FFmpegEncoder
from exostream.sender.webcam import WebcamManager, WebcamDevice
from exostream.daemon.state_manager import StateManager
from exostream.common.protocol import RPCError

logger = logging.getLogger(__name__)


class StreamState(Enum):
    """Streaming state"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class StreamingError(Exception):
    """Base exception for streaming errors"""
    pass


class StreamAlreadyRunningError(StreamingError):
    """Raised when trying to start streaming but already running"""
    pass


class StreamNotRunningError(StreamingError):
    """Raised when trying to stop streaming but not running"""
    pass


class DeviceNotFoundError(StreamingError):
    """Raised when requested device is not found"""
    pass


class StreamingService:
    """
    Main streaming service that orchestrates:
    - Camera detection and management
    - FFmpeg encoder lifecycle
    - State persistence
    - Error handling and recovery
    """
    
    def __init__(self, state_manager: Optional[StateManager] = None):
        """
        Initialize streaming service
        
        Args:
            state_manager: StateManager instance (creates new if not provided)
        """
        self.state_manager = state_manager or StateManager()
        self.webcam_manager = WebcamManager()
        
        self._state = StreamState.STOPPED
        self._state_lock = threading.Lock()
        self._encoder: Optional[FFmpegEncoder] = None
        self._encoder_thread: Optional[threading.Thread] = None
        self._current_config: Optional[StreamConfig] = None
        self._errors: List[str] = []
        
        logger.info("StreamingService initialized")
    
    @property
    def state(self) -> StreamState:
        """Get current state"""
        with self._state_lock:
            return self._state
    
    def _set_state(self, new_state: StreamState):
        """Set state with logging"""
        with self._state_lock:
            old_state = self._state
            self._state = new_state
            logger.info(f"State transition: {old_state.value} -> {new_state.value}")
    
    def start_streaming(self, device: str, name: str, resolution: str = "1920x1080",
                       fps: int = 30, raw_input: bool = False,
                       groups: Optional[str] = None) -> Dict[str, Any]:
        """
        Start streaming
        
        Args:
            device: Device path (e.g., /dev/video0)
            name: Stream name
            resolution: Video resolution (e.g., 1920x1080)
            fps: Frames per second
            raw_input: Use raw YUYV input
            groups: NDI groups
        
        Returns:
            Result dictionary with status
        
        Raises:
            StreamAlreadyRunningError: If already streaming
            DeviceNotFoundError: If device not found
            StreamingError: For other errors
        """
        logger.info(f"Starting streaming: device={device}, name={name}, resolution={resolution}")
        
        # Check current state
        if self.state != StreamState.STOPPED:
            raise StreamAlreadyRunningError(
                f"Stream already running (state: {self.state.value})"
            )
        
        self._set_state(StreamState.STARTING)
        self._errors.clear()
        
        try:
            # Detect devices
            devices = self.webcam_manager.detect_devices()
            if not devices:
                raise DeviceNotFoundError("No video devices found")
            
            # Check if requested device exists
            selected_device = self.webcam_manager.get_device_by_path(device)
            if not selected_device:
                available = [d.path for d in devices]
                raise DeviceNotFoundError(
                    f"Device {device} not found. Available: {available}"
                )
            
            # Create configuration
            try:
                video_config = VideoConfig.from_resolution_string(
                    resolution,
                    fps=fps
                )
                ndi_config = NDIConfig(
                    stream_name=name,
                    groups=groups
                )
                config = StreamConfig(
                    video=video_config,
                    ndi=ndi_config,
                    device=device
                )
            except Exception as e:
                raise StreamingError(f"Invalid configuration: {e}")
            
            self._current_config = config
            
            # Create encoder
            def on_error(msg: str):
                logger.error(f"Encoder error: {msg}")
                self._errors.append(msg)
            
            self._encoder = FFmpegEncoder(
                device_path=device,
                video_config=config.video,
                ndi_config=config.ndi,
                on_error=on_error,
                use_raw_input=raw_input
            )
            
            # Start encoder in separate thread
            self._encoder_thread = threading.Thread(
                target=self._run_encoder,
                daemon=False
            )
            self._encoder_thread.start()
            
            # Give it a moment to start
            time.sleep(0.5)
            
            # Check if encoder started successfully
            if self._encoder.process is None or self._encoder.process.poll() is not None:
                self._set_state(StreamState.ERROR)
                raise StreamingError("FFmpeg failed to start")
            
            # Update state
            ffmpeg_pid = self._encoder.process.pid
            self.state_manager.set_streaming_active(config, ffmpeg_pid)
            self._set_state(StreamState.RUNNING)
            
            logger.info(f"Streaming started successfully: {name} (PID: {ffmpeg_pid})")
            
            return {
                "status": "started",
                "stream_name": name,
                "device": device,
                "resolution": resolution,
                "fps": fps,
                "pid": ffmpeg_pid
            }
            
        except Exception as e:
            self._set_state(StreamState.ERROR)
            self._cleanup_encoder()
            logger.error(f"Failed to start streaming: {e}")
            raise
    
    def stop_streaming(self) -> Dict[str, Any]:
        """
        Stop streaming
        
        Returns:
            Result dictionary
        
        Raises:
            StreamNotRunningError: If not currently streaming
        """
        logger.info("Stopping streaming")
        
        if self.state == StreamState.STOPPED:
            raise StreamNotRunningError("Stream is not running")
        
        self._set_state(StreamState.STOPPING)
        
        try:
            # Stop encoder
            if self._encoder:
                self._encoder.stop()
            
            # Wait for encoder thread to finish
            if self._encoder_thread and self._encoder_thread.is_alive():
                self._encoder_thread.join(timeout=10.0)
                if self._encoder_thread.is_alive():
                    logger.warning("Encoder thread did not stop gracefully")
            
            # Update state
            self.state_manager.set_streaming_inactive()
            self._set_state(StreamState.STOPPED)
            
            # Cleanup
            self._cleanup_encoder()
            
            logger.info("Streaming stopped successfully")
            
            return {
                "status": "stopped"
            }
            
        except Exception as e:
            logger.error(f"Error stopping streaming: {e}")
            self._set_state(StreamState.ERROR)
            raise StreamingError(f"Failed to stop streaming: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current streaming status
        
        Returns:
            Status dictionary
        """
        streaming_info = self.state_manager.get_streaming_info()
        streaming = streaming_info.get("active", False)
        
        status = {
            "streaming": streaming,
            "state": self.state.value
        }
        
        if streaming:
            status.update({
                "stream_name": streaming_info.get("stream_name"),
                "device": streaming_info.get("device"),
                "resolution": streaming_info.get("resolution"),
                "fps": streaming_info.get("fps"),
                "groups": streaming_info.get("groups"),
                "uptime_seconds": self.state_manager.get_streaming_uptime_seconds(),
                "pid": streaming_info.get("ffmpeg_pid")
            })
        
        if self._errors:
            status["errors"] = self._errors[-10:]  # Last 10 errors
        
        return status
    
    def list_devices(self) -> List[Dict[str, Any]]:
        """
        List available video devices
        
        Returns:
            List of device dictionaries
        """
        devices = self.webcam_manager.detect_devices()
        
        # Get currently used device
        streaming_info = self.state_manager.get_streaming_info()
        current_device = streaming_info.get("device") if streaming_info.get("active") else None
        
        result = []
        for device in devices:
            result.append({
                "path": device.path,
                "name": device.name,
                "index": device.index,
                "driver": device.driver,
                "card": device.card,
                "in_use": device.path == current_device
            })
        
        return result
    
    def _run_encoder(self):
        """Run encoder (called in separate thread)"""
        try:
            logger.debug("Encoder thread started")
            if self._encoder:
                self._encoder.start()
        except KeyboardInterrupt:
            logger.info("Encoder interrupted")
        except Exception as e:
            logger.error(f"Encoder error: {e}")
            self._errors.append(str(e))
            self._set_state(StreamState.ERROR)
        finally:
            logger.debug("Encoder thread finished")
    
    def _cleanup_encoder(self):
        """Clean up encoder resources"""
        self._encoder = None
        self._encoder_thread = None
        self._current_config = None
    
    def is_streaming(self) -> bool:
        """Check if currently streaming"""
        return self.state == StreamState.RUNNING
    
    def get_current_config(self) -> Optional[StreamConfig]:
        """Get current streaming configuration"""
        return self._current_config
    
    def get_errors(self) -> List[str]:
        """Get recent errors"""
        return list(self._errors)
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check
        
        Returns:
            Health status dictionary
        """
        health = {
            "healthy": True,
            "state": self.state.value,
            "streaming": self.is_streaming(),
            "issues": []
        }
        
        # Check if in error state
        if self.state == StreamState.ERROR:
            health["healthy"] = False
            health["issues"].append("Service in error state")
        
        # Check if encoder process is alive when streaming
        if self.state == StreamState.RUNNING:
            if self._encoder and self._encoder.process:
                if self._encoder.process.poll() is not None:
                    health["healthy"] = False
                    health["issues"].append("FFmpeg process died unexpectedly")
            else:
                health["healthy"] = False
                health["issues"].append("No encoder process while streaming")
        
        # Check for recent errors
        if self._errors:
            health["issues"].extend(self._errors[-3:])  # Last 3 errors
        
        return health
    
    def cleanup(self):
        """Clean up resources (call on daemon shutdown)"""
        logger.info("Cleaning up streaming service")
        
        try:
            if self.is_streaming():
                self.stop_streaming()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        logger.info("Streaming service cleanup complete")

