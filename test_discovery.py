#!/usr/bin/env python3
"""
Test script for UDP broadcast discovery

This script helps debug discovery issues by showing exactly what's happening.
"""

import sys
import time
from exostream.common.discovery import ExostreamServicePublisher, ExostreamServiceDiscovery

def test_publisher():
    """Test publishing a service"""
    print("=" * 60)
    print("TESTING SERVICE PUBLISHER (UDP Broadcast)")
    print("=" * 60)
    
    publisher = ExostreamServicePublisher(port=9023, name="test-camera")
    
    print("\n1. Starting publisher...")
    publisher.start()
    
    print("2. Broadcasting announcements every 3 seconds")
    print("3. Service should now be visible on network")
    print("4. Press Ctrl+C to stop")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n5. Stopping publisher...")
        publisher.stop()
        print("6. Done!")

def test_discovery():
    """Test discovering services"""
    print("=" * 60)
    print("TESTING SERVICE DISCOVERY (UDP Broadcast)")
    print("=" * 60)
    
    def on_service_change(event_type, data):
        print(f"\n>>> SERVICE EVENT: {event_type}")
        if event_type in ('added', 'updated'):
            print(f"    Name: {data.name}")
            print(f"    Hostname: {data.hostname}")
            print(f"    Host: {data.host}")
            print(f"    Port: {data.port}")
            print(f"    Version: {data.version}")
        elif event_type == 'removed':
            print(f"    Name: {data.name}")
            print(f"    Host: {data.host}:{data.port}")
    
    discovery = ExostreamServiceDiscovery(callback=on_service_change)
    
    print("\n1. Starting discovery...")
    discovery.start()
    
    print("2. Listening for UDP broadcasts on port 5354...")
    print("3. Start a daemon in another terminal: exostreamd")
    print("4. Press Ctrl+C to stop")
    
    try:
        while True:
            time.sleep(1)
            # Show current services
            services = discovery.get_services()
            if services:
                print(f"\rCurrently {len(services)} service(s) found", end='', flush=True)
    except KeyboardInterrupt:
        print("\n\n5. Stopping discovery...")
        discovery.stop()
        print("6. Done!")

def test_both():
    """Test both publisher and discovery in same process"""
    print("=" * 60)
    print("TESTING BOTH PUBLISHER AND DISCOVERY (UDP Broadcast)")
    print("=" * 60)
    
    # Start publisher
    print("\n1. Starting publisher...")
    publisher = ExostreamServicePublisher(port=9023, name="test-camera")
    publisher.start()
    
    # Wait a moment for first broadcast
    print("2. Waiting for first broadcast (5 seconds)...")
    time.sleep(5)
    
    # Start discovery
    print("3. Starting discovery...")
    
    found_services = []
    
    def on_service_change(event_type, data):
        print(f"\n>>> SERVICE EVENT: {event_type}")
        if event_type in ('added', 'updated'):
            print(f"    Name: {data.name}")
            print(f"    Host: {data.host}:{data.port}")
            if event_type == 'added':
                found_services.append(data.name)
    
    discovery = ExostreamServiceDiscovery(callback=on_service_change)
    discovery.start()
    
    print("4. Waiting for discovery (10 seconds)...")
    time.sleep(10)
    
    # Check results
    print("\n5. Results:")
    services = discovery.get_services()
    print(f"   Found {len(services)} service(s)")
    for svc in services:
        print(f"   - {svc['name']} ({svc['hostname']}) at {svc['host']}:{svc['port']}")
    
    if found_services:
        print("\n✓ SUCCESS: Discovery working!")
        print("   UDP broadcast discovery is functioning correctly")
    else:
        print("\n✗ FAILED: No services discovered")
        print("\nPossible issues:")
        print("  - Firewall blocking UDP port 5354")
        print("  - Network doesn't allow broadcast traffic")
        print("  - Publisher and discovery on different networks")
    
    # Cleanup
    print("\n6. Cleaning up...")
    discovery.stop()
    publisher.stop()
    print("7. Done!")

if __name__ == "__main__":
    print("\nExostream Discovery Test")
    print("=" * 60)
    print("\nChoose a test:")
    print("  1. Test Publisher only")
    print("  2. Test Discovery only")
    print("  3. Test Both (self-test)")
    print()
    
    choice = input("Enter choice (1/2/3) or press Enter for option 3: ").strip()
    
    if choice == "1":
        test_publisher()
    elif choice == "2":
        test_discovery()
    else:
        test_both()

