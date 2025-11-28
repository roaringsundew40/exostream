"""
Network discovery service using UDP broadcast

Allows Exostream daemons to advertise themselves on the network
and clients to discover them automatically (like NDI discovery).

Uses UDP broadcast for simplicity and reliability across all platforms.
No mDNS/Zeroconf dependencies - just simple UDP sockets.
"""

import socket
import json
import logging
import threading
import time
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Discovery protocol settings
DISCOVERY_PORT = 5354  # UDP port for discovery broadcasts
BROADCAST_INTERVAL = 3.0  # seconds between broadcasts
DISCOVERY_TIMEOUT = 10.0  # seconds before considering a service offline
DISCOVERY_MESSAGE_TYPE = "EXOSTREAM_ANNOUNCEMENT"


@dataclass
class ExostreamServiceInfo:
    """Information about a discovered Exostream service"""
    name: str
    hostname: str
    host: str
    port: int
    version: str
    last_seen: float


class ExostreamServicePublisher:
    """
    Publishes Exostream daemon on the network using UDP broadcast
    
    This allows clients to discover the daemon without knowing its IP address.
    Uses simple UDP broadcasts for maximum compatibility.
    """
    
    def __init__(self, port: int = 9023, name: Optional[str] = None):
        """
        Initialize service publisher
        
        Args:
            port: Network control port
            name: Service name (defaults to hostname)
        """
        self.port = port
        self.name = name or socket.gethostname()
        self.sock: Optional[socket.socket] = None
        self.running = False
        self.broadcast_thread: Optional[threading.Thread] = None
    
    def _get_local_ip(self) -> str:
        """Get local IP address (not 127.0.0.1)"""
        try:
            # Create a socket to find our actual IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            # Fallback to hostname lookup
            try:
                return socket.gethostbyname(socket.gethostname())
            except:
                return "127.0.0.1"
        
    def start(self):
        """Start advertising the service via UDP broadcast"""
        if self.running:
            logger.warning("Publisher already running")
            return
        
        try:
            # Get local IP
            local_ip = self._get_local_ip()
            hostname = socket.gethostname()
            
            # Create UDP socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            self.running = True
            
            # Start broadcast thread
            self.broadcast_thread = threading.Thread(
                target=self._broadcast_loop,
                args=(local_ip, hostname),
                daemon=True
            )
            self.broadcast_thread.start()
            
            logger.info(f"Service publisher started: {self.name} at {local_ip}:{self.port}")
            logger.info(f"Broadcasting on UDP port {DISCOVERY_PORT} every {BROADCAST_INTERVAL}s")
            
        except Exception as e:
            logger.error(f"Failed to start service publisher: {e}")
            self.running = False
            if self.sock:
                self.sock.close()
                self.sock = None
    
    def _broadcast_loop(self, local_ip: str, hostname: str):
        """Broadcast service announcement periodically"""
        logger.debug("Broadcast loop started")
        
        while self.running:
            try:
                # Create announcement message
                announcement = {
                    'type': DISCOVERY_MESSAGE_TYPE,
                    'name': self.name,
                    'hostname': hostname,
                    'host': local_ip,
                    'port': self.port,
                    'version': '0.4.0',
                    'timestamp': time.time()
                }
                
                # Broadcast to network
                message = json.dumps(announcement).encode('utf-8')
                self.sock.sendto(message, ('255.255.255.255', DISCOVERY_PORT))
                
                logger.debug(f"Broadcast sent: {self.name} at {local_ip}:{self.port}")
                
            except Exception as e:
                if self.running:  # Only log if we're still supposed to be running
                    logger.error(f"Error broadcasting: {e}")
            
            # Wait before next broadcast
            time.sleep(BROADCAST_INTERVAL)
        
        logger.debug("Broadcast loop stopped")
    
    def stop(self):
        """Stop advertising the service"""
        if not self.running:
            return
        
        logger.info(f"Stopping service publisher: {self.name}")
        self.running = False
        
        # Wait for broadcast thread to finish
        if self.broadcast_thread and self.broadcast_thread.is_alive():
            self.broadcast_thread.join(timeout=1.0)
        
        # Close socket
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None
        
        logger.info("Service publisher stopped")


