"""GStreamer utilities and helpers"""

import os
import sys
from typing import Optional

try:
    import gi
    gi.require_version('Gst', '1.0')
    from gi.repository import Gst, GLib
    Gst.init(None)
except ImportError as e:
    print(f"Error: GStreamer Python bindings not found: {e}")
    print("Please install: sudo apt-get install python3-gst-1.0 gstreamer1.0-plugins-bad")
    sys.exit(1)


def check_gst_plugin(plugin_name: str) -> bool:
    """
    Check if a GStreamer plugin is available
    
    Args:
        plugin_name: Name of the plugin to check
    
    Returns:
        True if plugin is available, False otherwise
    """
    registry = Gst.Registry.get()
    plugin = registry.find_plugin(plugin_name)
    return plugin is not None


def check_gst_element(element_name: str) -> bool:
    """
    Check if a GStreamer element is available
    
    Args:
        element_name: Name of the element to check
    
    Returns:
        True if element is available, False otherwise
    """
    factory = Gst.ElementFactory.find(element_name)
    return factory is not None


def detect_h264_encoder(prefer_software: bool = False) -> Optional[str]:
    """
    Detect the best available H.264 encoder
    
    Args:
        prefer_software: If True, prefer software encoding (x264enc)
    
    Returns:
        Name of the encoder element, or None if not found
    """
    if prefer_software:
        # Use software encoder directly
        encoders = ['x264enc']
    else:
        # Check for Raspberry Pi hardware encoders in order of preference
        # Note: v4l2h264enc has issues on some Pi 4 systems, so we offer software fallback
        encoders = [
            'h264_v4l2m2m',      # FFmpeg hardware encoder
            'v4l2h264enc',      # Raspberry Pi 4 hardware encoder (can be buggy)
            'omxh264enc',       # Raspberry Pi 3 hardware encoder (deprecated but still used)
            'x264enc',          # Software fallback (reliable but CPU intensive)
        ]
    
    for encoder in encoders:
        if check_gst_element(encoder):
            return encoder
    
    return None


def check_srt_support() -> bool:
    """
    Check if SRT support is available in GStreamer
    
    Returns:
        True if SRT plugin is available, False otherwise
    """
    return check_gst_element('srtsink') and check_gst_element('srtsrc')


def check_ndi_support() -> bool:
    """
    Check if NDI support is available in GStreamer
    
    Returns:
        True if NDI plugin is available, False otherwise
    """
    return check_gst_element('ndisink') and check_gst_element('ndisrc')


def get_device_capabilities(device_path: str) -> dict:
    """
    Get video device capabilities using GStreamer
    
    Args:
        device_path: Path to video device (e.g., /dev/video0)
    
    Returns:
        Dictionary with device capabilities
    """
    caps_info = {
        'device': device_path,
        'formats': [],
        'resolutions': [],
    }
    
    if not os.path.exists(device_path):
        return caps_info
    
    try:
        # Create a v4l2src element to query capabilities
        source = Gst.ElementFactory.make("v4l2src", "source")
        if not source:
            return caps_info
        
        source.set_property("device", device_path)
        
        # Get device caps
        pad = source.get_static_pad("src")
        if pad:
            caps = pad.query_caps(None)
            for i in range(caps.get_size()):
                structure = caps.get_structure(i)
                format_name = structure.get_name()
                
                # Get width and height if available
                width = structure.get_value("width")
                height = structure.get_value("height")
                
                if width and height:
                    caps_info['resolutions'].append(f"{width}x{height}")
                
                if format_name not in caps_info['formats']:
                    caps_info['formats'].append(format_name)
    
    except Exception as e:
        pass
    
    return caps_info


class GstPipelineManager:
    """Manager for GStreamer pipeline lifecycle"""
    
    def __init__(self, pipeline: Gst.Pipeline):
        self.pipeline = pipeline
        self.loop = None
        self.bus = None
    
    def setup_bus_watch(self, message_callback=None):
        """Set up bus watch for pipeline messages"""
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        
        if message_callback:
            self.bus.connect("message", message_callback)
    
    def start(self):
        """Start the pipeline"""
        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            raise RuntimeError("Unable to set pipeline to PLAYING state")
    
    def stop(self):
        """Stop the pipeline"""
        self.pipeline.set_state(Gst.State.NULL)
    
    def pause(self):
        """Pause the pipeline"""
        self.pipeline.set_state(Gst.State.PAUSED)
    
    def get_state(self) -> Gst.State:
        """Get current pipeline state"""
        ret, state, pending = self.pipeline.get_state(Gst.CLOCK_TIME_NONE)
        return state

