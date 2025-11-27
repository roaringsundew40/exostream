"""Main daemon entry point"""

import os
import sys
import signal
import logging
import time
from pathlib import Path
from typing import Dict, Any

from exostream.daemon.ipc_server import IPCServerManager
from exostream.daemon.service import (
    StreamingService, 
    StreamAlreadyRunningError,
    StreamNotRunningError,
    DeviceNotFoundError,
    StreamingError
)
from exostream.daemon.state_manager import StateManager
from exostream.common.protocol import (
    Methods, 
    RPCError,
    StartStreamParams
)
from exostream.common.logger import setup_logger, get_logger

# Version
__version__ = "0.3.0"

logger = get_logger(__name__)


class ExostreamDaemon:
    """
    Main daemon process
    
    Manages:
    - IPC server for command handling
    - Streaming service
    - State persistence
    - Signal handling
    """
    
    DEFAULT_SOCKET_PATH = "/tmp/exostream.sock"
    
    def __init__(self, socket_path: str = DEFAULT_SOCKET_PATH,
                 state_dir: Path = None):
        """
        Initialize daemon
        
        Args:
            socket_path: Path to Unix socket
            state_dir: Directory for state files
        """
        self.socket_path = socket_path
        self.state_manager = StateManager(state_dir)
        self.streaming_service = StreamingService(self.state_manager)
        self.ipc_server = IPCServerManager(socket_path)
        
        self._running = False
        self._setup_signal_handlers()
        self._register_handlers()
        
        logger.info(f"ExostreamDaemon v{__version__} initialized")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def _register_handlers(self):
        """Register all RPC method handlers"""
        
        # Stream control methods
        self.ipc_server.register_handler(
            Methods.STREAM_START,
            self._handle_stream_start
        )
        self.ipc_server.register_handler(
            Methods.STREAM_STOP,
            self._handle_stream_stop
        )
        self.ipc_server.register_handler(
            Methods.STREAM_STATUS,
            self._handle_stream_status
        )
        
        # Device management
        self.ipc_server.register_handler(
            Methods.DEVICES_LIST,
            self._handle_devices_list
        )
        
        # Daemon control
        self.ipc_server.register_handler(
            Methods.DAEMON_STATUS,
            self._handle_daemon_status
        )
        self.ipc_server.register_handler(
            Methods.DAEMON_PING,
            self._handle_daemon_ping
        )
        self.ipc_server.register_handler(
            Methods.DAEMON_SHUTDOWN,
            self._handle_daemon_shutdown
        )
        
        logger.info("RPC handlers registered")
    
    # ========================================================================
    # RPC Method Handlers
    # ========================================================================
    
    def _handle_stream_start(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle stream.start method
        
        Args:
            params: Stream parameters
        
        Returns:
            Result dictionary
        
        Raises:
            Exception: Converted to appropriate RPC error by server
        """
        logger.info(f"RPC: stream.start called with params: {params}")
        
        # Parse parameters
        try:
            stream_params = StartStreamParams.from_dict(params)
        except Exception as e:
            raise ValueError(f"Invalid parameters: {e}")
        
        # Start streaming
        try:
            result = self.streaming_service.start_streaming(
                device=stream_params.device,
                name=stream_params.name,
                resolution=stream_params.resolution,
                fps=stream_params.fps,
                raw_input=stream_params.raw_input,
                groups=stream_params.groups
            )
            return result
        except StreamAlreadyRunningError as e:
            # Return specific error for already running
            raise StreamingError(f"Stream already running: {e}")
        except DeviceNotFoundError as e:
            raise StreamingError(f"Device not found: {e}")
        except Exception as e:
            raise StreamingError(f"Failed to start stream: {e}")
    
    def _handle_stream_stop(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle stream.stop method
        
        Args:
            params: Parameters (currently unused)
        
        Returns:
            Result dictionary
        """
        logger.info("RPC: stream.stop called")
        
        try:
            result = self.streaming_service.stop_streaming()
            return result
        except StreamNotRunningError as e:
            raise StreamingError(f"Stream not running: {e}")
        except Exception as e:
            raise StreamingError(f"Failed to stop stream: {e}")
    
    def _handle_stream_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle stream.status method
        
        Args:
            params: Parameters (currently unused)
        
        Returns:
            Status dictionary
        """
        logger.debug("RPC: stream.status called")
        
        try:
            status = self.streaming_service.get_status()
            return status
        except Exception as e:
            logger.error(f"Error getting stream status: {e}")
            raise StreamingError(f"Failed to get status: {e}")
    
    def _handle_devices_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle devices.list method
        
        Args:
            params: Parameters (currently unused)
        
        Returns:
            Dictionary with devices list
        """
        logger.debug("RPC: devices.list called")
        
        try:
            devices = self.streaming_service.list_devices()
            return {"devices": devices}
        except Exception as e:
            logger.error(f"Error listing devices: {e}")
            raise StreamingError(f"Failed to list devices: {e}")
    
    def _handle_daemon_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle daemon.status method
        
        Args:
            params: Parameters (currently unused)
        
        Returns:
            Daemon status dictionary
        """
        logger.debug("RPC: daemon.status called")
        
        try:
            daemon_info = self.state_manager.get_daemon_info()
            uptime = self.state_manager.get_uptime_seconds()
            
            status = {
                "running": True,
                "version": __version__,
                "uptime_seconds": uptime or 0.0,
                "pid": os.getpid()
            }
            
            # Add health check info
            health = self.streaming_service.health_check()
            status["health"] = health
            
            return status
        except Exception as e:
            logger.error(f"Error getting daemon status: {e}")
            raise StreamingError(f"Failed to get daemon status: {e}")
    
    def _handle_daemon_ping(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle daemon.ping method (health check)
        
        Args:
            params: Parameters (currently unused)
        
        Returns:
            Pong response
        """
        logger.debug("RPC: daemon.ping called")
        return {"pong": True}
    
    def _handle_daemon_shutdown(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle daemon.shutdown method
        
        Args:
            params: Parameters (currently unused)
        
        Returns:
            Shutdown acknowledgment
        """
        logger.info("RPC: daemon.shutdown called")
        
        # Stop in a separate thread to allow response to be sent
        import threading
        def shutdown_thread():
            time.sleep(0.5)  # Give time for response
            self.stop()
        
        threading.Thread(target=shutdown_thread, daemon=True).start()
        
        return {"status": "shutting_down"}
    
    # ========================================================================
    # Daemon Lifecycle
    # ========================================================================
    
    def start(self):
        """Start the daemon"""
        logger.info("Starting daemon...")
        
        # Mark daemon as started
        self.state_manager.set_daemon_started(os.getpid())
        
        # Start IPC server
        self.ipc_server.start()
        logger.info(f"IPC server listening on {self.socket_path}")
        
        self._running = True
        logger.info("Daemon started successfully")
        
        # Main loop
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the daemon"""
        if not self._running:
            return
        
        logger.info("Stopping daemon...")
        self._running = False
        
        # Stop streaming if active
        try:
            if self.streaming_service.is_streaming():
                logger.info("Stopping active stream...")
                self.streaming_service.stop_streaming()
        except Exception as e:
            logger.error(f"Error stopping stream: {e}")
        
        # Stop IPC server
        try:
            self.ipc_server.stop()
        except Exception as e:
            logger.error(f"Error stopping IPC server: {e}")
        
        # Cleanup
        try:
            self.streaming_service.cleanup()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        logger.info("Daemon stopped")
    
    def is_running(self) -> bool:
        """Check if daemon is running"""
        return self._running


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Exostream Daemon - NDI streaming service"
    )
    parser.add_argument(
        "--socket",
        default=ExostreamDaemon.DEFAULT_SOCKET_PATH,
        help="Unix socket path"
    )
    parser.add_argument(
        "--state-dir",
        type=Path,
        help="State directory"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose logging"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"exostreamd {__version__}"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logger("exostream", log_level)
    
    logger.info(f"Exostream Daemon v{__version__}")
    logger.info(f"Socket: {args.socket}")
    if args.state_dir:
        logger.info(f"State directory: {args.state_dir}")
    
    # Create and start daemon
    try:
        daemon = ExostreamDaemon(
            socket_path=args.socket,
            state_dir=args.state_dir
        )
        daemon.start()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.exception("Traceback:")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

