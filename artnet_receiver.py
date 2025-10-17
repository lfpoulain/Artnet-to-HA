"""
Art-Net DMX Receiver Module
Listens for Art-Net packets and extracts DMX channel data
"""
import socket
import struct
import threading
import logging
from typing import Callable, Dict

logger = logging.getLogger(__name__)


class ArtNetReceiver:
    """Receives Art-Net DMX packets and triggers callbacks with channel data."""
    
    ARTNET_HEADER = b'Art-Net\x00'
    ARTNET_DMX = 0x5000
    
    def __init__(self, bind_ip: str = '0.0.0.0', port: int = 6454, universe: int = 0):
        """
        Initialize Art-Net receiver.
        
        Args:
            bind_ip: IP address to bind to
            port: UDP port to listen on (default 6454)
            universe: Art-Net universe to listen to (default 0)
        """
        self.bind_ip = bind_ip
        self.port = port
        self.universe = universe
        self.socket = None
        self.running = False
        self.thread = None
        self.dmx_data = [0] * 512  # DMX universe has 512 channels
        self.callback = None
        
    def set_callback(self, callback: Callable[[Dict[int, int]], None]):
        """Set callback function to be called when DMX data is received."""
        self.callback = callback
        
    def start(self):
        """Start listening for Art-Net packets."""
        if self.running:
            logger.warning("Art-Net receiver already running")
            return
            
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.bind_ip, self.port))
        self.running = True
        
        self.thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.thread.start()
        
        logger.info(f"Art-Net receiver started on {self.bind_ip}:{self.port}, Universe {self.universe}")
        
    def stop(self):
        """Stop listening for Art-Net packets."""
        if not self.running:
            return
            
        self.running = False
        if self.socket:
            self.socket.close()
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("Art-Net receiver stopped")
        
    def _receive_loop(self):
        """Main receive loop running in separate thread."""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(1024)
                self._parse_artnet_packet(data)
            except Exception as e:
                if self.running:
                    logger.error(f"Error receiving Art-Net packet: {e}")
                    
    def _parse_artnet_packet(self, data: bytes):
        """Parse incoming Art-Net packet."""
        if len(data) < 18:
            return
            
        # Check Art-Net header
        if data[:8] != self.ARTNET_HEADER:
            return
            
        # Check opcode (should be 0x5000 for DMX data)
        opcode = struct.unpack('<H', data[8:10])[0]
        if opcode != self.ARTNET_DMX:
            return
            
        # Parse protocol version, sequence, physical, universe
        version = struct.unpack('>H', data[10:12])[0]
        sequence = data[12]
        physical = data[13]
        universe_low = data[14]
        universe_high = data[15]
        packet_universe = universe_low | (universe_high << 8)
        
        # Check if this is our universe
        if packet_universe != self.universe:
            return
            
        # Get DMX data length
        length = struct.unpack('>H', data[16:18])[0]
        
        # Extract DMX data
        dmx_start = 18
        dmx_end = dmx_start + length
        
        if len(data) < dmx_end:
            return
            
        new_dmx_data = list(data[dmx_start:dmx_end])
        
        # Pad with zeros if needed
        while len(new_dmx_data) < 512:
            new_dmx_data.append(0)
            
        # Check if data changed
        if new_dmx_data != self.dmx_data:
            self.dmx_data = new_dmx_data
            
            # Create dictionary of channel:value pairs (1-indexed)
            channel_data = {i+1: val for i, val in enumerate(self.dmx_data)}
            
            # Call callback if set
            if self.callback:
                try:
                    self.callback(channel_data)
                except Exception as e:
                    logger.error(f"Error in DMX callback: {e}")
                    
    def get_channel(self, channel: int) -> int:
        """
        Get current value of a specific DMX channel.
        
        Args:
            channel: DMX channel number (1-512)
            
        Returns:
            Current value (0-255)
        """
        if 1 <= channel <= 512:
            return self.dmx_data[channel - 1]
        return 0
        
    def get_channels(self, start: int, count: int) -> list:
        """
        Get multiple consecutive channel values.
        
        Args:
            start: Starting channel number (1-512)
            count: Number of channels to get
            
        Returns:
            List of channel values
        """
        if start < 1 or start > 512:
            return []
        end = min(start + count, 512)
        return self.dmx_data[start-1:end]
