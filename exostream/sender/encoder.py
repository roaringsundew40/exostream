"""GStreamer encoder pipeline for webcam streaming"""

import sys
from typing import Optional, Callable
from exostream.common.logger import get_logger
from exostream.common.config import VideoConfig, SRTConfig
from exostream.common.gst_utils import detect_h264_encoder, check_srt_support

try:
    import gi
    gi.require_version('Gst', '1.0')
    from gi.repository import Gst, GLib
except ImportError as e:
    print(f"Error: GStreamer Python bindings not found: {e}")
    sys.exit(1)

logger = get_logger(__name__)


class StreamEncoder:
    """Handles video encoding and streaming pipeline"""
    
    def __init__(
        self,
        device_path: str,
        video_config: VideoConfig,
        srt_config: SRTConfig,
        on_error: Optional[Callable] = None,
        use_software_encoder: bool = False
    ):
        """
        Initialize the stream encoder
        
        Args:
            device_path: Path to video device (e.g., /dev/video0)
            video_config: Video encoding configuration
            srt_config: SRT streaming configuration
            on_error: Callback function for errors
            use_software_encoder: Force software encoding (x264enc) instead of hardware
        """
        self.device_path = device_path
        self.video_config = video_config
        self.srt_config = srt_config
        self.on_error = on_error
        self.use_software_encoder = use_software_encoder
        
        self.pipeline: Optional[Gst.Pipeline] = None
        self.loop: Optional[GLib.MainLoop] = None
        self.bus: Optional[Gst.Bus] = None
        
        # Detect encoder
        self.encoder_name = detect_h264_encoder(prefer_software=use_software_encoder)
        if not self.encoder_name:
            raise RuntimeError("No H.264 encoder found!")
        
        if self.encoder_name == 'x264enc':
            logger.warning("Using SOFTWARE encoder (x264enc) - this will use more CPU")
            logger.warning("Hardware encoder (v4l2h264enc) may be unavailable or buggy on your system")
        else:
            logger.info(f"Using encoder: {self.encoder_name}")
        
        # Check SRT support
        if not check_srt_support():
            raise RuntimeError("SRT support not found! Install gstreamer1.0-plugins-bad")
    
    def build_pipeline(self) -> Gst.Pipeline:
        """
        Build the GStreamer pipeline
        
        Pipeline structure:
        v4l2src -> capsfilter -> queue -> encoder -> h264parse -> 
        mpegtsmux -> queue -> srtsink
        
        Returns:
            Configured GStreamer pipeline
        """
        logger.info("Building GStreamer pipeline...")
        
        # Create pipeline
        pipeline = Gst.Pipeline.new("exostream-sender")
        
        # Create elements
        elements = {}
        
        try:
            # Source: v4l2src for webcam
            elements['source'] = Gst.ElementFactory.make("v4l2src", "source")
            elements['source'].set_property("device", self.device_path)
            
            # Caps filter - allow both MJPEG and raw, camera will choose
            elements['capsfilter'] = Gst.ElementFactory.make("capsfilter", "capsfilter")
            # Try MJPEG first (what C930e provides at 1080p), then raw as fallback
            caps = Gst.Caps.from_string(
                f"image/jpeg,width={self.video_config.width},"
                f"height={self.video_config.height},"
                f"framerate={self.video_config.fps}/1"
            )
            elements['capsfilter'].set_property("caps", caps)
            
            # JPEG decoder (for MJPEG cameras like Logitech C930e)
            elements['jpegdec'] = Gst.ElementFactory.make("jpegdec", "jpegdec")
            
            # Video convert for format conversion
            elements['videoconvert'] = Gst.ElementFactory.make("videoconvert", "videoconvert")
            
            # Videoscale in case we need to adjust resolution
            elements['videoscale'] = Gst.ElementFactory.make("videoscale", "videoscale")
            
            # Caps filter - MUST force I420 format for v4l2h264enc
            elements['encoder_caps'] = Gst.ElementFactory.make("capsfilter", "encoder_caps")
            # v4l2h264enc on Pi only supports I420 or NV12, NOT YUY2
            encoder_caps = Gst.Caps.from_string(
                f"video/x-raw,format=I420,"
                f"width={self.video_config.width},"
                f"height={self.video_config.height}"
            )
            elements['encoder_caps'].set_property("caps", encoder_caps)
            
            # Queue before encoder
            elements['queue1'] = Gst.ElementFactory.make("queue", "queue1")
            elements['queue1'].set_property("max-size-buffers", 0)
            elements['queue1'].set_property("max-size-time", 0)
            elements['queue1'].set_property("max-size-bytes", 0)
            
            # H.264 encoder
            elements['encoder'] = Gst.ElementFactory.make(self.encoder_name, "encoder")
            self._configure_encoder(elements['encoder'])
            
            # H.264 parser - CRITICAL for proper headers
            elements['h264parse'] = Gst.ElementFactory.make("h264parse", "h264parse")
            # Insert SPS/PPS before EVERY IDR frame
            elements['h264parse'].set_property("config-interval", -1)  # -1 = insert before every IDR
            
            # Video caps - force proper H.264 format for streaming
            elements['video_caps'] = Gst.ElementFactory.make("capsfilter", "video_caps")
            video_caps = Gst.Caps.from_string(
                "video/x-h264,stream-format=byte-stream,alignment=nal,profile=baseline"
            )
            elements['video_caps'].set_property("caps", video_caps)
            
            # Queue before sink
            elements['queue2'] = Gst.ElementFactory.make("queue", "queue2")
            
            # SRT sink
            elements['srtsink'] = Gst.ElementFactory.make("srtsink", "srtsink")
            self._configure_srt_sink(elements['srtsink'])
            
        except Exception as e:
            logger.error(f"Failed to create pipeline elements: {e}")
            raise
        
        # Add all elements to pipeline
        for element in elements.values():
            pipeline.add(element)
        
        # Link elements
        try:
            elements['source'].link(elements['capsfilter'])
            elements['capsfilter'].link(elements['jpegdec'])
            elements['jpegdec'].link(elements['videoconvert'])
            elements['videoconvert'].link(elements['videoscale'])
            elements['videoscale'].link(elements['encoder_caps'])
            elements['encoder_caps'].link(elements['queue1'])
            elements['queue1'].link(elements['encoder'])
            elements['encoder'].link(elements['h264parse'])
            elements['h264parse'].link(elements['video_caps'])
            elements['video_caps'].link(elements['queue2'])
            elements['queue2'].link(elements['srtsink'])
        except Exception as e:
            logger.error(f"Failed to link pipeline elements: {e}")
            raise
        
        logger.info("Pipeline built successfully")
        return pipeline
    
    def _configure_encoder(self, encoder: Gst.Element):
        """Configure the H.264 encoder based on type"""
        if self.encoder_name == "v4l2h264enc":
            # Raspberry Pi 4 hardware encoder
            # Use minimal configuration for compatibility
            try:
                # Simple bitrate control only
                controls = Gst.Structure.new_empty("controls")
                controls.set_value("video_bitrate", self.video_config.bitrate * 1000)
                encoder.set_property("extra-controls", controls)
                logger.debug(f"Set encoder bitrate to {self.video_config.bitrate} kbps")
            except Exception as e:
                logger.warning(f"Could not set encoder controls: {e}")
                logger.warning("Encoder will use default settings")
        
        elif self.encoder_name == "omxh264enc":
            # Raspberry Pi 3 hardware encoder
            encoder.set_property("target-bitrate", self.video_config.bitrate * 1000)
            encoder.set_property("interval-intraframes", self.video_config.keyframe_interval)
            encoder.set_property("control-rate", "variable")
        
        elif self.encoder_name == "x264enc":
            # Software encoder - configure for proper streaming
            encoder.set_property("bitrate", self.video_config.bitrate)
            encoder.set_property("speed-preset", "veryfast")  # veryfast is more stable than ultrafast
            encoder.set_property("tune", "zerolatency")
            # Keyframe every 2 seconds for quick VLC startup
            encoder.set_property("key-int-max", self.video_config.fps * 2)
            # Critical: Force IDR frames (not just I-frames)
            encoder.set_property("option-string", "keyint=%d:min-keyint=%d:scenecut=0" % (
                self.video_config.fps * 2,
                self.video_config.fps * 2
            ))
            encoder.set_property("bframes", 0)  # No B-frames for lower latency
            encoder.set_property("threads", 2)  # Limit threads on Pi
            logger.info("Using software encoder (x264enc) with streaming optimization")
    
    def _configure_srt_sink(self, srtsink: Gst.Element):
        """Configure the SRT sink element"""
        # Generate SRT URI
        srt_uri = self.srt_config.get_uri()
        logger.info(f"SRT URI: {srt_uri}")
        
        srtsink.set_property("uri", srt_uri)
        srtsink.set_property("mode", "listener")  # Act as server
        srtsink.set_property("wait-for-connection", False)  # Don't wait, stream immediately
        
        # Optional: Set passphrase for encryption
        if self.srt_config.passphrase:
            srtsink.set_property("passphrase", self.srt_config.passphrase)
            logger.info("SRT encryption enabled")
    
    def start(self):
        """Start the streaming pipeline"""
        if not self.pipeline:
            self.pipeline = self.build_pipeline()
        
        # Set up bus watch
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message", self._on_bus_message)
        
        # Start pipeline
        logger.info("Starting pipeline...")
        ret = self.pipeline.set_state(Gst.State.PLAYING)
        
        if ret == Gst.StateChangeReturn.FAILURE:
            logger.error("Unable to set pipeline to PLAYING state")
            raise RuntimeError("Failed to start pipeline")
        
        logger.info("Pipeline started successfully")
        
        # Create and run main loop
        self.loop = GLib.MainLoop()
        try:
            self.loop.run()
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the streaming pipeline"""
        if self.pipeline:
            logger.info("Stopping pipeline...")
            self.pipeline.set_state(Gst.State.NULL)
            logger.info("Pipeline stopped")
        
        if self.loop and self.loop.is_running():
            self.loop.quit()
    
    def _on_bus_message(self, bus: Gst.Bus, message: Gst.Message):
        """Handle messages from the GStreamer bus"""
        t = message.type
        
        if t == Gst.MessageType.EOS:
            logger.info("End of stream")
            self.stop()
        
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error(f"Pipeline error: {err.message}")
            if debug:
                logger.error(f"Debug info: {debug}")
            
            # Log the element that caused the error
            if message.src:
                logger.error(f"Error from element: {message.src.get_name()}")
            
            if self.on_error:
                self.on_error(err.message)
            
            self.stop()
        
        elif t == Gst.MessageType.WARNING:
            warn, debug = message.parse_warning()
            logger.warning(f"Pipeline warning: {warn.message}")
            logger.debug(f"Debug info: {debug}")
        
        elif t == Gst.MessageType.STATE_CHANGED:
            if message.src == self.pipeline:
                old_state, new_state, pending_state = message.parse_state_changed()
                logger.debug(
                    f"Pipeline state changed from {old_state.value_nick} "
                    f"to {new_state.value_nick}"
                )
        
        elif t == Gst.MessageType.INFO:
            info, debug = message.parse_info()
            logger.info(f"Pipeline info: {info.message}")
        
        elif t == Gst.MessageType.ELEMENT:
            # Log element-specific messages (like SRT connection events)
            structure = message.get_structure()
            if structure and structure.get_name() == "GstSRTSinkStats":
                logger.info("SRT client connected!")
            elif structure:
                logger.debug(f"Element message: {structure.get_name()}")
    
    def get_stats(self) -> dict:
        """
        Get streaming statistics
        
        Returns:
            Dictionary with statistics
        """
        stats = {
            'bitrate': self.video_config.bitrate,
            'resolution': self.video_config.resolution,
            'fps': self.video_config.fps,
            'encoder': self.encoder_name,
            'device': self.device_path,
        }
        
        return stats

