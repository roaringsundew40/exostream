"""Integration tests for daemon components"""

import unittest
import tempfile
import os
import time
import threading
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from exostream.daemon.state_manager import StateManager
from exostream.daemon.service import (
    StreamingService,
    StreamState,
    StreamAlreadyRunningError,
    StreamNotRunningError,
    DeviceNotFoundError
)
from exostream.daemon.main import ExostreamDaemon
from exostream.cli.ipc_client import IPCClientManager
from exostream.common.config import StreamConfig, VideoConfig, NDIConfig


class TestStateManager(unittest.TestCase):
    """Test StateManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.state_manager = StateManager(self.temp_dir)
    
    def tearDown(self):
        """Clean up"""
        # Remove state file
        if self.state_manager.state_file.exists():
            self.state_manager.state_file.unlink()
        self.temp_dir.rmdir()
    
    def test_default_state(self):
        """Test default state"""
        state = self.state_manager.get_full_state()
        
        self.assertEqual(state["version"], "0.3.0")
        self.assertFalse(state["streaming"]["active"])
        self.assertEqual(state["last_config"]["device"], "/dev/video0")
    
    def test_set_daemon_started(self):
        """Test setting daemon started"""
        self.state_manager.set_daemon_started(12345)
        
        daemon_info = self.state_manager.get_daemon_info()
        self.assertEqual(daemon_info["pid"], 12345)
        self.assertIsNotNone(daemon_info["started_at"])
    
    def test_set_streaming_active(self):
        """Test setting streaming active"""
        config = StreamConfig(
            video=VideoConfig(width=1920, height=1080, fps=30),
            ndi=NDIConfig(stream_name="Test"),
            device="/dev/video0"
        )
        
        self.state_manager.set_streaming_active(config, 54321)
        
        streaming_info = self.state_manager.get_streaming_info()
        self.assertTrue(streaming_info["active"])
        self.assertEqual(streaming_info["stream_name"], "Test")
        self.assertEqual(streaming_info["ffmpeg_pid"], 54321)
    
    def test_set_streaming_inactive(self):
        """Test setting streaming inactive"""
        # First set active
        config = StreamConfig(
            video=VideoConfig(width=1920, height=1080, fps=30),
            ndi=NDIConfig(stream_name="Test"),
            device="/dev/video0"
        )
        self.state_manager.set_streaming_active(config, 54321)
        
        # Then set inactive
        self.state_manager.set_streaming_inactive()
        
        streaming_info = self.state_manager.get_streaming_info()
        self.assertFalse(streaming_info["active"])
        self.assertIsNone(streaming_info["stream_name"])
    
    def test_persistence(self):
        """Test state persists across instances"""
        # Set some state
        self.state_manager.set_daemon_started(12345)
        
        # Create new instance with same directory
        new_manager = StateManager(self.temp_dir)
        
        # Check state was loaded
        daemon_info = new_manager.get_daemon_info()
        self.assertEqual(daemon_info["pid"], 12345)
    
    def test_uptime_calculation(self):
        """Test uptime calculation"""
        self.state_manager.set_daemon_started(12345)
        
        # Small delay
        time.sleep(0.1)
        
        uptime = self.state_manager.get_uptime_seconds()
        self.assertIsNotNone(uptime)
        self.assertGreater(uptime, 0)


class TestStreamingService(unittest.TestCase):
    """Test StreamingService"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.state_manager = StateManager(self.temp_dir)
        self.service = StreamingService(self.state_manager)
    
    def tearDown(self):
        """Clean up"""
        try:
            if self.service.is_streaming():
                self.service.stop_streaming()
        except:
            pass
        
        if self.state_manager.state_file.exists():
            self.state_manager.state_file.unlink()
        self.temp_dir.rmdir()
    
    def test_initial_state(self):
        """Test initial state"""
        self.assertEqual(self.service.state, StreamState.STOPPED)
        self.assertFalse(self.service.is_streaming())
    
    def test_list_devices(self):
        """Test device listing"""
        devices = self.service.list_devices()
        
        # Should be a list (might be empty on test system)
        self.assertIsInstance(devices, list)
        
        # If devices exist, check structure
        if devices:
            device = devices[0]
            self.assertIn("path", device)
            self.assertIn("name", device)
            self.assertIn("index", device)
    
    def test_get_status_not_streaming(self):
        """Test status when not streaming"""
        status = self.service.get_status()
        
        self.assertFalse(status["streaming"])
        self.assertEqual(status["state"], StreamState.STOPPED.value)
    
    @patch('exostream.sender.webcam.WebcamManager.detect_devices')
    @patch('exostream.sender.ffmpeg_encoder.FFmpegEncoder')
    def test_start_streaming_no_devices(self, mock_encoder, mock_detect):
        """Test starting streaming when no devices available"""
        mock_detect.return_value = []
        
        with self.assertRaises(DeviceNotFoundError):
            self.service.start_streaming(
                device="/dev/video0",
                name="Test"
            )
    
    @patch('exostream.sender.webcam.WebcamManager.detect_devices')
    @patch('exostream.sender.webcam.WebcamManager.get_device_by_path')
    def test_start_streaming_device_not_found(self, mock_get_device, mock_detect):
        """Test starting streaming with non-existent device"""
        from exostream.sender.webcam import WebcamDevice
        
        mock_detect.return_value = [
            WebcamDevice(path="/dev/video1", name="Camera", index=1)
        ]
        mock_get_device.return_value = None
        
        with self.assertRaises(DeviceNotFoundError):
            self.service.start_streaming(
                device="/dev/video0",
                name="Test"
            )
    
    def test_stop_streaming_when_not_running(self):
        """Test stopping streaming when not running"""
        with self.assertRaises(StreamNotRunningError):
            self.service.stop_streaming()
    
    def test_health_check(self):
        """Test health check"""
        health = self.service.health_check()
        
        self.assertIn("healthy", health)
        self.assertIn("state", health)
        self.assertIn("streaming", health)
        self.assertIn("issues", health)


