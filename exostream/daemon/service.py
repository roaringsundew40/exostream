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
    - FFmpeg encoder lifecycle (supports up to 3 concurrent streams)
    - State persistence
    - Error handling and recovery
    
    Multi-Stream Architecture:
    - Manages up to MAX_STREAMS (3) concurrent video streams
    - Each stream is independent with its own encoder, thread, and configuration
    - Streams are keyed by device path (e.g., /dev/video0)
    - Each device can only have one active stream at a time
    - Provides granular control: start/stop individual streams or all at once
    """
    
    MAX_STREAMS = 3  # Maximum number of concurrent streams
    
    def __init__(self, state_manager: Optional[StateManager] = None):
        """
        Initialize streaming service
        
        Args:
            state_manager: StateManager instance (creates new if not provided)
        """
        self.state_manager = state_manager or StateManager()
        self.webcam_manager = WebcamManager()
        
        self._state_lock = threading.Lock()
        # Dictionary of active streams keyed by device path
        self._streams: Dict[str, Dict[str, Any]] = {}
        # Each stream dict contains: encoder, thread, config, raw_input, state, errors
        
        logger.info(f"StreamingService initialized (max {self.MAX_STREAMS} concurrent streams)")
    
    def _get_stream_state(self, device: str) -> StreamState:
        """Get state for a specific stream"""
        with self._state_lock:
            if device in self._streams:
                return self._streams[device].get("state", StreamState.STOPPED)
            return StreamState.STOPPED
    
    def _set_stream_state(self, device: str, new_state: StreamState):
        """Set state for a specific stream"""
        with self._state_lock:
            if device in self._streams:
                old_state = self._streams[device].get("state", StreamState.STOPPED)
                self._streams[device]["state"] = new_state
                logger.info(f"Stream {device}: {old_state.value} -> {new_state.value}")
    
    def start_streaming(self, device: str, name: str, resolution: str = "1920x1080",
                       fps: int = 30, raw_input: bool = False,
                       groups: Optional[str] = None) -> Dict[str, Any]:
        """
        Start streaming on a specific device
        
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
            StreamAlreadyRunningError: If device already streaming or max streams reached
            DeviceNotFoundError: If device not found
            StreamingError: For other errors
        """
        logger.info(f"Starting streaming: device={device}, name={name}, resolution={resolution}")
        
        with self._state_lock:
            # Check if device is already streaming
            if device in self._streams:
                raise StreamAlreadyRunningError(
                    f"Device {device} is already streaming"
                )
            
            # Check max streams limit
            if len(self._streams) >= self.MAX_STREAMS:
                raise StreamAlreadyRunningError(
                    f"Maximum number of streams ({self.MAX_STREAMS}) already running. "
                    f"Stop a stream before starting a new one."
                )
        
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
            
            # Create stream entry
            stream_errors: List[str] = []
            
            # Create encoder
            def on_error(msg: str):
                logger.error(f"Encoder error ({device}): {msg}")
                stream_errors.append(msg)
            
            encoder = FFmpegEncoder(
                device_path=device,
                video_config=config.video,
                ndi_config=config.ndi,
                on_error=on_error,
                use_raw_input=raw_input
            )
            
            # Start encoder in separate thread
            encoder_thread = threading.Thread(
                target=self._run_encoder,
                args=(device,),
                daemon=False,
                name=f"encoder-{device}"
            )
            
            # Add to streams dictionary
            with self._state_lock:
                self._streams[device] = {
                    "encoder": encoder,
                    "thread": encoder_thread,
                    "config": config,
                    "raw_input": raw_input,
                    "state": StreamState.STARTING,
                    "errors": stream_errors
                }
            
            # Start the thread
            encoder_thread.start()
            
            # Give it a brief moment to start
            time.sleep(0.2)
            
            # Check if encoder started successfully
            if encoder.process is None or encoder.process.poll() is not None:
                with self._state_lock:
                    if device in self._streams:
                        self._streams[device]["state"] = StreamState.ERROR
                raise StreamingError("FFmpeg failed to start")
            
            # Update state
            ffmpeg_pid = encoder.process.pid
            self.state_manager.set_streaming_active(config, ffmpeg_pid, raw_input)
            
            with self._state_lock:
                if device in self._streams:
                    self._streams[device]["state"] = StreamState.RUNNING
            
            logger.info(f"Streaming started successfully: {name} on {device} (PID: {ffmpeg_pid})")
            
            return {
                "status": "started",
                "stream_name": name,
                "device": device,
                "resolution": resolution,
                "fps": fps,
                "pid": ffmpeg_pid
            }
            
        except Exception as e:
            # Clean up on error
            with self._state_lock:
                if device in self._streams:
                    self._cleanup_stream(device)
            logger.error(f"Failed to start streaming on {device}: {e}")
            raise
    
    def stop_streaming(self, device: Optional[str] = None) -> Dict[str, Any]:
        """
        Stop streaming on one or all devices
        
        Args:
            device: Device path to stop (None = stop all streams)
        
        Returns:
            Result dictionary
        
        Raises:
            StreamNotRunningError: If not currently streaming
        """
        if device:
            logger.info(f"Stopping streaming on {device}")
            
            with self._state_lock:
                if device not in self._streams:
                    raise StreamNotRunningError(f"No stream running on device {device}")
                
                self._streams[device]["state"] = StreamState.STOPPING
            
            try:
                # Stop specific stream
                self._stop_stream_device(device)
                
                logger.info(f"Streaming stopped successfully on {device}")
                
                return {
                    "status": "stopped",
                    "device": device
                }
                
            except Exception as e:
                logger.error(f"Error stopping streaming on {device}: {e}")
                with self._state_lock:
                    if device in self._streams:
                        self._streams[device]["state"] = StreamState.ERROR
                raise StreamingError(f"Failed to stop streaming: {e}")
        else:
            # Stop all streams
            logger.info("Stopping all streams")
            
            with self._state_lock:
                if len(self._streams) == 0:
                    raise StreamNotRunningError("No streams are running")
                
                devices_to_stop = list(self._streams.keys())
            
            stopped_count = 0
            errors = []
            
            for dev in devices_to_stop:
                try:
                    self._stop_stream_device(dev)
                    stopped_count += 1
                except Exception as e:
                    logger.error(f"Error stopping stream on {dev}: {e}")
                    errors.append(f"{dev}: {e}")
            
            logger.info(f"Stopped {stopped_count} stream(s)")
            
            result = {
                "status": "stopped",
                "count": stopped_count
            }
            if errors:
                result["errors"] = errors
            
            return result
    
    def _stop_stream_device(self, device: str):
        """
        Stop streaming on a specific device (internal helper)
        
        Args:
            device: Device path
        """
        with self._state_lock:
            if device not in self._streams:
                return
            
            stream = self._streams[device]
            encoder = stream.get("encoder")
            thread = stream.get("thread")
        
        # Stop encoder
        if encoder:
            encoder.stop()
        
        # Wait for encoder thread to finish
        if thread and thread.is_alive():
            thread.join(timeout=10.0)
            if thread.is_alive():
                logger.warning(f"Encoder thread for {device} did not stop gracefully")
        
        # Update state
        self.state_manager.set_streaming_inactive(device)
        
        # Cleanup
        with self._state_lock:
            self._cleanup_stream(device)
    
    def restart_streaming(self, device: str,
                         name: Optional[str] = None,
                         resolution: Optional[str] = None,
                         fps: Optional[int] = None,
                         raw_input: Optional[bool] = None,
                         groups: Optional[str] = None) -> Dict[str, Any]:
        """
        Gracefully restart streaming on a specific device with new settings
        
        This method:
        1. Validates new settings before stopping
        2. Saves current settings for rollback
        3. Stops current stream
        4. Starts with new settings
        5. Rolls back if restart fails
        
        Args:
            device: Device path (must be currently streaming)
            name: New stream name (None = keep current)
            resolution: New resolution (None = keep current)
            fps: New FPS (None = keep current)
            raw_input: New raw_input setting (None = keep current)
            groups: New NDI groups (None = keep current)
        
        Returns:
            Result dictionary with status and settings
        
        Raises:
            StreamNotRunningError: If device not currently streaming
            DeviceNotFoundError: If device not found
            StreamingError: For other errors
        """
        logger.info(f"Restarting streaming on {device} with new settings...")
        
        # Check if device is currently streaming
        with self._state_lock:
            if device not in self._streams:
                raise StreamNotRunningError(
                    f"Cannot restart - device {device} is not streaming. Use start_streaming instead."
                )
            
            current_stream = self._streams[device]
            current_config = current_stream.get("config")
            if not current_config:
                raise StreamingError(f"No current configuration found for {device}")
        
        # Save current settings for rollback
        old_name = current_config.ndi.stream_name
        old_resolution = current_config.video.resolution
        old_fps = current_config.video.fps
        old_groups = current_config.ndi.groups
        old_raw_input = current_stream.get("raw_input", False)
        
        # Merge with new settings (use current if not provided)
        new_name = name if name is not None else old_name
        new_resolution = resolution if resolution is not None else old_resolution
        new_fps = fps if fps is not None else old_fps
        new_raw_input = raw_input if raw_input is not None else old_raw_input
        new_groups = groups if groups is not None else old_groups
        
        logger.info(f"Restart {device}: {old_resolution}@{old_fps} -> {new_resolution}@{new_fps}")
        
        # Pre-validate new settings before stopping
        try:
            
            # Validate resolution format
            if 'x' not in new_resolution:
                raise ValueError(f"Invalid resolution format: {new_resolution}")
            
            width, height = map(int, new_resolution.split('x'))
            if width < 1 or height < 1:
                raise ValueError("Resolution dimensions must be positive")
            
            # Validate FPS
            if new_fps < 1 or new_fps > 120:
                raise ValueError("FPS must be between 1 and 120")
            
        except Exception as e:
            logger.error(f"Pre-validation failed: {e}")
            raise StreamingError(f"Invalid settings: {e}")
        
        # Save the start time to calculate downtime
        import time
        stop_start_time = time.time()
        
        # Stop current stream
        try:
            logger.info(f"Stopping current stream on {device}...")
            self._stop_stream_device(device)
            
            stop_duration = time.time() - stop_start_time
            logger.info(f"Stream stopped in {stop_duration:.2f}s")
            
        except Exception as e:
            logger.error(f"Error stopping stream during restart: {e}")
            # Don't raise here - we're already in a bad state
            # Try to continue with restart
        
        # Start with new settings
        start_time = time.time()
        try:
            logger.info(f"Starting stream on {device} with new settings...")
            
            result = self.start_streaming(
                device=device,
                name=new_name,
                resolution=new_resolution,
                fps=new_fps,
                raw_input=new_raw_input,
                groups=new_groups
            )
            
            restart_duration = time.time() - stop_start_time
            logger.info(f"Stream restarted successfully in {restart_duration:.2f}s total")
            
            # Add restart info to result
            result["restart_info"] = {
                "downtime_seconds": restart_duration,
                "old_settings": {
                    "device": device,
                    "resolution": old_resolution,
                    "fps": old_fps
                },
                "new_settings": {
                    "device": device,
                    "resolution": new_resolution,
                    "fps": new_fps
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to start stream with new settings: {e}")
            logger.warning("Attempting to rollback to previous settings...")
            
            # Try to rollback to previous settings
            try:
                rollback_result = self.start_streaming(
                    device=device,
                    name=old_name,
                    resolution=old_resolution,
                    fps=old_fps,
                    raw_input=old_raw_input,
                    groups=old_groups
                )
                logger.info("Successfully rolled back to previous settings")
                raise StreamingError(
                    f"Restart failed, rolled back to previous settings. Error: {e}"
                )
            except Exception as rollback_error:
                logger.error(f"Rollback also failed: {rollback_error}")
                raise StreamingError(
                    f"Restart failed and rollback failed. Manual intervention required. "
                    f"Original error: {e}, Rollback error: {rollback_error}"
                )
    
    def get_status(self, device: Optional[str] = None) -> Dict[str, Any]:
        """
        Get current streaming status
        
        Args:
            device: Specific device to get status for (None = all streams)
        
        Returns:
            Status dictionary with stream information
        """
        if device:
            # Get status for specific device
            with self._state_lock:
                if device not in self._streams:
                    return {
                        "streaming": False,
                        "device": device
                    }
                
                stream = self._streams[device]
                config = stream.get("config")
                state = stream.get("state", StreamState.STOPPED)
                errors = stream.get("errors", [])
            
            # Get info from state manager
            stream_info = self.state_manager.get_streaming_info(device)
            
            status = {
                "streaming": True,
                "device": device,
                "state": state.value,
                "stream_name": config.ndi.stream_name if config else None,
                "resolution": config.video.resolution if config else None,
                "fps": config.video.fps if config else None,
                "groups": config.ndi.groups if config else None,
                "uptime_seconds": self.state_manager.get_streaming_uptime_seconds(device),
                "pid": stream_info.get("ffmpeg_pid")
            }
            
            if errors:
                status["errors"] = errors[-10:]  # Last 10 errors
            
            return status
        else:
            # Get status for all streams
            all_streams = self.state_manager.get_all_streams()
            
            streams_status = []
            for dev, stream_info in all_streams.items():
                with self._state_lock:
                    stream = self._streams.get(dev, {})
                    state = stream.get("state", StreamState.STOPPED)
                    errors = stream.get("errors", [])
                
                stream_status = {
                    "device": dev,
                    "streaming": True,
                    "state": state.value,
                    "stream_name": stream_info.get("stream_name"),
                    "resolution": stream_info.get("resolution"),
                    "fps": stream_info.get("fps"),
                    "groups": stream_info.get("groups"),
                    "uptime_seconds": self.state_manager.get_streaming_uptime_seconds(dev),
                    "pid": stream_info.get("ffmpeg_pid")
                }
                
                if errors:
                    stream_status["errors"] = errors[-10:]
                
                streams_status.append(stream_status)
            
            return {
                "streaming": len(streams_status) > 0,
                "stream_count": len(streams_status),
                "max_streams": self.MAX_STREAMS,
                "streams": streams_status
            }
    
    def list_devices(self) -> List[Dict[str, Any]]:
        """
        List available video devices
        
        Returns:
            List of device dictionaries
        """
        devices = self.webcam_manager.detect_devices()
        
        # Get all currently used devices
        all_streams = self.state_manager.get_all_streams()
        used_devices = set(all_streams.keys())
        
        result = []
        for device in devices:
            device_info = {
                "path": device.path,
                "name": device.name,
                "index": device.index,
                "driver": device.driver,
                "card": device.card,
                "in_use": device.path in used_devices
            }
            
            # Add stream info if device is in use
            if device.path in used_devices:
                stream_info = all_streams[device.path]
                device_info["stream_name"] = stream_info.get("stream_name")
            
            result.append(device_info)
        
        return result
    
    def _run_encoder(self, device: str):
        """
        Run encoder for a specific device (called in separate thread)
        
        Args:
            device: Device path
        """
        try:
            logger.debug(f"Encoder thread started for {device}")
            
            with self._state_lock:
                if device not in self._streams:
                    logger.error(f"Stream for {device} not found in _run_encoder")
                    return
                encoder = self._streams[device].get("encoder")
            
            if encoder:
                encoder.start()
        except KeyboardInterrupt:
            logger.info(f"Encoder interrupted for {device}")
        except Exception as e:
            logger.error(f"Encoder error on {device}: {e}")
            with self._state_lock:
                if device in self._streams:
                    self._streams[device]["errors"].append(str(e))
                    self._streams[device]["state"] = StreamState.ERROR
        finally:
            logger.debug(f"Encoder thread finished for {device}")
    
    def _cleanup_stream(self, device: str):
        """
        Clean up stream resources for a specific device
        
        Args:
            device: Device path
        """
        if device in self._streams:
            del self._streams[device]
            logger.debug(f"Cleaned up stream for {device}")
    
    def is_streaming(self, device: Optional[str] = None) -> bool:
        """
        Check if currently streaming
        
        Args:
            device: Specific device to check (None = check if any stream is active)
        
        Returns:
            True if streaming
        """
        if device:
            return self._get_stream_state(device) == StreamState.RUNNING
        else:
            with self._state_lock:
                return len(self._streams) > 0
    
    def get_current_config(self, device: str) -> Optional[StreamConfig]:
        """
        Get current streaming configuration for a device
        
        Args:
            device: Device path
        
        Returns:
            StreamConfig or None
        """
        with self._state_lock:
            if device in self._streams:
                return self._streams[device].get("config")
        return None
    
    def get_errors(self, device: Optional[str] = None) -> List[str]:
        """
        Get recent errors
        
        Args:
            device: Specific device (None = all errors)
        
        Returns:
            List of error messages
        """
        if device:
            with self._state_lock:
                if device in self._streams:
                    return list(self._streams[device].get("errors", []))
            return []
        else:
            all_errors = []
            with self._state_lock:
                for stream in self._streams.values():
                    all_errors.extend(stream.get("errors", []))
            return all_errors
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all streams
        
        Returns:
            Health status dictionary
        """
        health = {
            "healthy": True,
            "streaming": self.is_streaming(),
            "stream_count": 0,
            "issues": []
        }
        
        with self._state_lock:
            health["stream_count"] = len(self._streams)
            
            # Check each stream
            for device, stream in self._streams.items():
                state = stream.get("state", StreamState.STOPPED)
                encoder = stream.get("encoder")
                errors = stream.get("errors", [])
                
                # Check if in error state
                if state == StreamState.ERROR:
                    health["healthy"] = False
                    health["issues"].append(f"{device}: Stream in error state")
                
                # Check if encoder process is alive when streaming
                if state == StreamState.RUNNING:
                    if encoder and encoder.process:
                        if encoder.process.poll() is not None:
                            health["healthy"] = False
                            health["issues"].append(f"{device}: FFmpeg process died unexpectedly")
                    else:
                        health["healthy"] = False
                        health["issues"].append(f"{device}: No encoder process while streaming")
                
                # Add recent errors
                if errors:
                    recent_error = errors[-1]
                    health["issues"].append(f"{device}: {recent_error}")
        
        return health
    
    def cleanup(self):
        """Clean up resources (call on daemon shutdown)"""
        logger.info("Cleaning up streaming service")
        
        try:
            if self.is_streaming():
                # Stop all streams
                with self._state_lock:
                    devices_to_stop = list(self._streams.keys())
                
                for device in devices_to_stop:
                    try:
                        self._stop_stream_device(device)
                    except Exception as e:
                        logger.error(f"Error stopping stream on {device}: {e}")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        logger.info("Streaming service cleanup complete")

