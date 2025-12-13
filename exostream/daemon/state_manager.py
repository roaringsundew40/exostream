"""State management for daemon - persists configuration and status to disk"""

import json
import os
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from exostream.common.config import StreamConfig

logger = logging.getLogger(__name__)


class StateManager:
    """
    Manages daemon state persistence to disk
    
    Stores:
    - Current streaming status for all active streams
    - Active configuration for each stream
    - FFmpeg process info for each stream
    - Last known good configuration
    
    Multi-Stream Support:
    - State file contains a 'streams' dictionary keyed by device path
    - Each entry tracks: stream name, resolution, FPS, PID, start time, etc.
    - Supports querying individual streams or all streams at once
    """
    
    DEFAULT_STATE_DIR = Path.home() / ".exostream"
    DEFAULT_STATE_FILE = "state.json"
    
    def __init__(self, state_dir: Optional[Path] = None):
        """
        Initialize state manager
        
        Args:
            state_dir: Directory for state file (defaults to ~/.exostream)
        """
        self.state_dir = state_dir or self.DEFAULT_STATE_DIR
        self.state_file = self.state_dir / self.DEFAULT_STATE_FILE
        self._state: Dict[str, Any] = {}
        self._lock = threading.Lock()
        
        # Ensure state directory exists
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing state
        self._load()
    
    def _load(self):
        """Load state from disk"""
        if not self.state_file.exists():
            logger.info("No existing state file found, starting fresh")
            self._state = self._default_state()
            self._save()
            return
        
        try:
            with open(self.state_file, 'r') as f:
                self._state = json.load(f)
            logger.info(f"Loaded state from {self.state_file}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse state file: {e}")
            logger.warning("Using default state")
            self._state = self._default_state()
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            self._state = self._default_state()
    
    def _save(self):
        """Save state to disk"""
        try:
            # Write to temp file first, then rename (atomic operation)
            temp_file = self.state_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(self._state, f, indent=2)
            temp_file.replace(self.state_file)
            logger.debug(f"Saved state to {self.state_file}")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def _default_state(self) -> Dict[str, Any]:
        """Get default state"""
        return {
            "version": "0.3.0",
            "daemon": {
                "started_at": None,
                "pid": None
            },
            "streams": {},  # Dictionary of active streams keyed by device path
            "last_config": {
                "device": "/dev/video0",
                "resolution": "1920x1080",
                "fps": 30,
                "raw_input": False
            }
        }
    
    def set_daemon_started(self, pid: int):
        """Mark daemon as started"""
        with self._lock:
            self._state["daemon"]["started_at"] = datetime.now().isoformat()
            self._state["daemon"]["pid"] = pid
            self._save()
    
    def set_streaming_active(self, config: StreamConfig, ffmpeg_pid: int, raw_input: bool = False):
        """
        Mark a stream as active
        
        Args:
            config: Stream configuration
            ffmpeg_pid: FFmpeg process ID
            raw_input: Whether using raw input
        """
        with self._lock:
            device = config.device
            self._state["streams"][device] = {
                "active": True,
                "stream_name": config.ndi.stream_name,
                "device": device,
                "resolution": config.video.resolution,
                "fps": config.video.fps,
                "raw_input": raw_input,
                "groups": config.ndi.groups,
                "started_at": datetime.now().isoformat(),
                "ffmpeg_pid": ffmpeg_pid
            }
            
            # Update last known good config
            self._state["last_config"] = {
                "device": device,
                "resolution": config.video.resolution,
                "fps": config.video.fps,
                "raw_input": raw_input
            }
            
            self._save()
            logger.info(f"Stream marked as active: {config.ndi.stream_name} on {device}")
    
    def set_streaming_inactive(self, device: Optional[str] = None):
        """
        Mark one or all streams as inactive
        
        Args:
            device: Device path to stop (None = stop all streams)
        """
        with self._lock:
            if device:
                # Stop specific stream
                if device in self._state["streams"]:
                    stream_name = self._state["streams"][device].get("stream_name", device)
                    del self._state["streams"][device]
                    self._save()
                    logger.info(f"Stream marked as inactive: {stream_name} on {device}")
            else:
                # Stop all streams
                stream_count = len(self._state["streams"])
                self._state["streams"] = {}
                self._save()
                logger.info(f"All streams marked as inactive ({stream_count} streams)")
    
    def update_streaming_pid(self, device: str, pid: Optional[int]):
        """
        Update FFmpeg PID for a specific stream
        
        Args:
            device: Device path
            pid: FFmpeg process ID
        """
        with self._lock:
            if device in self._state["streams"]:
                self._state["streams"][device]["ffmpeg_pid"] = pid
                self._save()
    
    def is_streaming_active(self, device: Optional[str] = None) -> bool:
        """
        Check if streaming is currently active
        
        Args:
            device: Specific device to check (None = check if any stream is active)
        
        Returns:
            True if streaming is active
        """
        with self._lock:
            if device:
                return device in self._state["streams"]
            else:
                return len(self._state["streams"]) > 0
    
    def get_streaming_info(self, device: Optional[str] = None) -> Dict[str, Any]:
        """
        Get streaming information
        
        Args:
            device: Specific device to get info for (None = get all streams)
        
        Returns:
            Dictionary with stream info (single stream or all streams)
        """
        with self._lock:
            if device:
                # Return specific stream info
                return dict(self._state["streams"].get(device, {}))
            else:
                # Return all streams
                return {"streams": dict(self._state["streams"])}
    
    def get_last_config(self) -> Dict[str, Any]:
        """Get last known good configuration"""
        with self._lock:
            return dict(self._state["last_config"])
    
    def get_daemon_info(self) -> Dict[str, Any]:
        """Get daemon information"""
        with self._lock:
            return dict(self._state["daemon"])
    
    def get_uptime_seconds(self) -> Optional[float]:
        """
        Get daemon uptime in seconds
        
        Returns:
            Uptime in seconds, or None if not started
        """
        with self._lock:
            started_at = self._state["daemon"].get("started_at")
            if not started_at:
                return None
            
            try:
                start_time = datetime.fromisoformat(started_at)
                return (datetime.now() - start_time).total_seconds()
            except Exception as e:
                logger.error(f"Failed to calculate uptime: {e}")
                return None
    
    def get_streaming_uptime_seconds(self, device: str) -> Optional[float]:
        """
        Get streaming uptime in seconds for a specific stream
        
        Args:
            device: Device path
        
        Returns:
            Uptime in seconds, or None if not streaming
        """
        with self._lock:
            if device not in self._state["streams"]:
                return None
            
            started_at = self._state["streams"][device].get("started_at")
            if not started_at:
                return None
            
            try:
                start_time = datetime.fromisoformat(started_at)
                return (datetime.now() - start_time).total_seconds()
            except Exception as e:
                logger.error(f"Failed to calculate streaming uptime: {e}")
                return None
    
    def get_all_streams(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all active streams
        
        Returns:
            Dictionary of all streams keyed by device path
        """
        with self._lock:
            return dict(self._state["streams"])
    
    def get_stream_count(self) -> int:
        """
        Get number of active streams
        
        Returns:
            Number of active streams
        """
        with self._lock:
            return len(self._state["streams"])
    
    def get_full_state(self) -> Dict[str, Any]:
        """Get complete state"""
        with self._lock:
            return dict(self._state)
    
    def clear_state(self):
        """Reset to default state"""
        with self._lock:
            self._state = self._default_state()
            self._save()
            logger.info("State cleared")

