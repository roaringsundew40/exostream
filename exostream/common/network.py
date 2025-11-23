"""Network utilities for port checking and interface detection"""

import socket
import psutil
from typing import List, Optional


def is_port_available(port: int, host: str = "0.0.0.0") -> bool:
    """
    Check if a port is available for binding
    
    Args:
        port: Port number to check
        host: Host address to bind to
    
    Returns:
        True if port is available, False otherwise
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        sock.close()
        return True
    except OSError:
        return False


def get_local_ip() -> Optional[str]:
    """
    Get the local IP address of the machine
    
    Returns:
        Local IP address or None if not found
    """
    try:
        # Create a socket to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return None


def get_network_interfaces() -> List[dict]:
    """
    Get all network interfaces with their addresses
    
    Returns:
        List of dictionaries containing interface information
    """
    interfaces = []
    
    for interface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET:  # IPv4 only
                interfaces.append({
                    'name': interface,
                    'address': addr.address,
                    'netmask': addr.netmask,
                })
    
    return interfaces


def format_bandwidth(bytes_per_sec: float) -> str:
    """
    Format bandwidth in human-readable format
    
    Args:
        bytes_per_sec: Bandwidth in bytes per second
    
    Returns:
        Formatted string (e.g., "5.2 Mbps")
    """
    bits_per_sec = bytes_per_sec * 8
    
    if bits_per_sec < 1000:
        return f"{bits_per_sec:.1f} bps"
    elif bits_per_sec < 1_000_000:
        return f"{bits_per_sec / 1000:.1f} Kbps"
    elif bits_per_sec < 1_000_000_000:
        return f"{bits_per_sec / 1_000_000:.1f} Mbps"
    else:
        return f"{bits_per_sec / 1_000_000_000:.1f} Gbps"

