"""IPC Client for communicating with the daemon"""

import socket
import json
import time
from typing import Optional, Dict, Any
import logging

from exostream.common.protocol import (
    RPCRequest, RPCResponse, RPCError,
    create_request
)

logger = logging.getLogger(__name__)


class IPCClientError(Exception):
    """Base exception for IPC client errors"""
    pass


class DaemonNotRunningError(IPCClientError):
    """Raised when daemon is not running"""
    pass


class DaemonTimeoutError(IPCClientError):
    """Raised when daemon doesn't respond in time"""
    pass


class DaemonRPCError(IPCClientError):
    """Raised when daemon returns an RPC error"""
    def __init__(self, code: int, message: str, data: Optional[Any] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


class IPCClient:
    """Client for communicating with the daemon via Unix socket"""
    
    DEFAULT_SOCKET_PATH = "/tmp/exostream.sock"
    DEFAULT_TIMEOUT = 5.0  # seconds
    BUFFER_SIZE = 4096
    
    def __init__(self, socket_path: Optional[str] = None, 
                 timeout: float = DEFAULT_TIMEOUT):
        """
        Initialize IPC client
        
        Args:
            socket_path: Path to Unix socket (defaults to /tmp/exostream.sock)
            timeout: Timeout in seconds for socket operations
        """
        self.socket_path = socket_path or self.DEFAULT_SOCKET_PATH
        self.timeout = timeout
        self._request_id = 0
    
    def _get_next_id(self) -> int:
        """Get next request ID"""
        self._request_id += 1
        return self._request_id
    
    def is_daemon_running(self) -> bool:
        """
        Check if daemon is running
        
        Returns:
            True if daemon is running, False otherwise
        """
        try:
            # Try to ping the daemon
            self.call("daemon.ping", {})
            return True
        except (DaemonNotRunningError, DaemonTimeoutError, OSError):
            return False
        except Exception as e:
            logger.debug(f"Error checking daemon status: {e}")
            return False
    
    def call(self, method: str, params: Optional[Dict[str, Any]] = None,
             timeout: Optional[float] = None) -> Any:
        """
        Call a method on the daemon
        
        Args:
            method: Method name (e.g., "stream.start")
            params: Method parameters
            timeout: Timeout override (uses default if not specified)
        
        Returns:
            Result from the daemon
        
        Raises:
            DaemonNotRunningError: If daemon is not running
            DaemonTimeoutError: If daemon doesn't respond in time
            DaemonRPCError: If daemon returns an error
            IPCClientError: For other errors
        """
        timeout = timeout or self.timeout
        
        # Create request
        request = create_request(method, params or {}, self._get_next_id())
        
        # Send request and receive response
        try:
            response_data = self._send_and_receive(request.to_json(), timeout)
        except socket.error as e:
            if e.errno == 2:  # No such file or directory
                raise DaemonNotRunningError(
                    f"Daemon is not running (socket not found: {self.socket_path})"
                )
            elif e.errno == 111:  # Connection refused
                raise DaemonNotRunningError(
                    f"Daemon is not running (connection refused)"
                )
            else:
                raise IPCClientError(f"Socket error: {e}")
        except socket.timeout:
            raise DaemonTimeoutError(
                f"Daemon did not respond within {timeout} seconds"
            )
        
        # Parse response
        try:
            response = RPCResponse.from_json(response_data)
        except json.JSONDecodeError as e:
            raise IPCClientError(f"Invalid JSON response: {e}")
        
        # Check for errors
        if response.error is not None:
            error = response.error
            raise DaemonRPCError(
                code=error['code'],
                message=error['message'],
                data=error.get('data')
            )
        
        return response.result
    
    def _send_and_receive(self, data: str, timeout: float) -> str:
        """
        Send data and receive response via Unix socket
        
        Args:
            data: JSON string to send
            timeout: Timeout in seconds
        
        Returns:
            Response data as string
        
        Raises:
            socket.error: On socket errors
            socket.timeout: On timeout
        """
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.settimeout(timeout)
            
            # Connect to daemon
            logger.debug(f"Connecting to {self.socket_path}")
            sock.connect(self.socket_path)
            
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
    
    def call_with_retry(self, method: str, params: Optional[Dict[str, Any]] = None,
                       retries: int = 3, retry_delay: float = 0.5) -> Any:
        """
        Call a method with automatic retry on transient errors
        
        Args:
            method: Method name
            params: Method parameters
            retries: Number of retries
            retry_delay: Delay between retries in seconds
        
        Returns:
            Result from the daemon
        
        Raises:
            Same exceptions as call()
        """
        last_error = None
        
        for attempt in range(retries + 1):
            try:
                return self.call(method, params)
            except (DaemonTimeoutError, socket.timeout) as e:
                last_error = e
                if attempt < retries:
                    logger.debug(f"Retry {attempt + 1}/{retries} after timeout")
                    time.sleep(retry_delay)
                    continue
                raise
            except DaemonNotRunningError:
                # Don't retry if daemon is not running
                raise
            except DaemonRPCError:
                # Don't retry RPC errors (they're application-level errors)
                raise
            except Exception as e:
                last_error = e
                if attempt < retries:
                    logger.debug(f"Retry {attempt + 1}/{retries} after error: {e}")
                    time.sleep(retry_delay)
                    continue
                raise
        
        # Should never reach here, but just in case
        if last_error:
            raise last_error


class IPCClientManager:
    """High-level manager for IPC client with method helpers"""
    
    def __init__(self, socket_path: Optional[str] = None):
        """
        Initialize IPC client manager
        
        Args:
            socket_path: Path to Unix socket
        """
        self.client = IPCClient(socket_path)
    
    def is_daemon_running(self) -> bool:
        """Check if daemon is running"""
        return self.client.is_daemon_running()
    
    def ping(self) -> bool:
        """
        Ping the daemon
        
        Returns:
            True if daemon responds
        """
        try:
            result = self.client.call("daemon.ping", {})
            return result.get('pong', False)
        except Exception:
            return False
    
    def start_stream(self, device: str, name: str, resolution: str = "1920x1080",
                    fps: int = 30, raw_input: bool = False,
                    groups: Optional[str] = None) -> Dict[str, Any]:
        """
        Start streaming
        
        Args:
            device: Device path (e.g., /dev/video0)
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
        # Use longer timeout for start command (10s) since FFmpeg startup can be slow
        return self.client.call("stream.start", params, timeout=10.0)
    
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
    
    def shutdown_daemon(self) -> Dict[str, Any]:
        """
        Shutdown the daemon
        
        Returns:
            Result dictionary
        """
        return self.client.call("daemon.shutdown", {})

