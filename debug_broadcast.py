#!/usr/bin/env python3
"""
Debug script to test raw UDP broadcast/receive
"""

import socket
import json
import time
import sys

def test_send():
    """Test sending UDP broadcasts"""
    print("=" * 60)
    print("TESTING UDP BROADCAST SENDER")
    print("=" * 60)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    # Get local IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = socket.gethostbyname(socket.gethostname())
    
    print(f"Local IP: {local_ip}")
    print(f"Sending to: 255.255.255.255:5354")
    print("\nSending 10 test messages (1 per second)...")
    print("Run debug_broadcast.py receive on another machine!\n")
    
    for i in range(10):
        message = {
            'test': 'exostream-debug',
            'number': i + 1,
            'from': local_ip,
            'timestamp': time.time()
        }
        
        data = json.dumps(message).encode('utf-8')
        
        try:
            sock.sendto(data, ('255.255.255.255', 5354))
            print(f"[{i+1}/10] Sent {len(data)} bytes")
        except Exception as e:
            print(f"[{i+1}/10] ERROR: {e}")
        
        time.sleep(1)
    
    sock.close()
    print("\n✓ Done sending")

def test_receive():
    """Test receiving UDP broadcasts"""
    print("=" * 60)
    print("TESTING UDP BROADCAST RECEIVER")
    print("=" * 60)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # Try to enable SO_REUSEPORT if available
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        print("✓ SO_REUSEPORT enabled")
    except AttributeError:
        print("⚠ SO_REUSEPORT not available (Windows?)")
    except Exception as e:
        print(f"⚠ SO_REUSEPORT error: {e}")
    
    try:
        sock.bind(('', 5354))
        print(f"✓ Listening on 0.0.0.0:5354")
    except Exception as e:
        print(f"✗ Failed to bind: {e}")
        return
    
    sock.settimeout(1.0)
    
    print("\nWaiting for broadcasts (60 seconds)...")
    print("Run debug_broadcast.py send on another machine!\n")
    
    start_time = time.time()
    received_count = 0
    
    while time.time() - start_time < 60:
        try:
            data, addr = sock.recvfrom(4096)
            received_count += 1
            
            try:
                message = json.loads(data.decode('utf-8'))
                print(f"[{received_count}] From {addr[0]}:{addr[1]}")
                print(f"     Data: {message}")
            except:
                print(f"[{received_count}] From {addr[0]}:{addr[1]}")
                print(f"     Raw: {data[:100]}...")
            
        except socket.timeout:
            continue
        except Exception as e:
            print(f"Error receiving: {e}")
            break
    
    sock.close()
    
    print(f"\n{'='*60}")
    print(f"Received {received_count} messages in 60 seconds")
    print(f"{'='*60}")
    
    if received_count == 0:
        print("\n✗ NO MESSAGES RECEIVED")
        print("\nPossible issues:")
        print("  1. Firewall blocking UDP 5354")
        print("  2. Network filtering broadcast traffic")
        print("  3. Sender not running or on different network")
        print("  4. Router blocking broadcasts (AP isolation, etc)")
    else:
        print("\n✓ SUCCESS - Broadcasts are working!")

def test_multicast_send():
    """Test sending UDP multicast (alternative to broadcast)"""
    print("=" * 60)
    print("TESTING UDP MULTICAST SENDER")
    print("=" * 60)
    
    MULTICAST_GROUP = '224.0.0.251'  # mDNS group
    MULTICAST_PORT = 5354
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    
    # Get local IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = socket.gethostbyname(socket.gethostname())
    
    print(f"Local IP: {local_ip}")
    print(f"Multicast Group: {MULTICAST_GROUP}")
    print(f"Port: {MULTICAST_PORT}")
    print("\nSending 10 test messages (1 per second)...\n")
    
    for i in range(10):
        message = {
            'test': 'exostream-multicast',
            'number': i + 1,
            'from': local_ip,
            'timestamp': time.time()
        }
        
        data = json.dumps(message).encode('utf-8')
        
        try:
            sock.sendto(data, (MULTICAST_GROUP, MULTICAST_PORT))
            print(f"[{i+1}/10] Sent {len(data)} bytes to multicast")
        except Exception as e:
            print(f"[{i+1}/10] ERROR: {e}")
        
        time.sleep(1)
    
    sock.close()
    print("\n✓ Done sending")

def test_multicast_receive():
    """Test receiving UDP multicast"""
    print("=" * 60)
    print("TESTING UDP MULTICAST RECEIVER")
    print("=" * 60)
    
    MULTICAST_GROUP = '224.0.0.251'
    MULTICAST_PORT = 5354
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except:
        pass
    
    sock.bind(('', MULTICAST_PORT))
    
    # Join multicast group
    import struct
    mreq = struct.pack('4sl', socket.inet_aton(MULTICAST_GROUP), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    
    print(f"✓ Joined multicast group {MULTICAST_GROUP}")
    print(f"✓ Listening on port {MULTICAST_PORT}")
    
    sock.settimeout(1.0)
    
    print("\nWaiting for multicast (60 seconds)...\n")
    
    start_time = time.time()
    received_count = 0
    
    while time.time() - start_time < 60:
        try:
            data, addr = sock.recvfrom(4096)
            received_count += 1
            
            try:
                message = json.loads(data.decode('utf-8'))
                print(f"[{received_count}] From {addr[0]}:{addr[1]}")
                print(f"     Data: {message}")
            except:
                print(f"[{received_count}] From {addr[0]}:{addr[1]}")
        except socket.timeout:
            continue
        except Exception as e:
            print(f"Error: {e}")
            break
    
    sock.close()
    
    print(f"\n{'='*60}")
    print(f"Received {received_count} messages")
    print(f"{'='*60}")
    
    if received_count > 0:
        print("\n✓ SUCCESS - Multicast is working!")
    else:
        print("\n✗ NO MESSAGES RECEIVED")

if __name__ == "__main__":
    print("\n🔧 Exostream UDP Debug Tool\n")
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == "send":
            test_send()
        elif cmd == "receive":
            test_receive()
        elif cmd == "multicast-send":
            test_multicast_send()
        elif cmd == "multicast-receive":
            test_multicast_receive()
        else:
            print(f"Unknown command: {cmd}")
            print("\nUsage:")
            print("  python3 debug_broadcast.py send")
            print("  python3 debug_broadcast.py receive")
            print("  python3 debug_broadcast.py multicast-send")
            print("  python3 debug_broadcast.py multicast-receive")
    else:
        print("Choose a test:")
        print("  1. Send broadcast")
        print("  2. Receive broadcast")
        print("  3. Send multicast")
        print("  4. Receive multicast")
        print()
        choice = input("Enter choice (1/2/3/4): ").strip()
        
        if choice == "1":
            test_send()
        elif choice == "2":
            test_receive()
        elif choice == "3":
            test_multicast_send()
        elif choice == "4":
            test_multicast_receive()
        else:
            print("Invalid choice")

