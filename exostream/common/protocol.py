"""IPC Protocol definitions for communication between CLI and daemon"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List
from enum import Enum
import json


class RPCError(Enum):
    """Standard JSON-RPC 2.0 error codes"""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    
    # Custom application errors
    STREAM_ALREADY_RUNNING = -32000
    STREAM_NOT_RUNNING = -32001
    DEVICE_NOT_FOUND = -32002
    DEVICE_IN_USE = -32003
    INVALID_CONFIGURATION = -32004
    FFMPEG_ERROR = -32005


@dataclass
class RPCRequest:
    """JSON-RPC 2.0 request"""
    method: str
    params: Dict[str, Any]
    id: Optional[int] = None
    jsonrpc: str = "2.0"
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(asdict(self))
    
    @classmethod
    def from_json(cls, data: str) -> 'RPCRequest':
        """Parse from JSON string"""
        obj = json.loads(data)
        return cls(
            method=obj['method'],
            params=obj.get('params', {}),
            id=obj.get('id'),
            jsonrpc=obj.get('jsonrpc', '2.0')
        )


@dataclass
class RPCResponse:
    """JSON-RPC 2.0 response"""
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[int] = None
    jsonrpc: str = "2.0"
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        data = {
            'jsonrpc': self.jsonrpc,
            'id': self.id
        }
        if self.error is not None:
            data['error'] = self.error
        else:
            data['result'] = self.result
        return json.dumps(data)
    
    @classmethod
    def from_json(cls, data: str) -> 'RPCResponse':
        """Parse from JSON string"""
        obj = json.loads(data)
        return cls(
            result=obj.get('result'),
            error=obj.get('error'),
            id=obj.get('id'),
            jsonrpc=obj.get('jsonrpc', '2.0')
        )
    
    @classmethod
    def success(cls, result: Any, request_id: Optional[int] = None) -> 'RPCResponse':
        """Create a success response"""
        return cls(result=result, id=request_id)
    
    @classmethod
    def error_response(cls, code: RPCError, message: str, 
                      data: Optional[Any] = None, 
                      request_id: Optional[int] = None) -> 'RPCResponse':
        """Create an error response"""
        error = {
            'code': code.value,
            'message': message
        }
        if data is not None:
            error['data'] = data
        return cls(error=error, id=request_id)


# ============================================================================
# Method definitions and parameter types
# ============================================================================

@dataclass
class StartStreamParams:
    """Parameters for stream.start method"""
    device: str = "/dev/video0"
    name: str = "exostream"
    resolution: str = "1920x1080"
    fps: int = 30
    raw_input: bool = False
    groups: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StartStreamParams':
        return cls(
            device=data.get('device', '/dev/video0'),
            name=data.get('name', 'exostream'),
            resolution=data.get('resolution', '1920x1080'),
            fps=data.get('fps', 30),
            raw_input=data.get('raw_input', False),
            groups=data.get('groups')
        )


@dataclass
class StreamStatus:
    """Stream status information"""
    streaming: bool
    stream_name: Optional[str] = None
    device: Optional[str] = None
    resolution: Optional[str] = None
    fps: Optional[int] = None
    uptime_seconds: Optional[float] = None
    pid: Optional[int] = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StreamStatus':
        return cls(**data)


@dataclass
class DeviceInfo:
    """Video device information"""
    path: str
    name: str
    index: int
    driver: str = ""
    card: str = ""
    in_use: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeviceInfo':
        return cls(
            path=data['path'],
            name=data['name'],
            index=data['index'],
            driver=data.get('driver', ''),
            card=data.get('card', ''),
            in_use=data.get('in_use', False)
        )


@dataclass
class DaemonStatus:
    """Daemon status information"""
    running: bool
    version: str
    uptime_seconds: float
    pid: int
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DaemonStatus':
        return cls(**data)


@dataclass
class UpdateSettingsParams:
    """Parameters for settings.update method"""
    device: Optional[str] = None
    name: Optional[str] = None
    resolution: Optional[str] = None
    fps: Optional[int] = None
    raw_input: Optional[bool] = None
    groups: Optional[str] = None
    restart_if_streaming: bool = True  # Auto-restart stream with new settings
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UpdateSettingsParams':
        return cls(
            device=data.get('device'),
            name=data.get('name'),
            resolution=data.get('resolution'),
            fps=data.get('fps'),
            raw_input=data.get('raw_input'),
            groups=data.get('groups'),
            restart_if_streaming=data.get('restart_if_streaming', True)
        )


@dataclass
class SettingsInfo:
    """Current settings information"""
    device: str
    name: Optional[str]
    resolution: str
    fps: int
    raw_input: bool
    groups: Optional[str]
    streaming: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SettingsInfo':
        return cls(**data)


# ============================================================================
# Method names (constants)
# ============================================================================

class Methods:
    """Available RPC methods"""
    # Stream control
    STREAM_START = "stream.start"
    STREAM_STOP = "stream.stop"
    STREAM_STATUS = "stream.status"
    
    # Device management
    DEVICES_LIST = "devices.list"
    
    # Settings control (for remote camera control)
    SETTINGS_GET = "settings.get"
    SETTINGS_UPDATE = "settings.update"
    SETTINGS_GET_AVAILABLE = "settings.get_available"
    
    # Daemon control
    DAEMON_STATUS = "daemon.status"
    DAEMON_SHUTDOWN = "daemon.shutdown"
    DAEMON_PING = "daemon.ping"


# ============================================================================
# Protocol utilities
# ============================================================================

def create_request(method: str, params: Optional[Dict[str, Any]] = None, 
                  request_id: Optional[int] = None) -> RPCRequest:
    """Helper to create an RPC request"""
    return RPCRequest(
        method=method,
        params=params or {},
        id=request_id
    )


def create_success_response(result: Any, request_id: Optional[int] = None) -> RPCResponse:
    """Helper to create a success response"""
    return RPCResponse.success(result, request_id)


def create_error_response(code: RPCError, message: str, 
                         data: Optional[Any] = None,
                         request_id: Optional[int] = None) -> RPCResponse:
    """Helper to create an error response"""
    return RPCResponse.error_response(code, message, data, request_id)

