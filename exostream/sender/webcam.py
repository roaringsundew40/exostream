"""Webcam detection and V4L2 device management"""

import os
import glob
from typing import List, Optional, Dict
from dataclasses import dataclass
from exostream.common.logger import get_logger

logger = get_logger(__name__)


@dataclass
class WebcamDevice:
    """Represents a V4L2 video device"""
    path: str
    name: str
    index: int
    driver: str = ""
    card: str = ""
    bus_info: str = ""
    capabilities: List[str] = None
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
    
    @property
    def is_capture_device(self) -> bool:
        """Check if device supports video capture"""
        return "video_capture" in self.capabilities or len(self.capabilities) == 0
    
    def __str__(self) -> str:
        return f"{self.name} ({self.path})"


class WebcamManager:
    """Manager for detecting and enumerating webcam devices"""
    
    def __init__(self):
        self.devices: List[WebcamDevice] = []
    
    def detect_devices(self) -> List[WebcamDevice]:
        """
        Detect all available V4L2 video devices
        
        Returns:
            List of WebcamDevice objects
        """
        self.devices = []
        
        # Find all /dev/video* devices
        video_devices = sorted(glob.glob("/dev/video*"))
        
        for device_path in video_devices:
            try:
                device = self._probe_device(device_path)
                if device and device.is_capture_device:
                    self.devices.append(device)
                    logger.debug(f"Found device: {device}")
            except Exception as e:
                logger.warning(f"Failed to probe {device_path}: {e}")
        
        return self.devices
    
    def _probe_device(self, device_path: str) -> Optional[WebcamDevice]:
        """
        Probe a device to get its information
        
        Args:
            device_path: Path to the device (e.g., /dev/video0)
        
        Returns:
            WebcamDevice object or None if probe failed
        """
        if not os.path.exists(device_path):
            return None
        
        # Extract device index
        index = int(device_path.replace("/dev/video", ""))
        
        # Try to get device info from sysfs
        device_info = self._get_device_info_from_sysfs(device_path)
        
        # Default name if we can't get it from sysfs
        name = device_info.get('name', f"Video Device {index}")
        
        device = WebcamDevice(
            path=device_path,
            name=name,
            index=index,
            driver=device_info.get('driver', ''),
            card=device_info.get('card', ''),
            bus_info=device_info.get('bus_info', ''),
            capabilities=device_info.get('capabilities', [])
        )
        
        return device
    
    def _get_device_info_from_sysfs(self, device_path: str) -> Dict[str, any]:
        """
        Get device information from sysfs
        
        Args:
            device_path: Path to the device
        
        Returns:
            Dictionary with device information
        """
        info = {}
        
        try:
            # Get device name from sysfs
            device_name = os.path.basename(device_path)
            sysfs_path = f"/sys/class/video4linux/{device_name}"
            
            if os.path.exists(sysfs_path):
                # Read device name
                name_file = os.path.join(sysfs_path, "name")
                if os.path.exists(name_file):
                    with open(name_file, 'r') as f:
                        info['name'] = f.read().strip()
                
                # Try to read device/modalias for more info
                modalias_file = os.path.join(sysfs_path, "device/modalias")
                if os.path.exists(modalias_file):
                    with open(modalias_file, 'r') as f:
                        info['modalias'] = f.read().strip()
        
        except Exception as e:
            logger.debug(f"Failed to read sysfs info for {device_path}: {e}")
        
        return info
    
    def get_device_by_path(self, path: str) -> Optional[WebcamDevice]:
        """
        Get a device by its path
        
        Args:
            path: Device path (e.g., /dev/video0)
        
        Returns:
            WebcamDevice object or None
        """
        for device in self.devices:
            if device.path == path:
                return device
        return None
    
    def get_device_by_index(self, index: int) -> Optional[WebcamDevice]:
        """
        Get a device by its index
        
        Args:
            index: Device index
        
        Returns:
            WebcamDevice object or None
        """
        for device in self.devices:
            if device.index == index:
                return device
        return None
    
    def find_logitech_camera(self) -> Optional[WebcamDevice]:
        """
        Find a Logitech camera (C920 or C930)
        
        Returns:
            WebcamDevice object or None
        """
        logitech_keywords = ['logitech', 'c920', 'c930']
        
        for device in self.devices:
            device_name_lower = device.name.lower()
            if any(keyword in device_name_lower for keyword in logitech_keywords):
                return device
        
        return None
    
    def list_devices(self) -> str:
        """
        Get a formatted string listing all devices
        
        Returns:
            Formatted string with device information
        """
        if not self.devices:
            return "No video devices found"
        
        lines = ["Available video devices:"]
        for i, device in enumerate(self.devices):
            lines.append(f"  [{i}] {device.name} - {device.path}")
        
        return "\n".join(lines)

