"""
Bridge Controller Module
Coordinates Art-Net reception and Home Assistant control
"""
import asyncio
import logging
from typing import Dict, Any
from artnet_receiver import ArtNetReceiver
from ha_client import HomeAssistantClient
from entity_mapper import EntityMapper
from config_manager import ConfigManager
import time

logger = logging.getLogger(__name__)


class BridgeController:
    """Main controller that bridges Art-Net to Home Assistant."""
    
    def __init__(self):
        """Initialize bridge controller."""
        self.config = ConfigManager()
        self.artnet = None
        self.ha_client = None
        self.mapper = EntityMapper()
        self.running = False
        self.loop = None
        self.last_dmx_data = {}
        self.last_command_time = {}  # Track last command time per entity
        self.min_command_interval = 0.05  # Minimum 50ms between commands per entity
        self.status = {
            'artnet_running': False,
            'ha_connected': False,
            'entities_loaded': 0,
            'last_update': None
        }
        
    async def start(self):
        """Start the bridge."""
        if self.running:
            logger.warning("Bridge already running")
            return
            
        logger.info("Starting bridge...")
        
        # Get configuration
        ha_config = self.config.get_ha_config()
        artnet_config = self.config.get_artnet_config()
        
        # Initialize Home Assistant client
        self.ha_client = HomeAssistantClient(ha_config['url'], ha_config['token'])
        
        try:
            await self.ha_client.connect()
            self.status['ha_connected'] = True
            logger.info("Connected to Home Assistant")
            
            # Load entities with "orchestream" label
            entities = await self.ha_client.get_entities_with_label('orchestream')
            self.status['entities_loaded'] = len(entities)
            
            if entities:
                # Auto-assign channels if not already mapped
                start_channel = self.config.get_dmx_start_channel()
                self.mapper.auto_assign_channels(entities, start_channel)
                logger.info(f"Loaded {len(entities)} entities with 'orchestream' label")
            else:
                logger.warning("No entities found with 'orchestream' label")
                
        except Exception as e:
            logger.error(f"Failed to connect to Home Assistant: {e}")
            raise
            
        # Initialize Art-Net receiver
        self.artnet = ArtNetReceiver(
            bind_ip=artnet_config['bind_ip'],
            port=artnet_config['port'],
            universe=artnet_config['universe']
        )
        self.artnet.set_callback(self._handle_dmx_data)
        self.artnet.start()
        self.status['artnet_running'] = True
        
        self.running = True
        logger.info("Bridge started successfully")
        
    async def stop(self):
        """Stop the bridge."""
        if not self.running:
            return
            
        logger.info("Stopping bridge...")
        
        self.running = False
        
        if self.artnet:
            self.artnet.stop()
            self.status['artnet_running'] = False
            
        if self.ha_client:
            await self.ha_client.disconnect()
            self.status['ha_connected'] = False
            
        logger.info("Bridge stopped")
        
    def _handle_dmx_data(self, dmx_data: Dict[int, int]):
        """
        Handle incoming DMX data from Art-Net.
        Called from Art-Net receiver thread.
        
        Args:
            dmx_data: Dictionary of {channel: value}
        """
        # Check if data actually changed
        if dmx_data == self.last_dmx_data:
            return
            
        self.last_dmx_data = dmx_data.copy()
        
        # Process in async context
        if self.loop and self.running:
            try:
                if not self.loop.is_closed():
                    asyncio.run_coroutine_threadsafe(
                        self._process_dmx_data(dmx_data),
                        self.loop
                    )
            except Exception as e:
                logger.error(f"Error scheduling DMX processing: {e}")
            
    async def _process_dmx_data(self, dmx_data: Dict[int, int]):
        """
        Process DMX data and send commands to Home Assistant.
        
        Args:
            dmx_data: Dictionary of {channel: value}
        """
        if not self.ha_client or not self.ha_client.connected:
            return
            
        try:
            # Get commands from mapper
            commands = self.mapper.get_entity_commands(dmx_data)
            
            # Execute commands with throttling - process one at a time
            current_time = time.time()
            
            for command in commands:
                entity_id = command['entity_id']
                action = command['action']
                
                # Check if we should throttle this command
                last_time = self.last_command_time.get(entity_id, 0)
                if current_time - last_time < self.min_command_interval:
                    continue  # Skip this command, too soon
                
                try:
                    if action == 'turn_on':
                        kwargs = {}
                        if 'brightness' in command:
                            kwargs['brightness'] = command['brightness']
                        if 'rgb_color' in command:
                            kwargs['rgb_color'] = command['rgb_color']
                        if 'rgbw_color' in command:
                            kwargs['rgbw_color'] = command['rgbw_color']
                        if 'rgbww_color' in command:
                            kwargs['rgbww_color'] = command['rgbww_color']
                        if 'kelvin' in command:
                            kwargs['kelvin'] = command['kelvin']
                            
                        await self.ha_client.turn_on(entity_id, **kwargs)
                        
                    elif action == 'turn_off':
                        await self.ha_client.turn_off(entity_id)
                    
                    # Update last command time
                    self.last_command_time[entity_id] = current_time
                    
                    # Small delay between commands to avoid overwhelming HA
                    await asyncio.sleep(0.01)
                        
                except Exception as e:
                    logger.error(f"Error controlling {entity_id}: {e}")
                    
            self.status['last_update'] = asyncio.get_event_loop().time()
            
        except Exception as e:
            logger.error(f"Error processing DMX data: {e}")
            
    def get_status(self) -> Dict[str, Any]:
        """Get current bridge status."""
        return self.status.copy()
        
    def get_mappings(self):
        """Get current entity mappings."""
        return self.mapper.get_all_mappings()
        
    async def refresh_entities(self):
        """Refresh entities from Home Assistant."""
        if not self.ha_client or not self.ha_client.connected:
            raise Exception("Home Assistant not connected")
            
        entities = await self.ha_client.get_entities_with_label('orchestream')
        self.status['entities_loaded'] = len(entities)
        
        start_channel = self.config.get_dmx_start_channel()
        self.mapper.auto_assign_channels(entities, start_channel)
        
        return entities
        
    def set_event_loop(self, loop):
        """Set the asyncio event loop for callbacks."""
        self.loop = loop


# Global bridge instance
_bridge = None


def get_bridge() -> BridgeController:
    """Get global bridge instance."""
    global _bridge
    if _bridge is None:
        _bridge = BridgeController()
    return _bridge
