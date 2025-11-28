"""Settings manager for camera configuration"""

import logging
from typing import Dict, Any, Optional, List
from exostream.common.protocol import UpdateSettingsParams, SettingsInfo
from exostream.daemon.state_manager import StateManager
from exostream.sender.webcam import WebcamManager

logger = logging.getLogger(__name__)


class SettingsManager:
    """
    Manages camera settings and configuration
    
    Provides:
    - Get current settings
    - Update settings (with validation)
    - Get available options (devices, resolutions, fps)
    """
    
    # Supported resolutions
    COMMON_RESOLUTIONS = [
        "640x480",
        "800x600",
        "1280x720",
        "1920x1080",
        "2560x1440",
        "3840x2160"
    ]
    
    # Supported frame rates
    COMMON_FPS = [15, 24, 30, 60]
    
    def __init__(self, state_manager: StateManager):
        """
        Initialize settings manager
        
        Args:
            state_manager: StateManager instance for accessing current config
        """
        self.state_manager = state_manager
        self.webcam_manager = WebcamManager()
    
    def get_current_settings(self) -> Dict[str, Any]:
        """
        Get current settings from state or defaults
        
        Returns:
            Dictionary with current settings
        """
        streaming_info = self.state_manager.get_streaming_info()
        last_config = self.state_manager.get_last_config()
        
        # If streaming, use current stream config
        if streaming_info.get('active'):
            settings = SettingsInfo(
                device=streaming_info.get('device', '/dev/video0'),
                name=streaming_info.get('stream_name'),
                resolution=streaming_info.get('resolution', '1920x1080'),
                fps=streaming_info.get('fps', 30),
                raw_input=streaming_info.get('raw_input', False),
                groups=streaming_info.get('groups'),
                streaming=True
            )
        else:
            # Use last known config
            settings = SettingsInfo(
                device=last_config.get('device', '/dev/video0'),
                name=None,
                resolution=last_config.get('resolution', '1920x1080'),
                fps=last_config.get('fps', 30),
                raw_input=last_config.get('raw_input', False),
                groups=None,
                streaming=False
            )
        
        return settings.to_dict()
    
    def validate_settings_update(self, params: UpdateSettingsParams) -> tuple[bool, Optional[str]]:
        """
        Validate settings update parameters
        
        Args:
            params: Settings to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate device if specified
        if params.device:
            devices = self.webcam_manager.detect_devices()
            device_paths = [d.path for d in devices]
            if params.device not in device_paths:
                return False, f"Device {params.device} not found. Available: {device_paths}"
        
        # Validate resolution if specified
        if params.resolution:
            if 'x' not in params.resolution:
                return False, f"Invalid resolution format: {params.resolution}. Use format like '1920x1080'"
            
            try:
                width, height = map(int, params.resolution.split('x'))
                if width < 1 or height < 1:
                    return False, "Resolution dimensions must be positive"
                if width > 4096 or height > 4096:
                    return False, "Resolution too large (max 4096x4096)"
            except ValueError:
                return False, f"Invalid resolution format: {params.resolution}"
        
        # Validate FPS if specified
        if params.fps is not None:
            if params.fps < 1 or params.fps > 120:
                return False, "FPS must be between 1 and 120"
        
        # Validate stream name if specified
        if params.name is not None and params.name == "":
            return False, "Stream name cannot be empty"
        
        return True, None
    
    def get_available_options(self) -> Dict[str, Any]:
        """
        Get available configuration options
        
        Returns:
            Dictionary with available devices, resolutions, fps options
        """
        # Detect available devices
        devices = self.webcam_manager.detect_devices()
        device_list = [
            {
                'path': d.path,
                'name': d.name,
                'index': d.index
            }
            for d in devices
        ]
        
        # Get streaming state to mark device in use
        streaming_info = self.state_manager.get_streaming_info()
        current_device = streaming_info.get('device') if streaming_info.get('active') else None
        
        for device in device_list:
            device['in_use'] = (device['path'] == current_device)
        
        return {
            'devices': device_list,
            'resolutions': self.COMMON_RESOLUTIONS,
            'fps_options': self.COMMON_FPS,
            'input_formats': ['mjpeg', 'yuyv']
        }
    
    def merge_settings(self, current: Dict[str, Any], 
                      updates: UpdateSettingsParams) -> Dict[str, Any]:
        """
        Merge update parameters into current settings
        
        Args:
            current: Current settings dictionary
            updates: Update parameters
        
        Returns:
            Merged settings dictionary
        """
        merged = current.copy()
        
        if updates.device is not None:
            merged['device'] = updates.device
        if updates.name is not None:
            merged['name'] = updates.name
        if updates.resolution is not None:
            merged['resolution'] = updates.resolution
        if updates.fps is not None:
            merged['fps'] = updates.fps
        if updates.raw_input is not None:
            merged['raw_input'] = updates.raw_input
        if updates.groups is not None:
            merged['groups'] = updates.groups
        
        return merged

