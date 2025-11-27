"""Unit tests for IPC protocol, server, and client"""

import unittest
import tempfile
import os
import time
import json
from pathlib import Path

from exostream.common.protocol import (
    RPCRequest, RPCResponse, RPCError,
    Methods, StartStreamParams, StreamStatus,
    create_request, create_success_response, create_error_response
)
from exostream.daemon.ipc_server import IPCServer, IPCServerManager
from exostream.cli.ipc_client import IPCClient, IPCClientManager, DaemonNotRunningError


class TestProtocol(unittest.TestCase):
    """Test protocol definitions"""
    
    def test_rpc_request_serialization(self):
        """Test RPCRequest to/from JSON"""
        request = RPCRequest(
            method="stream.start",
            params={"device": "/dev/video0"},
            id=1
        )
        
        # Serialize
        json_str = request.to_json()
        self.assertIn("stream.start", json_str)
        
        # Deserialize
        request2 = RPCRequest.from_json(json_str)
        self.assertEqual(request2.method, "stream.start")
        self.assertEqual(request2.params["device"], "/dev/video0")
        self.assertEqual(request2.id, 1)
    
    def test_rpc_response_success(self):
        """Test success response"""
        response = RPCResponse.success({"status": "ok"}, request_id=1)
        
        self.assertIsNotNone(response.result)
        self.assertIsNone(response.error)
        self.assertEqual(response.id, 1)
        
        # Serialize/deserialize
        json_str = response.to_json()
        response2 = RPCResponse.from_json(json_str)
        self.assertEqual(response2.result["status"], "ok")
    
    def test_rpc_response_error(self):
        """Test error response"""
        response = create_error_response(
            RPCError.METHOD_NOT_FOUND,
            "Method not found",
            request_id=1
        )
        
        self.assertIsNone(response.result)
        self.assertIsNotNone(response.error)
        self.assertEqual(response.error["code"], RPCError.METHOD_NOT_FOUND.value)
        
        # Serialize/deserialize
        json_str = response.to_json()
        response2 = RPCResponse.from_json(json_str)
        self.assertEqual(response2.error["message"], "Method not found")
    
    def test_start_stream_params(self):
        """Test StartStreamParams"""
        params = StartStreamParams(
            device="/dev/video0",
            name="test",
            resolution="1920x1080",
            fps=30
        )
        
        # To dict
        data = params.to_dict()
        self.assertEqual(data["device"], "/dev/video0")
        
        # From dict
        params2 = StartStreamParams.from_dict(data)
        self.assertEqual(params2.device, "/dev/video0")
        self.assertEqual(params2.name, "test")
    
    def test_stream_status(self):
        """Test StreamStatus"""
        status = StreamStatus(
            streaming=True,
            stream_name="test",
            device="/dev/video0",
            uptime_seconds=100.5
        )
        
        # To/from dict
        data = status.to_dict()
        status2 = StreamStatus.from_dict(data)
        self.assertEqual(status2.streaming, True)
        self.assertEqual(status2.uptime_seconds, 100.5)


