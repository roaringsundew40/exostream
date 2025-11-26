"""IPC Server using Unix Domain Sockets"""

import socket
import os
import threading
import logging
from pathlib import Path
from typing import Optional, Callable, Dict, Any
import json
import traceback

from exostream.common.protocol import (
    RPCRequest, RPCResponse, RPCError,
    create_error_response
)

logger = logging.getLogger(__name__)


class IPCServer:
    """Unix domain socket server for IPC communication"""
    
    DEFAULT_SOCKET_PATH = "/tmp/exostream.sock"  # Will use /var/run in production
    BUFFER_SIZE = 4096
    
    def __init__(self, socket_path: Optional[str] = None, 
                 handler: Optional[Callable] = None):
        """
        Initialize IPC server
        
        Args:
            socket_path: Path to Unix socket (defaults to /tmp/exostream.sock)
            handler: Callable that handles RPCRequest and returns RPCResponse
        """
        self.socket_path = socket_path or self.DEFAULT_SOCKET_PATH
        self.handler = handler or self._default_handler
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.server_thread: Optional[threading.Thread] = None
        self._client_handlers: Dict[int, threading.Thread] = {}
        self._lock = threading.Lock()
    
    def _default_handler(self, request: RPCRequest) -> RPCResponse:
        """Default handler that returns method not found"""
        return create_error_response(
            RPCError.METHOD_NOT_FOUND,
            f"Method '{request.method}' not found",
            request_id=request.id
        )
    
    def start(self):
        """Start the IPC server"""
        if self.running:
            logger.warning("IPC server already running")
            return
        
        # Remove existing socket file if it exists
        if os.path.exists(self.socket_path):
            logger.info(f"Removing existing socket file: {self.socket_path}")
            os.remove(self.socket_path)
        
        # Create socket directory if needed
        socket_dir = os.path.dirname(self.socket_path)
        if socket_dir and not os.path.exists(socket_dir):
            os.makedirs(socket_dir, mode=0o755)
        
        # Create Unix domain socket
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.bind(self.socket_path)
        self.socket.listen(5)
        
        # Set socket permissions (readable/writable by owner and group)
        os.chmod(self.socket_path, 0o660)
        
        self.running = True
        
        # Start server thread
        self.server_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self.server_thread.start()
        
        logger.info(f"IPC server started on {self.socket_path}")
    
    def stop(self):
        """Stop the IPC server"""
        if not self.running:
            return
        
        logger.info("Stopping IPC server...")
        self.running = False
        
        # Close server socket
        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                logger.error(f"Error closing server socket: {e}")
        
        # Wait for server thread
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=2.0)
        
        # Wait for client handler threads
        with self._lock:
            for thread_id, thread in list(self._client_handlers.items()):
                if thread.is_alive():
                    thread.join(timeout=1.0)
            self._client_handlers.clear()
        
        # Remove socket file
        if os.path.exists(self.socket_path):
            try:
                os.remove(self.socket_path)
                logger.info(f"Removed socket file: {self.socket_path}")
            except Exception as e:
                logger.error(f"Error removing socket file: {e}")
        
        logger.info("IPC server stopped")
    
    def _accept_loop(self):
        """Accept incoming connections"""
        logger.debug("Accept loop started")
        
        while self.running:
            try:
                # Accept connection (with timeout to allow clean shutdown)
                self.socket.settimeout(1.0)
                try:
                    client_socket, _ = self.socket.accept()
                except socket.timeout:
                    continue
                
                # Handle client in separate thread
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket,),
                    daemon=True
                )
                
                with self._lock:
                    thread_id = id(client_thread)
                    self._client_handlers[thread_id] = client_thread
                
                client_thread.start()
                
            except Exception as e:
                if self.running:  # Only log if we're still supposed to be running
                    logger.error(f"Error in accept loop: {e}")
        
        logger.debug("Accept loop stopped")
    
    def _handle_client(self, client_socket: socket.socket):
        """Handle a client connection"""
        thread_id = threading.get_ident()
        logger.debug(f"Client connected (thread {thread_id})")
        
        try:
            # Receive data (may need multiple reads for large messages)
            data_chunks = []
            while True:
                chunk = client_socket.recv(self.BUFFER_SIZE)
                if not chunk:
                    break
                data_chunks.append(chunk)
                
                # Check if we have a complete JSON message
                # (ends with newline or closing brace)
                if chunk.endswith(b'\n') or chunk.endswith(b'}'):
                    break
            
            if not data_chunks:
                logger.debug("Client disconnected without sending data")
                return
            
            data = b''.join(data_chunks).decode('utf-8')
            logger.debug(f"Received: {data[:200]}...")  # Log first 200 chars
            
            # Parse request
            try:
                request = RPCRequest.from_json(data)
                logger.debug(f"Parsed request: method={request.method}, id={request.id}")
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error: {e}")
                response = create_error_response(
                    RPCError.PARSE_ERROR,
                    f"Invalid JSON: {str(e)}"
                )
                self._send_response(client_socket, response)
                return
            except Exception as e:
                logger.error(f"Request parse error: {e}")
                response = create_error_response(
                    RPCError.INVALID_REQUEST,
                    f"Invalid request: {str(e)}"
                )
                self._send_response(client_socket, response)
                return
            
            # Handle request
            try:
                response = self.handler(request)
                logger.debug(f"Handler returned response for request {request.id}")
            except Exception as e:
                logger.error(f"Handler error: {e}")
                logger.debug(traceback.format_exc())
                response = create_error_response(
                    RPCError.INTERNAL_ERROR,
                    f"Internal error: {str(e)}",
                    data={'traceback': traceback.format_exc()},
                    request_id=request.id
                )
            
            # Send response
            self._send_response(client_socket, response)
            
        except Exception as e:
            logger.error(f"Error handling client: {e}")
            logger.debug(traceback.format_exc())
        finally:
            client_socket.close()
            with self._lock:
                if thread_id in self._client_handlers:
                    del self._client_handlers[thread_id]
            logger.debug(f"Client disconnected (thread {thread_id})")
    
    def _send_response(self, client_socket: socket.socket, response: RPCResponse):
        """Send response to client"""
        try:
            response_json = response.to_json()
            logger.debug(f"Sending response: {response_json[:200]}...")
            
            # Send with newline delimiter
            client_socket.sendall(response_json.encode('utf-8') + b'\n')
        except Exception as e:
            logger.error(f"Error sending response: {e}")


