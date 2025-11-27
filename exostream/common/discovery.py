"""
Network discovery service using mDNS/Zeroconf

Allows Exostream daemons to advertise themselves on the network
and clients to discover them automatically (like NDI discovery).
"""

import socket
import logging
from typing import List, Dict, Optional, Callable
from zeroconf import Zeroconf, ServiceInfo, ServiceBrowser, ServiceListener

logger = logging.getLogger(__name__)

# Service type for Exostream control
EXOSTREAM_SERVICE_TYPE = "_exostream._tcp.local."


class ExostreamServicePublisher:
    """
    Publishes Exostream daemon on the network using mDNS/Zeroconf
    
    This allows clients to discover the daemon without knowing its IP address.
    Similar to how NDI devices are discovered.
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
        self.zeroconf: Optional[Zeroconf] = None
        self.service_info: Optional[ServiceInfo] = None
        
    def start(self):
        """Start advertising the service"""
        try:
            self.zeroconf = Zeroconf()
            
            # Get local IP address
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            
            # Create service info
            service_name = f"{self.name}.{EXOSTREAM_SERVICE_TYPE}"
            
            # Service properties (metadata) - must be bytes
            properties = {
                b'version': b'0.4.0',
                b'type': b'exostream-daemon',
                b'hostname': hostname.encode('utf-8')
            }
            
            self.service_info = ServiceInfo(
                EXOSTREAM_SERVICE_TYPE,
                service_name,
                addresses=[socket.inet_aton(local_ip)],
                port=self.port,
                properties=properties,
                server=f"{hostname}.local."
            )
            
            # Register service
            self.zeroconf.register_service(self.service_info)
            
            logger.info(f"Service published: {self.name} at {local_ip}:{self.port}")
            logger.info(f"Service name: {service_name}")
            print(f"DEBUG: Service published: {service_name} at {local_ip}:{self.port}")
            
        except Exception as e:
            logger.error(f"Failed to publish service: {e}")
            print(f"DEBUG ERROR: Failed to publish: {e}")
            import traceback
            traceback.print_exc()
            if self.zeroconf:
                self.zeroconf.close()
                self.zeroconf = None
    
    def stop(self):
        """Stop advertising the service"""
        if self.zeroconf and self.service_info:
            try:
                logger.info(f"Unregistering service: {self.name}")
                self.zeroconf.unregister_service(self.service_info)
                self.zeroconf.close()
                logger.info("Service unregistered successfully")
            except Exception as e:
                logger.error(f"Error unregistering service: {e}")
            finally:
                self.zeroconf = None
                self.service_info = None


class ExostreamServiceListener(ServiceListener):
    """
    Listener for Exostream service events
    
    Called when services are added, removed, or updated.
    """
    
    def __init__(self, callback: Optional[Callable] = None):
        """
        Initialize listener
        
        Args:
            callback: Function to call when services change
        """
        self.callback = callback
        
    def add_service(self, zeroconf: Zeroconf, service_type: str, name: str):
        """Called when a service is discovered"""
        logger.info(f"Service added: {name}")
        print(f"DEBUG: Service added: {name}")  # Debug output
        if self.callback:
            info = zeroconf.get_service_info(service_type, name)
            if info:
                logger.info(f"Got service info for {name}: {info}")
                print(f"DEBUG: Got service info: {info}")
                self.callback('added', info)
            else:
                logger.warning(f"Could not get service info for {name}")
                print(f"DEBUG: No service info for {name}")
    
    def remove_service(self, zeroconf: Zeroconf, service_type: str, name: str):
        """Called when a service is removed"""
        logger.debug(f"Service removed: {name}")
        if self.callback:
            self.callback('removed', name)
    
    def update_service(self, zeroconf: Zeroconf, service_type: str, name: str):
        """Called when a service is updated"""
        logger.debug(f"Service updated: {name}")
        if self.callback:
            info = zeroconf.get_service_info(service_type, name)
            if info:
                self.callback('updated', info)


class ExostreamServiceDiscovery:
    """
    Discovers Exostream daemons on the network
    
    Provides a list of available daemons with their addresses and ports.
    """
    
    def __init__(self, callback: Optional[Callable] = None):
        """
        Initialize discovery client
        
        Args:
            callback: Function to call when services change
                     Signature: callback(event_type, service_info)
        """
        self.callback = callback
        self.zeroconf: Optional[Zeroconf] = None
        self.browser: Optional[ServiceBrowser] = None
        self.listener: Optional[ExostreamServiceListener] = None
        self.services: Dict[str, ServiceInfo] = {}
        
    def start(self):
        """Start discovering services"""
        try:
            self.zeroconf = Zeroconf()
            self.listener = ExostreamServiceListener(self._on_service_change)
            self.browser = ServiceBrowser(
                self.zeroconf,
                EXOSTREAM_SERVICE_TYPE,
                self.listener
            )
            logger.info("Service discovery started")
        except Exception as e:
            logger.error(f"Failed to start service discovery: {e}")
            if self.zeroconf:
                self.zeroconf.close()
                self.zeroconf = None
    
    def stop(self):
        """Stop discovering services"""
        if self.browser:
            self.browser.cancel()
            self.browser = None
        
        if self.zeroconf:
            try:
                self.zeroconf.close()
            except Exception as e:
                logger.error(f"Error closing zeroconf: {e}")
            finally:
                self.zeroconf = None
        
        self.services.clear()
        logger.info("Service discovery stopped")
    
    def _on_service_change(self, event_type: str, data):
        """Handle service change events"""
        if event_type == 'added' and isinstance(data, ServiceInfo):
            # Add service to our list
            self.services[data.name] = data
            logger.info(f"Discovered: {data.name}")
            
            # Notify callback
            if self.callback:
                self.callback(event_type, data)
                
        elif event_type == 'removed' and isinstance(data, str):
            # Remove service from our list
            if data in self.services:
                del self.services[data]
                logger.info(f"Lost: {data}")
            
            # Notify callback
            if self.callback:
                self.callback(event_type, data)
                
        elif event_type == 'updated' and isinstance(data, ServiceInfo):
            # Update service in our list
            self.services[data.name] = data
            logger.info(f"Updated: {data.name}")
            
            # Notify callback
            if self.callback:
                self.callback(event_type, data)
    
    def get_services(self) -> List[Dict[str, any]]:
        """
        Get list of discovered services
        
        Returns:
            List of service dictionaries with name, host, port, etc.
        """
        services = []
        
        for name, info in self.services.items():
            # Get IP address
            addresses = [socket.inet_ntoa(addr) for addr in info.addresses]
            host = addresses[0] if addresses else "unknown"
            
            # Get properties
            properties = {
                key.decode('utf-8') if isinstance(key, bytes) else key:
                val.decode('utf-8') if isinstance(val, bytes) else val
                for key, val in info.properties.items()
            }
            
            # Create service dict
            service = {
                'name': name.replace(f'.{EXOSTREAM_SERVICE_TYPE}', ''),
                'full_name': name,
                'host': host,
                'port': info.port,
                'hostname': properties.get('hostname', 'unknown'),
                'version': properties.get('version', 'unknown'),
                'type': properties.get('type', 'unknown')
            }
            
            services.append(service)
        
        return services

