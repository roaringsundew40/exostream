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
from exostream.common.discovery import ExostreamServiceDiscovery


class ExostreamGUI:
    """Main GUI application for Exostream remote control"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Exostream Remote Control")
        self.root.geometry("600x750")
        
        # Client and state
        self.client: Optional[NetworkClientManager] = None
        self.connected = False
        self.host = tk.StringVar(value="localhost")
        self.port = tk.StringVar(value="9023")
        
        # Service discovery
        self.discovery: Optional[ExostreamServiceDiscovery] = None
        self.discovered_services = {}
        
        # Status refresh
        self.auto_refresh = tk.BooleanVar(value=True)
        self.refresh_interval = 2000  # ms
        self.refresh_job = None
        
        # Message queue for thread-safe UI updates
        self.message_queue = queue.Queue()
        
        # Build UI
        self._create_widgets()
        self._setup_styles()
        
        # Setup cleanup on close
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Start message processing
        self._process_messages()
        
        # Auto-start discovery
        self._start_discovery()
        
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
        self._create_device_log_tab()
        self._create_log_tab()
        
    def _create_connection_frame(self, parent):
        """Create connection controls"""
        frame = ttk.LabelFrame(parent, text="Connection", padding="10")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        frame.columnconfigure(1, weight=1)
        
        # Discovery section
        discovery_frame = ttk.Frame(frame)
        discovery_frame.grid(row=0, column=0, columnspan=7, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(discovery_frame, text="Discovered Cameras:").pack(side=tk.LEFT, padx=(0, 5))
        
        # Discovered cameras dropdown
        self.discovered_combo = ttk.Combobox(discovery_frame, width=40, state='readonly')
        self.discovered_combo.pack(side=tk.LEFT, padx=(0, 5))
        self.discovered_combo.bind('<<ComboboxSelected>>', self._on_discovered_selected)
        
        # Refresh button
        self.refresh_discovery_btn = ttk.Button(discovery_frame, text="🔄 Refresh", command=self._refresh_discovery)
        self.refresh_discovery_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Manual connection section
        manual_frame = ttk.Frame(frame)
        manual_frame.grid(row=1, column=0, columnspan=7, sticky=(tk.W, tk.E))
        manual_frame.columnconfigure(1, weight=1)
        
        ttk.Label(manual_frame, text="Manual Connection:").grid(row=0, column=0, columnspan=4, sticky=tk.W, pady=(5, 5))
        
        # Host
        ttk.Label(manual_frame, text="Host:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        ttk.Entry(manual_frame, textvariable=self.host, width=20).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # Port
        ttk.Label(manual_frame, text="Port:").grid(row=1, column=2, sticky=tk.W, padx=(0, 5))
        ttk.Entry(manual_frame, textvariable=self.port, width=8).grid(row=1, column=3, sticky=tk.W, padx=(0, 10))
        
        # Connect button
        self.connect_btn = ttk.Button(manual_frame, text="Connect", command=self._connect)
        self.connect_btn.grid(row=1, column=4, padx=(0, 5))
        
        # Disconnect button
        self.disconnect_btn = ttk.Button(manual_frame, text="Disconnect", command=self._disconnect, state=tk.DISABLED)
        self.disconnect_btn.grid(row=1, column=5)
        
        # Connection status
        self.conn_status_label = ttk.Label(manual_frame, text="● Not Connected", style='Disconnected.TLabel')
        self.conn_status_label.grid(row=1, column=6, padx=(20, 0))
        
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
        
    def _create_device_log_tab(self):
        """Create device log display tab"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="Device Log")
        
        # Control frame for filters and refresh
        control_frame = ttk.Frame(frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Log filter (level and component)
        ttk.Label(control_frame, text="Filter:").pack(side=tk.LEFT, padx=(0, 5))
        self.log_filter = tk.StringVar(value="INFO")
        filter_combo = ttk.Combobox(control_frame, textvariable=self.log_filter,
                                   values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "ALL", "TCP", "FFMPEG"],
                                   width=10, state='readonly')
        filter_combo.pack(side=tk.LEFT, padx=(0, 10))
        filter_combo.bind('<<ComboboxSelected>>', lambda e: self._refresh_device_log())
        
        # Lines to show
        ttk.Label(control_frame, text="Lines:").pack(side=tk.LEFT, padx=(0, 5))
        self.log_lines_var = tk.StringVar(value="500")
        lines_entry = ttk.Entry(control_frame, textvariable=self.log_lines_var, width=8)
        lines_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        # Refresh button
        ttk.Button(control_frame, text="🔄 Refresh", command=self._refresh_device_log).pack(side=tk.LEFT, padx=(0, 10))
        
        # Auto-refresh checkbox
        self.device_log_auto_refresh = tk.BooleanVar(value=False)
        ttk.Checkbutton(control_frame, text="Auto-refresh (1s)", 
                       variable=self.device_log_auto_refresh,
                       command=self._toggle_device_log_auto_refresh).pack(side=tk.LEFT)
        
        # Log display
        self.device_log_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=25, 
                                                         font=('Courier', 9), bg='#1e1e1e', fg='#ffffff')
        self.device_log_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Clear log button
        ttk.Button(frame, text="Clear Log", command=self._clear_device_log).pack()
        
        # Setup color tags for log levels (matching rich console colors)
        self.device_log_text.tag_config('timestamp', foreground='#50a14f')  # Dark green
        self.device_log_text.tag_config('logger', foreground='#ffffff')  # White
        self.device_log_text.tag_config('separator', foreground='#808080')  # Gray
        self.device_log_text.tag_config('level_debug', foreground='#a0a0a0')  # Light gray
        self.device_log_text.tag_config('level_info', foreground='#61afef')  # Light blue
        self.device_log_text.tag_config('level_warning', foreground='#e5c07b')  # Yellow/orange
        self.device_log_text.tag_config('level_error', foreground='#e06c75')  # Red
        self.device_log_text.tag_config('level_critical', foreground='#c678dd')  # Magenta
        self.device_log_text.tag_config('message', foreground='#ffffff')  # White
        self.device_log_text.tag_config('ip_address', foreground='#98c379')  # Bright green
        self.device_log_text.tag_config('port', foreground='#61afef')  # Light blue/cyan
        
        # Initial message
        self.device_log_text.insert(tk.END, "Connect to a daemon to view device logs.\n")
        self.device_log_text.config(state=tk.DISABLED)
        
        # Auto-refresh job
        self.device_log_refresh_job = None
        
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
    
    def _clear_device_log(self):
        """Clear the device log display"""
        self.device_log_text.config(state=tk.NORMAL)
        self.device_log_text.delete('1.0', tk.END)
        self.device_log_text.insert(tk.END, "Log cleared.\n")
        self.device_log_text.config(state=tk.DISABLED)
    
    def _on_closing(self):
        """Called when window is closing"""
        # Stop discovery if running
        if self.discovery:
            try:
                self.discovery.stop()
            except:
                pass
        
        # Close window
        self.root.destroy()
        
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
        
        # Update connection UI
        self.conn_status_label.config(text="● Not Connected", style='Disconnected.TLabel')
        self.connect_btn.config(state=tk.NORMAL)
        self.disconnect_btn.config(state=tk.DISABLED)
        
        # Reset status displays to defaults
        self.daemon_status.config(text="Unknown")
        self.stream_status.config(text="Unknown")
        
        # Reset current settings displays
        self.current_device.config(text="Not connected")
        self.current_resolution.config(text="Not connected")
        self.current_fps.config(text="Not connected")
        self.current_streaming.config(text="Unknown")
        
        # Clear settings input fields
        self.new_resolution.set('')
        self.new_fps.set('')
        self.new_device.set('')
        self.new_name.delete(0, tk.END)
        
        # Stop auto-refresh
        if self.refresh_job:
            self.root.after_cancel(self.refresh_job)
            self.refresh_job = None
        
        # Stop device log auto-refresh
        if self.device_log_refresh_job:
            self.root.after_cancel(self.device_log_refresh_job)
            self.device_log_refresh_job = None
        
        # Clear device log display
        self.device_log_text.config(state=tk.NORMAL)
        self.device_log_text.delete('1.0', tk.END)
        self.device_log_text.insert(tk.END, "Connect to a daemon to view device logs.\n")
        self.device_log_text.config(state=tk.DISABLED)
        
        self._log("Disconnected")
    
    def _start_discovery(self):
        """Start discovering Exostream services on the network (runs continuously)"""
        if self.discovery:
            return  # Already running
        
        def discovery_thread():
            try:
                self.discovery = ExostreamServiceDiscovery(callback=self._on_service_discovered)
                self.discovery.start()
                self.message_queue.put(('discovery_started', None))
            except Exception as e:
                self.message_queue.put(('discovery_error', str(e)))
        
        threading.Thread(target=discovery_thread, daemon=True).start()
    
    def _refresh_discovery(self):
        """Force refresh of discovered cameras list"""
        if self.discovery:
            # Get current services and update dropdown
            services = self.discovery.get_services()
            
            # Update discovered_services dict
            self.discovered_services.clear()
            for svc in services:
                display_name = f"{svc['name']} ({svc['host']}:{svc['port']})"
                self.discovered_services[display_name] = svc
            
            # Update combo box
            values = list(self.discovered_services.keys())
            self.discovered_combo.config(values=values)
            
            self._log(f"Refreshed: Found {len(services)} camera(s)")
        else:
            # Restart discovery if not running
            self._start_discovery()
    
    def _on_service_discovered(self, event_type: str, data):
        """Called when a service is discovered/removed"""
        self.message_queue.put(('service_event', {'event': event_type, 'data': data}))
    
    def _on_discovered_selected(self, event):
        """Called when user selects a discovered camera"""
        selection = self.discovered_combo.get()
        if selection and selection in self.discovered_services:
            service = self.discovered_services[selection]
            # Update host and port
            self.host.set(service['host'])
            self.port.set(str(service['port']))
            self._log(f"Selected: {service['name']} at {service['host']}:{service['port']}")
        
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
        self._refresh_device_log()
        
        # Start auto-refresh if enabled
        if self.auto_refresh.get():
            self._schedule_refresh()
        
        # Start device log auto-refresh if enabled
        if self.device_log_auto_refresh.get():
            self._schedule_device_log_refresh()
        
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
        
        # Update current settings display
        self.current_device.config(text=settings.get('device', 'Unknown'))
        self.current_resolution.config(text=settings.get('resolution', 'Unknown'))
        self.current_fps.config(text=str(settings.get('fps', 'Unknown')))
        
        if settings.get('streaming'):
            stream_name = settings.get('name', 'Unknown')
            self.current_streaming.config(text=f"Yes - {stream_name}")
        else:
            self.current_streaming.config(text="No")
        
        # Pre-fill update settings fields with current values
        self._populate_settings_fields(settings)
    
    def _populate_settings_fields(self, settings: Dict[str, Any]):
        """Populate the update settings input fields with current values"""
        # Set resolution
        resolution = settings.get('resolution', '')
        if resolution:
            self.new_resolution.set(resolution)
        
        # Set FPS
        fps = settings.get('fps')
        if fps is not None:
            self.new_fps.set(str(fps))
        
        # Set device
        device = settings.get('device', '')
        if device:
            self.new_device.set(device)
        
        # Set stream name
        name = settings.get('name', '')
        if name:
            self.new_name.delete(0, tk.END)
            self.new_name.insert(0, name)
        
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
    
    def _refresh_device_log(self):
        """Refresh device log display"""
        if not self.connected:
            self.device_log_text.config(state=tk.NORMAL)
            self.device_log_text.delete('1.0', tk.END)
            self.device_log_text.insert(tk.END, "Connect to a daemon to view device logs.\n")
            self.device_log_text.config(state=tk.DISABLED)
            return
        
        def refresh_thread():
            try:
                # Get filter settings
                filter_value = self.log_filter.get()
                
                # Determine if it's a level filter or component filter
                level = None
                component_filter = None
                
                if filter_value in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
                    level = filter_value
                elif filter_value == "ALL":
                    level = None
                elif filter_value == "TCP":
                    component_filter = "tcp"
                elif filter_value == "FFMPEG":
                    component_filter = "ffmpeg"
                
                lines_str = self.log_lines_var.get()
                try:
                    lines = int(lines_str) if lines_str else None
                except ValueError:
                    lines = 500  # Default
                
                # Get logs from daemon
                result = self.client.get_logs(level=level, lines=lines)
                
                # Apply component filtering if needed (client-side)
                if component_filter:
                    logs = result.get('logs', [])
                    filtered_logs = []
                    for log_line in logs:
                        # Check if log line contains the component name
                        # Format: YYYY-MM-DD HH:MM:SS - logger_name - LEVEL - message
                        # Look for component in logger name (between first and second dash)
                        if component_filter == "tcp":
                            # Look for tcp_server in logger name
                            if "tcp_server" in log_line.lower() or "tcp" in log_line.lower():
                                filtered_logs.append(log_line)
                        elif component_filter == "ffmpeg":
                            # Look for ffmpeg in logger name
                            if "ffmpeg" in log_line.lower():
                                filtered_logs.append(log_line)
                    result['logs'] = filtered_logs
                    result['total_lines'] = len(filtered_logs)
                    result['filtered_by'] = component_filter.upper()
                
                self.message_queue.put(('device_log_update', result))
            except Exception as e:
                self.message_queue.put(('device_log_error', str(e)))
        
        threading.Thread(target=refresh_thread, daemon=True).start()
    
    def _toggle_device_log_auto_refresh(self):
        """Toggle auto-refresh for device log"""
        if self.device_log_auto_refresh.get() and self.connected:
            self._schedule_device_log_refresh()
        elif self.device_log_refresh_job:
            self.root.after_cancel(self.device_log_refresh_job)
            self.device_log_refresh_job = None
    
    def _schedule_device_log_refresh(self):
        """Schedule next device log refresh"""
        if self.device_log_auto_refresh.get() and self.connected:
            self._refresh_device_log()
            self.device_log_refresh_job = self.root.after(1000, self._schedule_device_log_refresh)  # 1 second
    
    def _insert_colored_log_line(self, log_line: str):
        """Insert a log line with colorization matching rich console output"""
        import re
        
        # Pattern: YYYY-MM-DD HH:MM:SS - logger_name - LEVEL - message
        # Or: [HH:MM:SS] INFO Client connected from ('IP', PORT)
        pattern1 = r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - ([^-]+) - (DEBUG|INFO|WARNING|ERROR|CRITICAL) - (.+)$'
        pattern2 = r'^\[(\d{2}:\d{2}:\d{2})\] (DEBUG|INFO|WARNING|ERROR|CRITICAL) (.+)$'
        
        match1 = re.match(pattern1, log_line)
        match2 = re.match(pattern2, log_line)
        
        if match1:
            # Format: YYYY-MM-DD HH:MM:SS - logger_name - LEVEL - message
            timestamp, logger_name, level, message = match1.groups()
            
            # Insert timestamp
            start = self.device_log_text.index(tk.END + '-1c')
            self.device_log_text.insert(tk.END, timestamp)
            end = self.device_log_text.index(tk.END + '-1c')
            self.device_log_text.tag_add('timestamp', start, end)
            
            # Insert separator
            self.device_log_text.insert(tk.END, ' - ')
            start = self.device_log_text.index(tk.END + '-3c')
            end = self.device_log_text.index(tk.END + '-1c')
            self.device_log_text.tag_add('separator', start, end)
            
            # Insert logger name
            start = self.device_log_text.index(tk.END + '-1c')
            self.device_log_text.insert(tk.END, logger_name.strip())
            end = self.device_log_text.index(tk.END + '-1c')
            self.device_log_text.tag_add('logger', start, end)
            
            # Insert separator
            self.device_log_text.insert(tk.END, ' - ')
            start = self.device_log_text.index(tk.END + '-3c')
            end = self.device_log_text.index(tk.END + '-1c')
            self.device_log_text.tag_add('separator', start, end)
            
            # Insert level with color
            level_tag = f'level_{level.lower()}'
            start = self.device_log_text.index(tk.END + '-1c')
            self.device_log_text.insert(tk.END, level)
            end = self.device_log_text.index(tk.END + '-1c')
            self.device_log_text.tag_add(level_tag, start, end)
            
            # Insert separator
            self.device_log_text.insert(tk.END, ' - ')
            start = self.device_log_text.index(tk.END + '-3c')
            end = self.device_log_text.index(tk.END + '-1c')
            self.device_log_text.tag_add('separator', start, end)
            
            # Insert message (with special handling for IP addresses and ports)
            self._insert_colored_message(message)
            
        elif match2:
            # Format: [HH:MM:SS] LEVEL message
            timestamp, level, message = match2.groups()
            
            # Insert timestamp
            start = self.device_log_text.index(tk.END + '-1c')
            self.device_log_text.insert(tk.END, f'[{timestamp}]')
            end = self.device_log_text.index(tk.END + '-1c')
            self.device_log_text.tag_add('timestamp', start, end)
            
            # Insert space and level
            self.device_log_text.insert(tk.END, ' ')
            level_tag = f'level_{level.lower()}'
            start = self.device_log_text.index(tk.END + '-1c')
            self.device_log_text.insert(tk.END, level)
            end = self.device_log_text.index(tk.END + '-1c')
            self.device_log_text.tag_add(level_tag, start, end)
            
            # Insert space and message
            self.device_log_text.insert(tk.END, ' ')
            self._insert_colored_message(message)
        else:
            # Plain text line
            self.device_log_text.insert(tk.END, log_line)
        
        self.device_log_text.insert(tk.END, '\n')
    
    def _insert_colored_message(self, message: str):
        """Insert message with colorization for IP addresses and ports"""
        import re
        
        # Pattern for: Client connected from ('IP', PORT) or ('IP',PORT)
        ip_port_pattern = r"\(['\"]?(\d+\.\d+\.\d+\.\d+)['\"]?,\s*(\d+)\)"
        
        last_pos = 0
        for match in re.finditer(ip_port_pattern, message):
            # Insert text before match
            if match.start() > last_pos:
                start = self.device_log_text.index(tk.END + '-1c')
                self.device_log_text.insert(tk.END, message[last_pos:match.start()])
                end = self.device_log_text.index(tk.END + '-1c')
                self.device_log_text.tag_add('message', start, end)
            
            # Insert opening parenthesis
            self.device_log_text.insert(tk.END, '(')
            
            # Insert IP address
            ip_addr = match.group(1)
            start = self.device_log_text.index(tk.END + '-1c')
            self.device_log_text.insert(tk.END, ip_addr)
            end = self.device_log_text.index(tk.END + '-1c')
            self.device_log_text.tag_add('ip_address', start, end)
            
            # Insert comma and space
            self.device_log_text.insert(tk.END, ', ')
            
            # Insert port number
            port = match.group(2)
            start = self.device_log_text.index(tk.END + '-1c')
            self.device_log_text.insert(tk.END, port)
            end = self.device_log_text.index(tk.END + '-1c')
            self.device_log_text.tag_add('port', start, end)
            
            # Insert closing parenthesis
            self.device_log_text.insert(tk.END, ')')
            
            last_pos = match.end()
        
        # Insert remaining text
        if last_pos < len(message):
            start = self.device_log_text.index(tk.END + '-1c')
            self.device_log_text.insert(tk.END, message[last_pos:])
            end = self.device_log_text.index(tk.END + '-1c')
            self.device_log_text.tag_add('message', start, end)
    
    def _update_device_log_display(self, data: Dict[str, Any]):
        """Update device log display with new logs"""
        logs = data.get('logs', [])
        total_lines = data.get('total_lines', 0)
        filtered_by = data.get('filtered_by')
        
        # Enable text widget for editing
        self.device_log_text.config(state=tk.NORMAL)
        self.device_log_text.delete('1.0', tk.END)
        
        if not logs:
            self.device_log_text.insert(tk.END, "No logs available.\n")
            if filtered_by:
                self.device_log_text.insert(tk.END, f"Filtered by: {filtered_by}\n")
        else:
            # Display logs with colorization
            for log_line in logs:
                self._insert_colored_log_line(log_line)
            
            # Add summary (plain text)
            self.device_log_text.insert(tk.END, f"\n--- Total: {total_lines} lines")
            if filtered_by:
                self.device_log_text.insert(tk.END, f" (filtered by {filtered_by})")
            self.device_log_text.insert(tk.END, " ---\n")
        
        # Scroll to bottom
        self.device_log_text.see(tk.END)
        self.device_log_text.config(state=tk.DISABLED)
        
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
                elif msg_type == 'discovery_started':
                    self._log("Discovery started - continuously scanning for cameras")
                elif msg_type == 'discovery_error':
                    self._log(f"Discovery error: {msg_data}", "ERROR")
                    messagebox.showerror("Discovery Error", f"Failed to start discovery: {msg_data}")
                elif msg_type == 'device_log_update':
                    self._update_device_log_display(msg_data)
                elif msg_type == 'device_log_error':
                    self._log(f"Error fetching device logs: {msg_data}", "ERROR")
                    self.device_log_text.config(state=tk.NORMAL)
                    self.device_log_text.insert(tk.END, f"\n[ERROR] Failed to fetch logs: {msg_data}\n")
                    self.device_log_text.see(tk.END)
                    self.device_log_text.config(state=tk.DISABLED)
                elif msg_type == 'service_event':
                    self._handle_service_event(msg_data)
                    
        except queue.Empty:
            pass
        
        # Schedule next check
        self.root.after(100, self._process_messages)
    
    def _handle_service_event(self, data: Dict):
        """Handle service discovery events"""
        event_type = data.get('event')
        service_data = data.get('data')
        
        if event_type == 'added' or event_type == 'updated':
            try:
                # Extract service info from ExostreamServiceInfo dataclass
                name = service_data.name
                host = service_data.host
                port = service_data.port
                hostname = service_data.hostname
                version = service_data.version
                
                display_name = f"{name} ({host}:{port})"
                
                self.discovered_services[display_name] = {
                    'name': name,
                    'host': host,
                    'port': port,
                    'hostname': hostname,
                    'version': version
                }
                
                # Update combo box
                values = list(self.discovered_services.keys())
                self.discovered_combo.config(values=values)
                
                if event_type == 'added':
                    self._log(f"Discovered: {name} at {host}:{port}")
                
            except Exception as e:
                self._log(f"Error processing service: {e}", "ERROR")
            
        elif event_type == 'removed':
            # Remove service from our list using host:port as key
            service_key = f"{service_data.host}:{service_data.port}"
            
            # Find and remove from dict
            to_remove = None
            for display_name, info in self.discovered_services.items():
                if f"{info['host']}:{info['port']}" == service_key:
                    to_remove = display_name
                    break
            
            if to_remove:
                del self.discovered_services[to_remove]
                
                # Update combo box
                values = list(self.discovered_services.keys())
                self.discovered_combo.config(values=values)
                
                self._log(f"Lost: {service_data.name}")


def main():
    """Main entry point"""
    root = tk.Tk()
    app = ExostreamGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