class TestDaemonIntegration(unittest.TestCase):
    """Integration tests for full daemon"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.socket_path = str(self.temp_dir / "test.sock")
    
    def tearDown(self):
        """Clean up"""
        # Remove socket if exists
        socket_file = Path(self.socket_path)
        if socket_file.exists():
            socket_file.unlink()
        
        # Remove state files
        for file in self.temp_dir.glob("*"):
            file.unlink()
        self.temp_dir.rmdir()
    
    def test_daemon_initialization(self):
        """Test daemon can be initialized"""
        daemon = ExostreamDaemon(
            socket_path=self.socket_path,
            state_dir=self.temp_dir
        )
        
        self.assertIsNotNone(daemon.streaming_service)
        self.assertIsNotNone(daemon.state_manager)
        self.assertIsNotNone(daemon.ipc_server)
    
    def test_daemon_start_stop(self):
        """Test daemon can start and stop"""
        daemon = ExostreamDaemon(
            socket_path=self.socket_path,
            state_dir=self.temp_dir
        )
        
        # Start daemon in thread
        daemon_thread = threading.Thread(target=daemon.start, daemon=True)
        daemon_thread.start()
        
        # Give it time to start
        time.sleep(0.5)
        
        try:
            # Check it's running
            self.assertTrue(daemon.is_running())
            self.assertTrue(daemon.ipc_server.running)
            
            # Stop daemon
            daemon.stop()
            
            # Wait for thread
            daemon_thread.join(timeout=2.0)
            
            # Check it stopped
            self.assertFalse(daemon.is_running())
            
        finally:
            if daemon.is_running():
                daemon.stop()
    
    def test_daemon_rpc_ping(self):
        """Test daemon responds to ping"""
        daemon = ExostreamDaemon(
            socket_path=self.socket_path,
            state_dir=self.temp_dir
        )
        
        # Start daemon
        daemon_thread = threading.Thread(target=daemon.start, daemon=True)
        daemon_thread.start()
        time.sleep(0.5)
        
        try:
            # Create client and ping
            client = IPCClientManager(self.socket_path)
            result = client.ping()
            
            self.assertTrue(result)
            
        finally:
            daemon.stop()
            daemon_thread.join(timeout=2.0)
    
    def test_daemon_rpc_status(self):
        """Test daemon status RPC"""
        daemon = ExostreamDaemon(
            socket_path=self.socket_path,
            state_dir=self.temp_dir
        )
        
        daemon_thread = threading.Thread(target=daemon.start, daemon=True)
        daemon_thread.start()
        time.sleep(0.5)
        
        try:
            client = IPCClientManager(self.socket_path)
            status = client.get_daemon_status()
            
            self.assertTrue(status["running"])
            self.assertEqual(status["version"], "0.3.0")
            self.assertGreaterEqual(status["uptime_seconds"], 0)
            self.assertIsInstance(status["pid"], int)
            
        finally:
            daemon.stop()
            daemon_thread.join(timeout=2.0)
    
    def test_daemon_rpc_devices_list(self):
        """Test devices list RPC"""
        daemon = ExostreamDaemon(
            socket_path=self.socket_path,
            state_dir=self.temp_dir
        )
        
        daemon_thread = threading.Thread(target=daemon.start, daemon=True)
        daemon_thread.start()
        time.sleep(0.5)
        
        try:
            client = IPCClientManager(self.socket_path)
            devices = client.list_devices()
            
            # Should be a list (might be empty)
            self.assertIsInstance(devices, list)
            
        finally:
            daemon.stop()
            daemon_thread.join(timeout=2.0)
    
    def test_daemon_rpc_stream_status(self):
        """Test stream status RPC"""
        daemon = ExostreamDaemon(
            socket_path=self.socket_path,
            state_dir=self.temp_dir
        )
        
        daemon_thread = threading.Thread(target=daemon.start, daemon=True)
        daemon_thread.start()
        time.sleep(0.5)
        
        try:
            client = IPCClientManager(self.socket_path)
            status = client.get_stream_status()
            
            # Should not be streaming initially
            self.assertFalse(status["streaming"])
            
        finally:
            daemon.stop()
            daemon_thread.join(timeout=2.0)


if __name__ == '__main__':
    unittest.main()