class IPCServerManager:
    """High-level manager for IPC server with method routing"""
    
    def __init__(self, socket_path: Optional[str] = None):
        """
        Initialize IPC server manager
        
        Args:
            socket_path: Path to Unix socket
        """
        self.server = IPCServer(socket_path, handler=self._route_request)
        self._handlers: Dict[str, Callable] = {}
        self._lock = threading.Lock()
    
    def register_handler(self, method: str, handler: Callable[[Dict[str, Any]], Any]):
        """
        Register a handler for a specific method
        
        Args:
            method: Method name (e.g., "stream.start")
            handler: Callable that takes params dict and returns result
        """
        with self._lock:
            self._handlers[method] = handler
            logger.debug(f"Registered handler for method: {method}")
    
    def unregister_handler(self, method: str):
        """Unregister a handler"""
        with self._lock:
            if method in self._handlers:
                del self._handlers[method]
                logger.debug(f"Unregistered handler for method: {method}")
    
    def _route_request(self, request: RPCRequest) -> RPCResponse:
        """Route request to appropriate handler"""
        logger.debug(f"Routing request: method={request.method}")
        
        with self._lock:
            handler = self._handlers.get(request.method)
        
        if not handler:
            logger.warning(f"No handler for method: {request.method}")
            return create_error_response(
                RPCError.METHOD_NOT_FOUND,
                f"Method '{request.method}' not found",
                request_id=request.id
            )
        
        try:
            # Call handler with params
            result = handler(request.params)
            return RPCResponse.success(result, request_id=request.id)
        except Exception as e:
            # Internal error (including ValueError from handler)
            logger.error(f"Handler error for {request.method}: {e}")
            logger.debug(traceback.format_exc())
            return create_error_response(
                RPCError.INTERNAL_ERROR,
                str(e),
                data={'traceback': traceback.format_exc()},
                request_id=request.id
            )
    
    def start(self):
        """Start the IPC server"""
        self.server.start()
    
    def stop(self):
        """Stop the IPC server"""
        self.server.stop()
    
    @property
    def socket_path(self) -> str:
        """Get the socket path"""
        return self.server.socket_path
    
    @property
    def running(self) -> bool:
        """Check if server is running"""
        return self.server.running

