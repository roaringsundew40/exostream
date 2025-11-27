"""Tests for CLI commands"""

import unittest
import tempfile
import threading
import time
from pathlib import Path
from click.testing import CliRunner

from exostream.cli.main import cli
from exostream.daemon.main import ExostreamDaemon


class TestCLI(unittest.TestCase):
    """Test CLI commands"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.socket_path = str(self.temp_dir / "test.sock")
        self.runner = CliRunner()
        self.daemon = None
        self.daemon_thread = None
    
    def tearDown(self):
        """Clean up"""
        # Stop daemon if running
        if self.daemon and self.daemon.is_running():
            self.daemon.stop()
        
        if self.daemon_thread and self.daemon_thread.is_alive():
            self.daemon_thread.join(timeout=2.0)
        
        # Clean up files
        for file in self.temp_dir.glob("*"):
            try:
                file.unlink()
            except:
                pass
        try:
            self.temp_dir.rmdir()
        except:
            pass
    
    def start_daemon(self):
        """Start daemon in background thread"""
        self.daemon = ExostreamDaemon(self.socket_path, self.temp_dir)
        self.daemon_thread = threading.Thread(target=self.daemon.start, daemon=True)
        self.daemon_thread.start()
        time.sleep(0.5)  # Give daemon time to start
    
    def test_help(self):
        """Test help command"""
        result = self.runner.invoke(cli, ['--help'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Exostream', result.output)
        self.assertIn('start', result.output)
        self.assertIn('stop', result.output)
        self.assertIn('status', result.output)
        self.assertIn('devices', result.output)
        self.assertIn('daemon', result.output)
    
    def test_version(self):
        """Test version command"""
        result = self.runner.invoke(cli, ['--version'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('0.3.0', result.output)
    
    def test_daemon_status_not_running(self):
        """Test daemon status when not running"""
        result = self.runner.invoke(cli, [
            'daemon', 'status',
            '--socket', self.socket_path
        ])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('not running', result.output.lower())
    
    def test_daemon_status_running(self):
        """Test daemon status when running"""
        self.start_daemon()
        
        result = self.runner.invoke(cli, [
            'daemon', 'status',
            '--socket', self.socket_path
        ])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('running', result.output.lower())
        self.assertIn('0.3.0', result.output)
    
    def test_daemon_ping(self):
        """Test daemon ping"""
        self.start_daemon()
        
        result = self.runner.invoke(cli, [
            'daemon', 'ping',
            '--socket', self.socket_path
        ])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('responding', result.output.lower())
    
    def test_devices_command(self):
        """Test devices listing"""
        self.start_daemon()
        
        result = self.runner.invoke(cli, [
            '--socket', self.socket_path,
            'devices'
        ], obj={})
        self.assertEqual(result.exit_code, 0)
        # Output should contain devices info or "No video devices"
        self.assertTrue(
            'devices' in result.output.lower() or
            'no video' in result.output.lower()
        )
    
    def test_status_command(self):
        """Test status command"""
        self.start_daemon()
        
        result = self.runner.invoke(cli, [
            '--socket', self.socket_path,
            'status'
        ], obj={})
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Daemon', result.output)
        self.assertIn('Stream', result.output)
    
    def test_start_without_daemon(self):
        """Test start command when daemon not running"""
        result = self.runner.invoke(cli, [
            '--socket', self.socket_path,
            'start',
            '--name', 'TestCamera'
        ], obj={})
        self.assertEqual(result.exit_code, 1)
        self.assertIn('not running', result.output.lower())
    
    def test_stop_without_daemon(self):
        """Test stop command when daemon not running"""
        result = self.runner.invoke(cli, [
            '--socket', self.socket_path,
            'stop'
        ], obj={})
        self.assertEqual(result.exit_code, 1)
        self.assertIn('not running', result.output.lower())


if __name__ == '__main__':
    unittest.main()

