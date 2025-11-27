"""Network client for remote control via TCP"""

import socket
import json
import logging
from typing import Optional, Dict, Any

from exostream.common.protocol import (
    RPCRequest, RPCResponse, RPCError,
    create_request
)

logger = logging.getLogger(__name__)


class NetworkClientError(Exception):
    """Base exception for network client errors"""
    pass


class NetworkConnectionError(NetworkClientError):
    """Raised when connection fails"""
    pass


class NetworkTimeoutError(NetworkClientError):
    """Raised when request times out"""
    pass


class NetworkRPCError(NetworkClientError):
    """Raised when server returns an RPC error"""
    def __init__(self, code: int, message: str, data: Optional[Any] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


class NetworkClient:
    """Client for remote control via TCP socket"""
    
    DEFAULT_TIMEOUT = 10.0  # seconds
    BUFFER_SIZE = 4096
    
    def __init__(self, host: str, port: int = 9023,
                 timeout: float = DEFAULT_TIMEOUT):
        """
        Initialize network client
        
        Args:
            host: Server hostname or IP address
            port: Server port (default: 9023)
            timeout: Timeout in seconds for socket operations
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self._request_id = 0
    
    def _get_next_id(self) -> int:
        """Get next request ID"""
        self._request_id += 1
        return self._request_id
    
    def is_connected(self) -> bool:
        """
        Check if can connect to server
        
        Returns:
            True if server is reachable, False otherwise
        """
        try:
            # Try to ping the server
            self.call("daemon.ping", {})
            return True
        except (NetworkConnectionError, NetworkTimeoutError, OSError):
            return False
        except Exception as e:
            logger.debug(f"Error checking connection: {e}")
            return False
    
    def call(self, method: str, params: Optional[Dict[str, Any]] = None,
             timeout: Optional[float] = None) -> Any:
        """
        Call a method on the remote server
        
        Args:
            method: Method name (e.g., "stream.start")
            params: Method parameters
            timeout: Timeout override (uses default if not specified)
        
        Returns:
            Result from the server
        
        Raises:
            NetworkConnectionError: If cannot connect to server
            NetworkTimeoutError: If server doesn't respond in time
            NetworkRPCError: If server returns an error
            NetworkClientError: For other errors
        """
        timeout = timeout or self.timeout
        
        # Create request
        request = create_request(method, params or {}, self._get_next_id())
        
        # Send request and receive response
        try:
            response_data = self._send_and_receive(request.to_json(), timeout)
        except socket.timeout:
            raise NetworkTimeoutError(
                f"Server did not respond within {timeout} seconds"
            )
        except ConnectionRefusedError:
            raise NetworkConnectionError(
                f"Connection refused to {self.host}:{self.port}"
            )
        except socket.gaierror as e:
            raise NetworkConnectionError(
                f"Could not resolve hostname {self.host}: {e}"
            )
        except socket.error as e:
            raise NetworkClientError(f"Socket error: {e}")
        
        # Parse response
        try:
            response = RPCResponse.from_json(response_data)
        except json.JSONDecodeError as e:
            raise NetworkClientError(f"Invalid JSON response: {e}")
        
        # Check for errors
        if response.error is not None:
            error = response.error
            raise NetworkRPCError(
                code=error['code'],
                message=error['message'],
                data=error.get('data')
            )
        
        return response.result
    
    def _send_and_receive(self, data: str, timeout: float) -> str:
        """
        Send data and receive response via TCP socket
        
        Args:
            data: JSON string to send
            timeout: Timeout in seconds
        
        Returns:
            Response data as string
        
        Raises:
            socket.error: On socket errors
            socket.timeout: On timeout
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.settimeout(timeout)
            
            # Connect to server
            logger.debug(f"Connecting to {self.host}:{self.port}")
            sock.connect((self.host, self.port))
            
            # Send request
            logger.debug(f"Sending: {data[:200]}...")
            sock.sendall(data.encode('utf-8') + b'\n')
            
            # Receive response (may need multiple reads)
            response_chunks = []
            while True:
                chunk = sock.recv(self.BUFFER_SIZE)
                if not chunk:
                    break
                response_chunks.append(chunk)
                
                # Check if we have a complete JSON message
                if chunk.endswith(b'\n') or chunk.endswith(b'}'):
                    break
            
            response_data = b''.join(response_chunks).decode('utf-8').strip()
            logger.debug(f"Received: {response_data[:200]}...")
            
            return response_data
            
        finally:
            sock.close()


class NetworkClientManager:
    """High-level manager for network client with method helpers"""
    
    def __init__(self, host: str, port: int = 9023):
        """
        Initialize network client manager
        
        Args:
            host: Server hostname or IP address
            port: Server port
        """
        self.client = NetworkClient(host, port)
    
    def is_connected(self) -> bool:
        """Check if connected to server"""
        return self.client.is_connected()
    
    def ping(self) -> bool:
        """
        Ping the server
        
        Returns:
            True if server responds
        """
        try:
            result = self.client.call("daemon.ping", {})
            return result.get('pong', False)
        except Exception:
            return False
    
    def get_settings(self) -> Dict[str, Any]:
        """
        Get current camera settings
        
        Returns:
            Settings dictionary
        """
        return self.client.call("settings.get", {})
    
    def update_settings(self, device: Optional[str] = None,
                       name: Optional[str] = None,
                       resolution: Optional[str] = None,
                       fps: Optional[int] = None,
                       raw_input: Optional[bool] = None,
                       groups: Optional[str] = None,
                       restart_if_streaming: bool = True) -> Dict[str, Any]:
        """
        Update camera settings
        
        Args:
            device: Device path
            name: Stream name
            resolution: Video resolution
            fps: Frames per second
            raw_input: Use raw YUYV input
            groups: NDI groups
            restart_if_streaming: Auto-restart stream if currently streaming
        
        Returns:
            Result dictionary
        """
        params = {}
        if device is not None:
            params['device'] = device
        if name is not None:
            params['name'] = name
        if resolution is not None:
            params['resolution'] = resolution
        if fps is not None:
            params['fps'] = fps
        if raw_input is not None:
            params['raw_input'] = raw_input
        if groups is not None:
            params['groups'] = groups
        params['restart_if_streaming'] = restart_if_streaming
        
        return self.client.call("settings.update", params)
    
    def get_available_options(self) -> Dict[str, Any]:
        """
        Get available configuration options
        
        Returns:
            Dictionary with available devices, resolutions, fps
        """
        return self.client.call("settings.get_available", {})
    
    def start_stream(self, device: str, name: str, resolution: str = "1920x1080",
                    fps: int = 30, raw_input: bool = False,
                    groups: Optional[str] = None) -> Dict[str, Any]:
        """
        Start streaming
        
        Args:
            device: Device path
            name: Stream name
            resolution: Video resolution
            fps: Frames per second
            raw_input: Use raw YUYV input
            groups: NDI groups
        
        Returns:
            Result dictionary
        """
        params = {
            'device': device,
            'name': name,
            'resolution': resolution,
            'fps': fps,
            'raw_input': raw_input,
            'groups': groups
        }
        return self.client.call("stream.start", params, timeout=15.0)
    
    def stop_stream(self) -> Dict[str, Any]:
        """
        Stop streaming
        
        Returns:
            Result dictionary
        """
        return self.client.call("stream.stop", {})
    
    def get_stream_status(self) -> Dict[str, Any]:
        """
        Get stream status
        
        Returns:
            Status dictionary
        """
        return self.client.call("stream.status", {})
    
    def list_devices(self) -> list:
        """
        List available devices
        
        Returns:
            List of device dictionaries
        """
        result = self.client.call("devices.list", {})
        return result.get('devices', [])
    
    def get_daemon_status(self) -> Dict[str, Any]:
        """
        Get daemon status
        
        Returns:
            Status dictionary
        """
        return self.client.call("daemon.status", {})

