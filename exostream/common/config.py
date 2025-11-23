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
    bitrate: int = 4000  # kbps
    keyframe_interval: int = 60  # GOP size
    
    @property
    def resolution(self) -> str:
        return f"{self.width}x{self.height}"
    
    @classmethod
    def from_resolution_string(cls, resolution: str, **kwargs):
        """Create VideoConfig from resolution string like '1920x1080'"""
        width, height = map(int, resolution.split('x'))
        return cls(width=width, height=height, **kwargs)


@dataclass
class SRTConfig:
    """SRT streaming configuration"""
    port: int = 9000
    latency: int = 120  # milliseconds
    passphrase: Optional[str] = None
    mode: str = "listener"  # listener or caller
    
    def get_uri(self, host: Optional[str] = None) -> str:
        """Generate SRT URI"""
        if self.mode == "listener":
            uri = f"srt://:{self.port}"
        else:
            if not host:
                raise ValueError("Host is required for caller mode")
            uri = f"srt://{host}:{self.port}"
        
        # Add parameters
        params = [f"latency={self.latency}"]
        if self.passphrase:
            params.append(f"passphrase={self.passphrase}")
        
        return f"{uri}?{'&'.join(params)}"


@dataclass
class StreamConfig:
    """Complete streaming configuration"""
    video: VideoConfig
    srt: SRTConfig
    device: str = "/dev/video0"
    
    @classmethod
    def from_preset(cls, preset: str = "medium"):
        """Load configuration from preset"""
        presets = {
            "low": VideoConfig(width=1280, height=720, fps=25, bitrate=2000),
            "medium": VideoConfig(width=1920, height=1080, fps=30, bitrate=4000),
            "high": VideoConfig(width=1920, height=1080, fps=30, bitrate=6000),
        }
        
        if preset not in presets:
            raise ValueError(f"Unknown preset: {preset}. Available: {list(presets.keys())}")
        
        return cls(
            video=presets[preset],
            srt=SRTConfig()
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
            'srt': {
                'port': self.srt.port,
                'latency': self.srt.latency,
                'mode': self.srt.mode,
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
        srt = SRTConfig(**config_dict['srt'])
        
        return cls(
            video=video,
            srt=srt,
            device=config_dict.get('device', '/dev/video0')
        )

