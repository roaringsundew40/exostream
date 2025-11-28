"""TCP Server for network-based control of the daemon"""

import socket
import threading
import logging
from typing import Optional, Callable, Dict, Any
import json
import traceback

from exostream.common.protocol import (
    RPCRequest, RPCResponse, RPCError,
    create_error_response
)
from exostream.common.config import NetworkConfig

logger = logging.getLogger(__name__)


class TCPControlServer:
    """TCP server for remote control via network"""
    
    BUFFER_SIZE = 4096
    
    def __init__(self, network_config: NetworkConfig,
                 handler: Optional[Callable] = None):
        """
        Initialize TCP control server
        
        Args:
            network_config: Network configuration (host, port, etc.)
            handler: Callable that handles RPCRequest and returns RPCResponse
        """
        self.config = network_config
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
        """Start the TCP server"""
        if self.running:
            logger.warning("TCP server already running")
            return
        
        if not self.config.enabled:
            logger.info("TCP server is disabled in configuration")
            return
        
        try:
            # Create TCP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # Allow socket reuse (prevents "Address already in use" errors)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Bind to host and port
            self.socket.bind((self.config.host, self.config.port))
            self.socket.listen(5)
            
            self.running = True
            
            # Start server thread
            self.server_thread = threading.Thread(
                target=self._accept_loop,
                daemon=True
            )
            self.server_thread.start()
            
            logger.info(f"TCP control server started on {self.config.host}:{self.config.port}")
            
        except OSError as e:
            if e.errno == 48:  # Address already in use
                logger.error(f"Port {self.config.port} is already in use")
                raise RuntimeError(f"Port {self.config.port} is already in use")
            else:
                logger.error(f"Failed to start TCP server: {e}")
                raise
        except Exception as e:
            logger.error(f"Failed to start TCP server: {e}")
            raise
    
    def stop(self):
        """Stop the TCP server"""
        if not self.running:
            return
        
        logger.info("Stopping TCP control server...")
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
        
        logger.info("TCP control server stopped")
    
    def _accept_loop(self):
        """Accept incoming connections"""
        logger.debug("TCP accept loop started")
        
        while self.running:
            try:
                # Accept connection (with timeout to allow clean shutdown)
                self.socket.settimeout(1.0)
                try:
                    client_socket, client_address = self.socket.accept()
                    logger.info(f"Client connected from {client_address}")
                except socket.timeout:
                    continue
                
                # Handle client in separate thread
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, client_address),
                    daemon=True
                )
                
                with self._lock:
                    thread_id = id(client_thread)
                    self._client_handlers[thread_id] = client_thread
                
                client_thread.start()
                
            except Exception as e:
                if self.running:  # Only log if we're still supposed to be running
                    logger.error(f"Error in accept loop: {e}")
        
        logger.debug("TCP accept loop stopped")
    
    def _handle_client(self, client_socket: socket.socket, client_address: tuple):
        """Handle a client connection"""
        thread_id = threading.get_ident()
        logger.debug(f"Handling client from {client_address} (thread {thread_id})")
        
        try:
            # Receive data (may need multiple reads for large messages)
            data_chunks = []
            while True:
                chunk = client_socket.recv(self.BUFFER_SIZE)
                if not chunk:
                    break
                data_chunks.append(chunk)
                
                # Check if we have a complete JSON message
                if chunk.endswith(b'\n') or chunk.endswith(b'}'):
                    break
            
            if not data_chunks:
                logger.debug(f"Client {client_address} disconnected without sending data")
                return
            
            data = b''.join(data_chunks).decode('utf-8')
            logger.debug(f"Received from {client_address}: {data[:200]}...")
            
            # Parse request
            try:
                request = RPCRequest.from_json(data)
                logger.debug(f"Parsed request from {client_address}: method={request.method}, id={request.id}")
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error from {client_address}: {e}")
                response = create_error_response(
                    RPCError.PARSE_ERROR,
                    f"Invalid JSON: {str(e)}"
                )
                self._send_response(client_socket, response)
                return
            except Exception as e:
                logger.error(f"Request parse error from {client_address}: {e}")
                response = create_error_response(
                    RPCError.INVALID_REQUEST,
                    f"Invalid request: {str(e)}"
                )
                self._send_response(client_socket, response)
                return
            
            # Handle request
            try:
                response = self.handler(request)
                logger.debug(f"Handler returned response for request {request.id} from {client_address}")
            except Exception as e:
                logger.error(f"Handler error from {client_address}: {e}")
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
            logger.error(f"Error handling client {client_address}: {e}")
            logger.debug(traceback.format_exc())
        finally:
            client_socket.close()
            with self._lock:
                if thread_id in self._client_handlers:
                    del self._client_handlers[thread_id]
            logger.debug(f"Client {client_address} disconnected (thread {thread_id})")
    
    def _send_response(self, client_socket: socket.socket, response: RPCResponse):
        """Send response to client"""
        try:
            response_json = response.to_json()
            logger.debug(f"Sending response: {response_json[:200]}...")
            
            # Send with newline delimiter
            client_socket.sendall(response_json.encode('utf-8') + b'\n')
        except Exception as e:
            logger.error(f"Error sending response: {e}")


class TCPServerManager:
    """High-level manager for TCP server with method routing"""
    
    def __init__(self, network_config: NetworkConfig):
        """
        Initialize TCP server manager
        
        Args:
            network_config: Network configuration
        """
        self.config = network_config
        self.server = TCPControlServer(network_config, handler=self._route_request)
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
            logger.debug(f"Registered TCP handler for method: {method}")
    
    def unregister_handler(self, method: str):
        """Unregister a handler"""
        with self._lock:
            if method in self._handlers:
                del self._handlers[method]
                logger.debug(f"Unregistered TCP handler for method: {method}")
    
    def _route_request(self, request: RPCRequest) -> RPCResponse:
        """Route request to appropriate handler"""
        logger.debug(f"Routing TCP request: method={request.method}")
        
        with self._lock:
            handler = self._handlers.get(request.method)
        
        if not handler:
            logger.warning(f"No TCP handler for method: {request.method}")
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
            logger.error(f"TCP handler error for {request.method}: {e}")
            logger.debug(traceback.format_exc())
            return create_error_response(
                RPCError.INTERNAL_ERROR,
                str(e),
                data={'traceback': traceback.format_exc()},
                request_id=request.id
            )
    
    def start(self):
        """Start the TCP server"""
        self.server.start()
    
    def stop(self):
        """Stop the TCP server"""
        self.server.stop()
    
    @property
    def running(self) -> bool:
        """Check if server is running"""
        return self.server.running
    
    @property
    def port(self) -> int:
        """Get the server port"""
        return self.config.port
    
    @property
    def host(self) -> str:
        """Get the server host"""
        return self.config.host