class ExostreamServiceDiscovery:
    """
    Discovers Exostream daemons on the network via UDP broadcast
    
    Listens for broadcast announcements and maintains a list of active services.
    """
    
    def __init__(self, callback: Optional[Callable] = None):
        """
        Initialize discovery client
        
        Args:
            callback: Function to call when services change
                     Signature: callback(event_type, service_info)
                     event_type: 'added', 'removed', 'updated'
        """
        self.callback = callback
        self.sock: Optional[socket.socket] = None
        self.running = False
        self.listen_thread: Optional[threading.Thread] = None
        self.cleanup_thread: Optional[threading.Thread] = None
        self.services: Dict[str, ExostreamServiceInfo] = {}
        self.services_lock = threading.Lock()
    
    def start(self):
        """Start discovering services"""
        if self.running:
            logger.warning("Discovery already running")
            return
        
        try:
            # Create UDP socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(('', DISCOVERY_PORT))
            self.sock.settimeout(1.0)  # 1 second timeout for clean shutdown
            
            self.running = True
            
            # Start listening thread
            self.listen_thread = threading.Thread(
                target=self._listen_loop,
                daemon=True
            )
            self.listen_thread.start()
            
            # Start cleanup thread (removes stale services)
            self.cleanup_thread = threading.Thread(
                target=self._cleanup_loop,
                daemon=True
            )
            self.cleanup_thread.start()
            
            logger.info(f"Service discovery started, listening on UDP port {DISCOVERY_PORT}")
            
        except Exception as e:
            logger.error(f"Failed to start service discovery: {e}")
            self.running = False
            if self.sock:
                self.sock.close()
                self.sock = None
    
    def _listen_loop(self):
        """Listen for broadcast announcements"""
        logger.debug("Listen loop started")
        
        while self.running:
            try:
                # Receive broadcast message
                data, addr = self.sock.recvfrom(4096)
                
                # Parse JSON message
                try:
                    announcement = json.loads(data.decode('utf-8'))
                except json.JSONDecodeError:
                    logger.debug(f"Received invalid JSON from {addr}")
                    continue
                
                # Validate message type
                if announcement.get('type') != DISCOVERY_MESSAGE_TYPE:
                    continue
                
                # Extract service info
                name = announcement.get('name')
                hostname = announcement.get('hostname')
                host = announcement.get('host')
                port = announcement.get('port')
                version = announcement.get('version', 'unknown')
                
                if not all([name, hostname, host, port]):
                    logger.debug(f"Incomplete announcement from {addr}")
                    continue
                
                # Create/update service info
                service_key = f"{host}:{port}"
                now = time.time()
                
                with self.services_lock:
                    if service_key in self.services:
                        # Update existing service
                        old_service = self.services[service_key]
                        self.services[service_key] = ExostreamServiceInfo(
                            name=name,
                            hostname=hostname,
                            host=host,
                            port=port,
                            version=version,
                            last_seen=now
                        )
                        
                        event_type = 'updated'
                        logger.debug(f"Updated service: {name} at {host}:{port}")
                    else:
                        # Add new service
                        self.services[service_key] = ExostreamServiceInfo(
                            name=name,
                            hostname=hostname,
                            host=host,
                            port=port,
                            version=version,
                            last_seen=now
                        )
                        
                        event_type = 'added'
                        logger.info(f"Discovered service: {name} at {host}:{port}")
                    
                    service_info = self.services[service_key]
                
                # Notify callback
                if self.callback:
                    try:
                        self.callback(event_type, service_info)
                    except Exception as e:
                        logger.error(f"Error in callback: {e}")
                
            except socket.timeout:
                # Normal timeout, continue
                continue
            except Exception as e:
                if self.running:  # Only log if we're still supposed to be running
                    logger.error(f"Error receiving broadcast: {e}")
        
        logger.debug("Listen loop stopped")
    
    def _cleanup_loop(self):
        """Remove services that haven't been seen recently"""
        logger.debug("Cleanup loop started")
        
        while self.running:
            try:
                now = time.time()
                removed_services = []
                
                with self.services_lock:
                    # Find stale services
                    for key, service in list(self.services.items()):
                        if now - service.last_seen > DISCOVERY_TIMEOUT:
                            removed_services.append((key, service))
                            del self.services[key]
                            logger.info(f"Service timeout: {service.name} at {service.host}:{service.port}")
                
                # Notify callback for removed services
                if self.callback:
                    for key, service in removed_services:
                        try:
                            self.callback('removed', service)
                        except Exception as e:
                            logger.error(f"Error in callback: {e}")
                
            except Exception as e:
                if self.running:
                    logger.error(f"Error in cleanup loop: {e}")
            
            # Check every 2 seconds
            time.sleep(2.0)
        
        logger.debug("Cleanup loop stopped")
    
    def stop(self):
        """Stop discovering services"""
        if not self.running:
            return
        
        logger.info("Stopping service discovery")
        self.running = False
        
        # Wait for threads to finish
        if self.listen_thread and self.listen_thread.is_alive():
            self.listen_thread.join(timeout=2.0)
        
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=2.0)
        
        # Close socket
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None
        
        # Clear services
        with self.services_lock:
            self.services.clear()
        
        logger.info("Service discovery stopped")
    
    def get_services(self) -> List[Dict[str, Any]]:
        """
        Get list of discovered services
        
        Returns:
            List of service dictionaries with name, host, port, etc.
        """
        services = []
        
        with self.services_lock:
            for key, service in self.services.items():
                services.append({
                    'name': service.name,
                    'hostname': service.hostname,
                    'host': service.host,
                    'port': service.port,
                    'version': service.version,
                    'last_seen': service.last_seen
                })
        
        return services
