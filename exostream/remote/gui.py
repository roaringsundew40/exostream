#!/usr/bin/env python3
"""
Exostream Remote Control GUI

A graphical interface for controlling Exostream cameras remotely.
Built with tkinter for cross-platform compatibility.
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import queue
from datetime import datetime
from typing import Optional, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from exostream.cli.network_client import (
    NetworkClientManager,
    NetworkConnectionError,
    NetworkTimeoutError,
    NetworkRPCError
)


class ExostreamGUI:
    """Main GUI application for Exostream remote control"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Exostream Remote Control")
        self.root.geometry("900x700")
        
        # Client and state
        self.client: Optional[NetworkClientManager] = None
        self.connected = False
        self.host = tk.StringVar(value="localhost")
        self.port = tk.StringVar(value="9023")
        
        # Status refresh
        self.auto_refresh = tk.BooleanVar(value=True)
        self.refresh_interval = 2000  # ms
        self.refresh_job = None
        
        # Message queue for thread-safe UI updates
        self.message_queue = queue.Queue()
        
        # Build UI
        self._create_widgets()
        self._setup_styles()
        
        # Start message processing
        self._process_messages()
        
    def _setup_styles(self):
        """Setup custom styles for widgets"""
        style = ttk.Style()
        style.configure('Connected.TLabel', foreground='green', font=('Arial', 10, 'bold'))
        style.configure('Disconnected.TLabel', foreground='red', font=('Arial', 10, 'bold'))
        style.configure('Streaming.TLabel', foreground='green', font=('Arial', 10, 'bold'))
        style.configure('NotStreaming.TLabel', foreground='orange', font=('Arial', 10, 'bold'))
        
    def _create_widgets(self):
        """Create all GUI widgets"""
        
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)  # Make notebook expandable
        
        # Connection Frame
        self._create_connection_frame(main_frame)
        
        # Status Frame
        self._create_status_frame(main_frame)
        
        # Notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
        # Create tabs
        self._create_settings_tab()
        self._create_devices_tab()
        self._create_log_tab()
        
    def _create_connection_frame(self, parent):
        """Create connection controls"""
        frame = ttk.LabelFrame(parent, text="Connection", padding="10")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        frame.columnconfigure(1, weight=1)
        
        # Host
        ttk.Label(frame, text="Host:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        ttk.Entry(frame, textvariable=self.host, width=20).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # Port
        ttk.Label(frame, text="Port:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        ttk.Entry(frame, textvariable=self.port, width=8).grid(row=0, column=3, sticky=tk.W, padx=(0, 10))
        
        # Connect button
        self.connect_btn = ttk.Button(frame, text="Connect", command=self._connect)
        self.connect_btn.grid(row=0, column=4, padx=(0, 5))
        
        # Disconnect button
        self.disconnect_btn = ttk.Button(frame, text="Disconnect", command=self._disconnect, state=tk.DISABLED)
        self.disconnect_btn.grid(row=0, column=5)
        
        # Connection status
        self.conn_status_label = ttk.Label(frame, text="● Not Connected", style='Disconnected.TLabel')
        self.conn_status_label.grid(row=0, column=6, padx=(20, 0))
        
    def _create_status_frame(self, parent):
        """Create status display"""
        frame = ttk.LabelFrame(parent, text="Status", padding="10")
        frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=1)
        
        # Daemon status
        ttk.Label(frame, text="Daemon:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.daemon_status = ttk.Label(frame, text="Unknown")
        self.daemon_status.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        # Stream status
        ttk.Label(frame, text="Stream:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.stream_status = ttk.Label(frame, text="Unknown")
        self.stream_status.grid(row=0, column=3, sticky=tk.W, padx=(0, 20))
        
        # Auto-refresh checkbox
        ttk.Checkbutton(frame, text="Auto-refresh", variable=self.auto_refresh, 
                       command=self._toggle_auto_refresh).grid(row=0, column=4, padx=(10, 0))
        
        # Refresh button
        ttk.Button(frame, text="Refresh Now", command=self._refresh_status).grid(row=0, column=5, padx=(5, 0))
        
    def _create_settings_tab(self):
        """Create settings control tab"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="Settings & Control")
        
        # Current settings display
        settings_frame = ttk.LabelFrame(frame, text="Current Settings", padding="10")
        settings_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))
        settings_frame.columnconfigure(1, weight=1)
        
        self.current_device = ttk.Label(settings_frame, text="Not connected")
        self.current_resolution = ttk.Label(settings_frame, text="Not connected")
        self.current_fps = ttk.Label(settings_frame, text="Not connected")
        self.current_streaming = ttk.Label(settings_frame, text="Unknown")
        
        ttk.Label(settings_frame, text="Device:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.current_device.grid(row=0, column=1, sticky=tk.W)
        
        ttk.Label(settings_frame, text="Resolution:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        self.current_resolution.grid(row=1, column=1, sticky=tk.W)
        
        ttk.Label(settings_frame, text="FPS:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10))
        self.current_fps.grid(row=2, column=1, sticky=tk.W)
        
        ttk.Label(settings_frame, text="Streaming:").grid(row=3, column=0, sticky=tk.W, padx=(0, 10))
        self.current_streaming.grid(row=3, column=1, sticky=tk.W)
        
        # Update settings
        update_frame = ttk.LabelFrame(frame, text="Update Settings", padding="10")
        update_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))
        update_frame.columnconfigure(1, weight=1)
        
        # Resolution
        ttk.Label(update_frame, text="Resolution:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.new_resolution = ttk.Combobox(update_frame, width=15, 
                                          values=['640x480', '1280x720', '1920x1080', '2560x1440'])
        self.new_resolution.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # FPS
        ttk.Label(update_frame, text="FPS:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        self.new_fps = ttk.Combobox(update_frame, width=15, values=['15', '24', '30', '60'])
        self.new_fps.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Device
        ttk.Label(update_frame, text="Device:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10))
        self.new_device = ttk.Combobox(update_frame, width=15)
        self.new_device.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Stream name
        ttk.Label(update_frame, text="Stream Name:").grid(row=3, column=0, sticky=tk.W, padx=(0, 10))
        self.new_name = ttk.Entry(update_frame, width=15)
        self.new_name.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Auto-restart checkbox
        self.auto_restart = tk.BooleanVar(value=True)
        ttk.Checkbutton(update_frame, text="Auto-restart stream if running", 
                       variable=self.auto_restart).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Update button
        ttk.Button(update_frame, text="Update Settings", command=self._update_settings).grid(
            row=5, column=0, columnspan=2, pady=10)
        
        # Stream control
        control_frame = ttk.LabelFrame(frame, text="Stream Control", padding="10")
        control_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N))
        
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Start Stream", command=self._start_stream, 
                  width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Stop Stream", command=self._stop_stream,
                  width=15).pack(side=tk.LEFT, padx=5)
        
    def _create_devices_tab(self):
        """Create devices list tab"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="Devices")
        
        # Devices list
        ttk.Label(frame, text="Available Devices:").pack(anchor=tk.W, pady=(0, 5))
        
        # Treeview for devices
        columns = ('Status', 'Path', 'Name')
        self.devices_tree = ttk.Treeview(frame, columns=columns, show='headings', height=10)
        
        self.devices_tree.heading('Status', text='Status')
        self.devices_tree.heading('Path', text='Device Path')
        self.devices_tree.heading('Name', text='Device Name')
        
        self.devices_tree.column('Status', width=80)
        self.devices_tree.column('Path', width=120)
        self.devices_tree.column('Name', width=400)
        
        self.devices_tree.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Refresh devices button
        ttk.Button(frame, text="Refresh Devices", command=self._refresh_devices).pack()
        
    def _create_log_tab(self):
        """Create log display tab"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="Log")
        
        # Log display
        self.log_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=20)
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Clear log button
        ttk.Button(frame, text="Clear Log", command=self._clear_log).pack()
        
        # Initial log message
        self._log("Exostream Remote Control initialized")
        self._log("Connect to a daemon to begin")
        
    def _log(self, message: str, level: str = "INFO"):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}\n"
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        
    def _clear_log(self):
        """Clear the log"""
        self.log_text.delete('1.0', tk.END)
        self._log("Log cleared")
        
    def _connect(self):
        """Connect to daemon"""
        host = self.host.get()
        try:
            port = int(self.port.get())
        except ValueError:
            messagebox.showerror("Error", "Port must be a number")
            return
        
        self._log(f"Connecting to {host}:{port}...")
        
        # Disable connect button during connection
        self.connect_btn.config(state=tk.DISABLED)
        
        # Connect in background thread
        def connect_thread():
            try:
                self.client = NetworkClientManager(host, port)
                if self.client.is_connected():
                    self.message_queue.put(('connected', None))
                else:
                    self.message_queue.put(('error', "Connection failed"))
            except Exception as e:
                self.message_queue.put(('error', str(e)))
        
        threading.Thread(target=connect_thread, daemon=True).start()
        
    def _disconnect(self):
        """Disconnect from daemon"""
        self.connected = False
        self.client = None
        
        # Update UI
        self.conn_status_label.config(text="● Not Connected", style='Disconnected.TLabel')
        self.connect_btn.config(state=tk.NORMAL)
        self.disconnect_btn.config(state=tk.DISABLED)
        
        # Stop auto-refresh
        if self.refresh_job:
            self.root.after_cancel(self.refresh_job)
            self.refresh_job = None
        
        self._log("Disconnected")
        
    def _on_connected(self):
        """Handle successful connection"""
        self.connected = True
        self.conn_status_label.config(text="● Connected", style='Connected.TLabel')
        self.connect_btn.config(state=tk.DISABLED)
        self.disconnect_btn.config(state=tk.NORMAL)
        
        self._log(f"Connected to {self.host.get()}:{self.port.get()}")
        
        # Refresh status
        self._refresh_status()
        self._refresh_devices()
        
        # Start auto-refresh if enabled
        if self.auto_refresh.get():
            self._schedule_refresh()
        
    def _toggle_auto_refresh(self):
        """Toggle auto-refresh"""
        if self.auto_refresh.get() and self.connected:
            self._schedule_refresh()
        elif self.refresh_job:
            self.root.after_cancel(self.refresh_job)
            self.refresh_job = None
            
    def _schedule_refresh(self):
        """Schedule next status refresh"""
        if self.refresh_job:
            self.root.after_cancel(self.refresh_job)
        self.refresh_job = self.root.after(self.refresh_interval, self._auto_refresh_status)
        
    def _auto_refresh_status(self):
        """Auto-refresh status (called by timer)"""
        if self.connected and self.auto_refresh.get():
            self._refresh_status_background()
            self._schedule_refresh()
            
    def _refresh_status(self):
        """Refresh status (manual)"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Connect to a daemon first")
            return
        
        self._refresh_status_background()
        
    def _refresh_status_background(self):
        """Refresh status in background thread"""
        def refresh_thread():
            try:
                # Get daemon status
                daemon_status = self.client.get_daemon_status()
                
                # Get settings
                settings = self.client.get_settings()
                
                self.message_queue.put(('status_update', {
                    'daemon': daemon_status,
                    'settings': settings
                }))
                
            except Exception as e:
                self.message_queue.put(('status_error', str(e)))
        
        threading.Thread(target=refresh_thread, daemon=True).start()
        
    def _update_status_display(self, data: Dict[str, Any]):
        """Update status display with new data"""
        daemon = data.get('daemon', {})
        settings = data.get('settings', {})
        
        # Update daemon status
        if daemon.get('running'):
            uptime = daemon.get('uptime_seconds', 0)
            if uptime < 60:
                uptime_str = f"{uptime:.0f}s"
            elif uptime < 3600:
                uptime_str = f"{uptime/60:.0f}m"
            else:
                uptime_str = f"{uptime/3600:.1f}h"
            self.daemon_status.config(text=f"Running (uptime: {uptime_str})")
        else:
            self.daemon_status.config(text="Not running")
        
        # Update stream status
        if settings.get('streaming'):
            self.stream_status.config(text="● Streaming", style='Streaming.TLabel')
        else:
            self.stream_status.config(text="● Not streaming", style='NotStreaming.TLabel')
        
        # Update current settings
        self.current_device.config(text=settings.get('device', 'Unknown'))
        self.current_resolution.config(text=settings.get('resolution', 'Unknown'))
        self.current_fps.config(text=str(settings.get('fps', 'Unknown')))
        
        if settings.get('streaming'):
            stream_name = settings.get('name', 'Unknown')
            self.current_streaming.config(text=f"Yes - {stream_name}")
        else:
            self.current_streaming.config(text="No")
        
    def _refresh_devices(self):
        """Refresh devices list"""
        if not self.connected:
            return
        
        def refresh_thread():
            try:
                devices = self.client.list_devices()
                available_options = self.client.get_available_options()
                self.message_queue.put(('devices_update', {
                    'devices': devices,
                    'options': available_options
                }))
            except Exception as e:
                self.message_queue.put(('devices_error', str(e)))
        
        threading.Thread(target=refresh_thread, daemon=True).start()
        
    def _update_devices_display(self, data: Dict[str, Any]):
        """Update devices display"""
        devices = data.get('devices', [])
        options = data.get('options', {})
        
        # Clear existing items
        for item in self.devices_tree.get_children():
            self.devices_tree.delete(item)
        
        # Add devices
        for device in devices:
            status = "IN USE" if device.get('in_use') else "FREE"
            self.devices_tree.insert('', tk.END, values=(
                status,
                device.get('path', ''),
                device.get('name', '')
            ))
        
        # Update device combobox
        device_paths = [d.get('path') for d in devices]
        self.new_device.config(values=device_paths)
        
        # Update resolution combobox
        resolutions = options.get('resolutions', [])
        if resolutions:
            self.new_resolution.config(values=resolutions)
        
        # Update FPS combobox
        fps_options = options.get('fps_options', [])
        if fps_options:
            self.new_fps.config(values=[str(f) for f in fps_options])
        
    def _update_settings(self):
        """Update camera settings"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Connect to a daemon first")
            return
        
        # Get values
        resolution = self.new_resolution.get()
        fps_str = self.new_fps.get()
        device = self.new_device.get()
        name = self.new_name.get()
        
        # Validate
        params = {}
        if resolution:
            params['resolution'] = resolution
        if fps_str:
            try:
                params['fps'] = int(fps_str)
            except ValueError:
                messagebox.showerror("Error", "FPS must be a number")
                return
        if device:
            params['device'] = device
        if name:
            params['name'] = name
        
        if not params:
            messagebox.showwarning("No Changes", "Please select settings to update")
            return
        
        params['restart_if_streaming'] = self.auto_restart.get()
        
        self._log(f"Updating settings: {params}")
        
        # Update in background
        def update_thread():
            try:
                result = self.client.update_settings(**params)
                self.message_queue.put(('settings_updated', result))
            except Exception as e:
                self.message_queue.put(('update_error', str(e)))
        
        threading.Thread(target=update_thread, daemon=True).start()
        
    def _start_stream(self):
        """Start streaming"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Connect to a daemon first")
            return
        
        # Get values
        device = self.new_device.get() or self.current_device.cget('text')
        name = self.new_name.get() or "Exostream"
        resolution = self.new_resolution.get() or self.current_resolution.cget('text')
        fps_str = self.new_fps.get() or self.current_fps.cget('text')
        
        try:
            fps = int(fps_str)
        except ValueError:
            messagebox.showerror("Error", "Invalid FPS value")
            return
        
        self._log(f"Starting stream: {name} ({resolution} @ {fps}fps)")
        
        def start_thread():
            try:
                result = self.client.start_stream(
                    device=device,
                    name=name,
                    resolution=resolution,
                    fps=fps
                )
                self.message_queue.put(('stream_started', result))
            except Exception as e:
                self.message_queue.put(('start_error', str(e)))
        
        threading.Thread(target=start_thread, daemon=True).start()
        
    def _stop_stream(self):
        """Stop streaming"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Connect to a daemon first")
            return
        
        if messagebox.askyesno("Confirm", "Stop the current stream?"):
            self._log("Stopping stream...")
            
            def stop_thread():
                try:
                    result = self.client.stop_stream()
                    self.message_queue.put(('stream_stopped', result))
                except Exception as e:
                    self.message_queue.put(('stop_error', str(e)))
            
            threading.Thread(target=stop_thread, daemon=True).start()
        
    def _process_messages(self):
        """Process messages from background threads"""
        try:
            while True:
                msg_type, msg_data = self.message_queue.get_nowait()
                
                if msg_type == 'connected':
                    self._on_connected()
                elif msg_type == 'error':
                    self.connect_btn.config(state=tk.NORMAL)
                    messagebox.showerror("Connection Error", f"Failed to connect: {msg_data}")
                    self._log(f"Connection failed: {msg_data}", "ERROR")
                elif msg_type == 'status_update':
                    self._update_status_display(msg_data)
                elif msg_type == 'status_error':
                    self._log(f"Status error: {msg_data}", "ERROR")
                elif msg_type == 'devices_update':
                    self._update_devices_display(msg_data)
                elif msg_type == 'devices_error':
                    self._log(f"Devices error: {msg_data}", "ERROR")
                elif msg_type == 'settings_updated':
                    self._log("Settings updated successfully")
                    messagebox.showinfo("Success", "Settings updated successfully")
                    self._refresh_status()
                elif msg_type == 'update_error':
                    self._log(f"Update error: {msg_data}", "ERROR")
                    messagebox.showerror("Error", f"Failed to update settings: {msg_data}")
                elif msg_type == 'stream_started':
                    self._log("Stream started successfully")
                    messagebox.showinfo("Success", "Stream started")
                    self._refresh_status()
                elif msg_type == 'start_error':
                    self._log(f"Start error: {msg_data}", "ERROR")
                    messagebox.showerror("Error", f"Failed to start stream: {msg_data}")
                elif msg_type == 'stream_stopped':
                    self._log("Stream stopped successfully")
                    messagebox.showinfo("Success", "Stream stopped")
                    self._refresh_status()
                elif msg_type == 'stop_error':
                    self._log(f"Stop error: {msg_data}", "ERROR")
                    messagebox.showerror("Error", f"Failed to stop stream: {msg_data}")
                    
        except queue.Empty:
            pass
        
        # Schedule next check
        self.root.after(100, self._process_messages)


def main():
    """Main entry point"""
    root = tk.Tk()
    app = ExostreamGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

