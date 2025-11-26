"""Configuration management and presets"""

from dataclasses import dataclass
from typing import Optional
import yaml
from pathlib import Path


@dataclass
class VideoConfig:
    """Video encoding configuration"""
    width: int = 1920
    height: int = 1080
    fps: int = 30
    bitrate: int = 6000  # kbps (increased for better quality with software encoder)
    keyframe_interval: int = 30  # GOP size (1 second at 30fps)
    
    @property
    def resolution(self) -> str:
        return f"{self.width}x{self.height}"
    
    @classmethod
    def from_resolution_string(cls, resolution: str, **kwargs):
        """Create VideoConfig from resolution string like '1920x1080'"""
        width, height = map(int, resolution.split('x'))
        return cls(width=width, height=height, **kwargs)


@dataclass
class NDIConfig:
    """NDI streaming configuration"""
    stream_name: str = "Exostream"
    groups: Optional[str] = None  # NDI groups (comma-separated)
    clock_video: bool = True  # Use video clock for timing
    clock_audio: bool = False  # Use audio clock for timing


@dataclass
class StreamConfig:
    """Complete streaming configuration"""
    video: VideoConfig
    ndi: NDIConfig
    device: str = "/dev/video0"
    
    @classmethod
    def from_preset(cls, preset: str = "medium", stream_name: str = "Exostream"):
        """Load configuration from preset"""
        presets = {
            "low": VideoConfig(width=1280, height=720, fps=25, bitrate=3000),
            "medium": VideoConfig(width=1920, height=1080, fps=30, bitrate=6000),
            "high": VideoConfig(width=1920, height=1080, fps=30, bitrate=8000),
        }
        
        if preset not in presets:
            raise ValueError(f"Unknown preset: {preset}. Available: {list(presets.keys())}")
        
        return cls(
            video=presets[preset],
            ndi=NDIConfig(stream_name=stream_name)
        )
    
    def save_to_file(self, filepath: Path):
        """Save configuration to YAML file"""
        config_dict = {
            'video': {
                'width': self.video.width,
                'height': self.video.height,
                'fps': self.video.fps,
                'bitrate': self.video.bitrate,
                'keyframe_interval': self.video.keyframe_interval,
            },
            'ndi': {
                'stream_name': self.ndi.stream_name,
                'groups': self.ndi.groups,
                'clock_video': self.ndi.clock_video,
                'clock_audio': self.ndi.clock_audio,
            },
            'device': self.device,
        }
        
        with open(filepath, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False)
    
    @classmethod
    def load_from_file(cls, filepath: Path):
        """Load configuration from YAML file"""
        with open(filepath, 'r') as f:
            config_dict = yaml.safe_load(f)
        
        video = VideoConfig(**config_dict['video'])
        ndi = NDIConfig(**config_dict['ndi'])
        
        return cls(
            video=video,
            ndi=ndi,
            device=config_dict.get('device', '/dev/video0')
        )

