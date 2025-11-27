#!/usr/bin/env python3
"""
Quick verification script for Phase 2

This script verifies that all Phase 2 components work correctly.
"""

import sys
import time
import threading
from pathlib import Path

# Verification checks
checks_passed = 0
checks_total = 0

def check(name, func):
    """Run a check and track results"""
    global checks_passed, checks_total
    checks_total += 1
    
    try:
        func()
        print(f"✓ {name}")
        checks_passed += 1
        return True
    except Exception as e:
        print(f"✗ {name}: {e}")
        return False


def verify_imports():
    """Verify all modules can be imported"""
    print("\n1. Verifying Imports...")
    print("-" * 50)
    
    check("Import StateManager", lambda: __import__('exostream.daemon.state_manager'))
    check("Import StreamingService", lambda: __import__('exostream.daemon.service'))
    check("Import ExostreamDaemon", lambda: __import__('exostream.daemon.main'))
    check("Import IPCClient", lambda: __import__('exostream.cli.ipc_client'))
    check("Import Protocol", lambda: __import__('exostream.common.protocol'))


def verify_state_manager():
    """Verify StateManager works"""
    print("\n2. Verifying StateManager...")
    print("-" * 50)
    
    import tempfile
    from exostream.daemon.state_manager import StateManager
    from exostream.common.config import StreamConfig, VideoConfig, NDIConfig
    
    temp_dir = Path(tempfile.mkdtemp())
    
    def test_creation():
        manager = StateManager(temp_dir)
        assert manager is not None
    
    def test_daemon_started():
        manager = StateManager(temp_dir)
        manager.set_daemon_started(12345)
        info = manager.get_daemon_info()
        assert info['pid'] == 12345
    
    def test_streaming():
        manager = StateManager(temp_dir)
        config = StreamConfig(
            video=VideoConfig(width=1920, height=1080, fps=30),
            ndi=NDIConfig(stream_name="Test"),
            device="/dev/video0"
        )
        manager.set_streaming_active(config, 54321)
        info = manager.get_streaming_info()
        assert info['active'] == True
        assert info['stream_name'] == "Test"
    
    def test_persistence():
        manager1 = StateManager(temp_dir)
        manager1.set_daemon_started(99999)
        manager2 = StateManager(temp_dir)
        info = manager2.get_daemon_info()
        assert info['pid'] == 99999
    
    check("Create StateManager", test_creation)
    check("Set daemon started", test_daemon_started)
    check("Set streaming active", test_streaming)
    check("State persistence", test_persistence)
    
    # Cleanup
    for file in temp_dir.glob("*"):
        file.unlink()
    temp_dir.rmdir()


def verify_streaming_service():
    """Verify StreamingService works"""
    print("\n3. Verifying StreamingService...")
    print("-" * 50)
    
    import tempfile
    from exostream.daemon.service import StreamingService, StreamState
    from exostream.daemon.state_manager import StateManager
    
    temp_dir = Path(tempfile.mkdtemp())
    
    def test_creation():
        manager = StateManager(temp_dir)
        service = StreamingService(manager)
        assert service is not None
        assert service.state == StreamState.STOPPED
    
    def test_list_devices():
        manager = StateManager(temp_dir)
        service = StreamingService(manager)
        devices = service.list_devices()
        assert isinstance(devices, list)
    
    def test_status():
        manager = StateManager(temp_dir)
        service = StreamingService(manager)
        status = service.get_status()
        assert 'streaming' in status
        assert status['streaming'] == False
    
    def test_health_check():
        manager = StateManager(temp_dir)
        service = StreamingService(manager)
        health = service.health_check()
        assert 'healthy' in health
        assert 'state' in health
    
    check("Create StreamingService", test_creation)
    check("List devices", test_list_devices)
    check("Get status", test_status)
    check("Health check", test_health_check)
    
    # Cleanup
    for file in temp_dir.glob("*"):
        file.unlink()
    temp_dir.rmdir()


def verify_daemon():
    """Verify daemon can start"""
    print("\n4. Verifying Daemon...")
    print("-" * 50)
    
    import tempfile
    from exostream.daemon.main import ExostreamDaemon
    from exostream.cli.ipc_client import IPCClientManager
    
    temp_dir = Path(tempfile.mkdtemp())
    socket_path = str(temp_dir / "test.sock")
    
    def test_creation():
        daemon = ExostreamDaemon(socket_path, temp_dir)
        assert daemon is not None
    
    def test_start_stop():
        daemon = ExostreamDaemon(socket_path, temp_dir)
        
        # Start in thread
        daemon_thread = threading.Thread(target=daemon.start, daemon=True)
        daemon_thread.start()
        time.sleep(0.5)
        
        try:
            assert daemon.is_running()
        finally:
            daemon.stop()
            daemon_thread.join(timeout=2.0)
    
    def test_rpc():
        daemon = ExostreamDaemon(socket_path, temp_dir)
        daemon_thread = threading.Thread(target=daemon.start, daemon=True)
        daemon_thread.start()
        time.sleep(0.5)
        
        try:
            client = IPCClientManager(socket_path)
            result = client.ping()
            assert result == True
        finally:
            daemon.stop()
            daemon_thread.join(timeout=2.0)
    
    check("Create daemon", test_creation)
    check("Start/stop daemon", test_start_stop)
    check("RPC communication", test_rpc)
    
    # Cleanup
    for file in temp_dir.glob("*"):
        file.unlink()
    temp_dir.rmdir()


def verify_tests():
    """Verify tests pass"""
    print("\n5. Verifying Tests...")
    print("-" * 50)
    
    import subprocess
    
    def test_ipc():
        result = subprocess.run(
            ['python3', '-m', 'unittest', 'tests.test_ipc', '-q'],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Tests failed: {result.stderr}"
    
    def test_daemon():
        result = subprocess.run(
            ['python3', '-m', 'unittest', 'tests.test_daemon', '-q'],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Tests failed: {result.stderr}"
    
    check("IPC tests (14 tests)", test_ipc)
    check("Daemon tests (19 tests)", test_daemon)


def main():
    print("=" * 50)
    print("PHASE 2 VERIFICATION")
    print("=" * 50)
    
    # Run all verifications
    verify_imports()
    verify_state_manager()
    verify_streaming_service()
    verify_daemon()
    verify_tests()
    
    # Summary
    print("\n" + "=" * 50)
    print("RESULTS")
    print("=" * 50)
    print(f"Checks passed: {checks_passed}/{checks_total}")
    
    if checks_passed == checks_total:
        print("\n✓ ALL CHECKS PASSED!")
        print("\nPhase 2 is complete and working correctly! 🎉")
        return 0
    else:
        print(f"\n✗ {checks_total - checks_passed} checks failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())