class TestIPCServerClient(unittest.TestCase):
    """Test IPC server and client communication"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Use temporary socket path
        self.temp_dir = tempfile.mkdtemp()
        self.socket_path = os.path.join(self.temp_dir, "test.sock")
    
    def tearDown(self):
        """Clean up"""
        # Remove temp directory
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)
        os.rmdir(self.temp_dir)
    
    def test_server_start_stop(self):
        """Test server can start and stop"""
        server = IPCServer(self.socket_path)
        
        # Start server
        server.start()
        self.assertTrue(server.running)
        self.assertTrue(os.path.exists(self.socket_path))
        
        # Stop server
        server.stop()
        self.assertFalse(server.running)
        self.assertFalse(os.path.exists(self.socket_path))
    
    def test_client_server_ping(self):
        """Test client can ping server"""
        # Create server with simple handler
        def handler(request: RPCRequest) -> RPCResponse:
            if request.method == "ping":
                return RPCResponse.success({"pong": True}, request.id)
            return create_error_response(
                RPCError.METHOD_NOT_FOUND,
                "Not found",
                request_id=request.id
            )
        
        server = IPCServer(self.socket_path, handler=handler)
        server.start()
        
        try:
            # Create client and call
            client = IPCClient(self.socket_path)
            result = client.call("ping", {})
            
            self.assertEqual(result["pong"], True)
        finally:
            server.stop()
    
    def test_client_daemon_not_running(self):
        """Test client handles daemon not running"""
        client = IPCClient(self.socket_path)
        
        with self.assertRaises(DaemonNotRunningError):
            client.call("ping", {})
    
    def test_server_manager_routing(self):
        """Test server manager method routing"""
        server_mgr = IPCServerManager(self.socket_path)
        
        # Register handlers
        call_count = {'ping': 0, 'echo': 0}
        
        def ping_handler(params):
            call_count['ping'] += 1
            return {"pong": True}
        
        def echo_handler(params):
            call_count['echo'] += 1
            return {"echo": params.get("message", "")}
        
        server_mgr.register_handler("ping", ping_handler)
        server_mgr.register_handler("echo", echo_handler)
        
        server_mgr.start()
        
        try:
            client = IPCClient(self.socket_path)
            
            # Test ping
            result = client.call("ping", {})
            self.assertEqual(result["pong"], True)
            self.assertEqual(call_count['ping'], 1)
            
            # Test echo
            result = client.call("echo", {"message": "hello"})
            self.assertEqual(result["echo"], "hello")
            self.assertEqual(call_count['echo'], 1)
            
            # Test method not found
            from exostream.cli.ipc_client import DaemonRPCError
            with self.assertRaises(DaemonRPCError) as ctx:
                client.call("nonexistent", {})
            self.assertEqual(ctx.exception.code, RPCError.METHOD_NOT_FOUND.value)
            
        finally:
            server_mgr.stop()
    
    def test_client_manager_helpers(self):
        """Test client manager helper methods"""
        # Create server
        server_mgr = IPCServerManager(self.socket_path)
        
        def ping_handler(params):
            return {"pong": True}
        
        def status_handler(params):
            return {
                "running": True,
                "version": "0.3.0",
                "uptime_seconds": 100.0,
                "pid": 12345
            }
        
        server_mgr.register_handler("daemon.ping", ping_handler)
        server_mgr.register_handler("daemon.status", status_handler)
        
        server_mgr.start()
        
        try:
            client_mgr = IPCClientManager(self.socket_path)
            
            # Test is_daemon_running
            self.assertTrue(client_mgr.is_daemon_running())
            
            # Test ping
            self.assertTrue(client_mgr.ping())
            
            # Test get_daemon_status
            status = client_mgr.get_daemon_status()
            self.assertEqual(status["version"], "0.3.0")
            self.assertEqual(status["pid"], 12345)
            
        finally:
            server_mgr.stop()
    
    def test_large_payload(self):
        """Test handling of large payloads"""
        def handler(request: RPCRequest) -> RPCResponse:
            # Echo back the data
            return RPCResponse.success(request.params, request.id)
        
        server = IPCServer(self.socket_path, handler=handler)
        server.start()
        
        try:
            client = IPCClient(self.socket_path)
            
            # Send large payload (10KB of data)
            large_data = {"data": "x" * 10000}
            result = client.call("test", large_data)
            
            self.assertEqual(len(result["data"]), 10000)
        finally:
            server.stop()
    
    def test_concurrent_clients(self):
        """Test multiple concurrent clients"""
        import threading
        
        def handler(request: RPCRequest) -> RPCResponse:
            return RPCResponse.success({"id": request.id}, request.id)
        
        server = IPCServer(self.socket_path, handler=handler)
        server.start()
        
        # Give server time to start accepting connections
        time.sleep(0.1)
        
        try:
            results = []
            errors = []
            
            def client_thread(thread_id):
                try:
                    # Add small delay between client starts to avoid overwhelming server
                    time.sleep(thread_id * 0.01)
                    client = IPCClient(self.socket_path)
                    result = client.call("test", {"thread": thread_id})
                    results.append(result)
                except Exception as e:
                    errors.append(e)
            
            # Start 10 concurrent clients
            threads = []
            for i in range(10):
                t = threading.Thread(target=client_thread, args=(i,))
                threads.append(t)
                t.start()
            
            # Wait for all to complete
            for t in threads:
                t.join()
            
            # Check results
            self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
            self.assertEqual(len(results), 10)
            
        finally:
            server.stop()


class TestIPCErrorHandling(unittest.TestCase):
    """Test IPC error handling"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.socket_path = os.path.join(self.temp_dir, "test.sock")
    
    def tearDown(self):
        """Clean up"""
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)
        os.rmdir(self.temp_dir)
    
    def test_invalid_json(self):
        """Test handling of invalid JSON"""
        server_mgr = IPCServerManager(self.socket_path)
        server_mgr.start()
        
        try:
            # Send invalid JSON directly
            import socket
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(self.socket_path)
            sock.sendall(b"invalid json\n")
            
            response = sock.recv(4096).decode('utf-8')
            sock.close()
            
            # Should get parse error
            resp_obj = json.loads(response)
            self.assertIn('error', resp_obj)
            self.assertEqual(resp_obj['error']['code'], RPCError.PARSE_ERROR.value)
            
        finally:
            server_mgr.stop()
    
    def test_handler_exception(self):
        """Test handling of handler exceptions"""
        def bad_handler(params):
            raise ValueError("Something went wrong")
        
        server_mgr = IPCServerManager(self.socket_path)
        server_mgr.register_handler("bad", bad_handler)
        server_mgr.start()
        
        try:
            client = IPCClient(self.socket_path)
            
            from exostream.cli.ipc_client import DaemonRPCError
            with self.assertRaises(DaemonRPCError) as ctx:
                client.call("bad", {})
            
            self.assertEqual(ctx.exception.code, RPCError.INTERNAL_ERROR.value)
            self.assertIn("Something went wrong", ctx.exception.message)
            
        finally:
            server_mgr.stop()


if __name__ == '__main__':
    unittest.main()

