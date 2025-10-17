"""
Home Assistant WebSocket Client Module
Connects to Home Assistant and controls entities
"""
import asyncio
import json
import logging
from typing import Optional, List, Dict, Any
import aiohttp

logger = logging.getLogger(__name__)


class HomeAssistantClient:
    """Client for communicating with Home Assistant via WebSocket API."""
    
    def __init__(self, url: str, token: str):
        """
        Initialize Home Assistant client.
        
        Args:
            url: Home Assistant URL (e.g., http://homeassistant.local:8123)
            token: Long-lived access token
        """
        self.url = url.rstrip('/')
        self.token = token
        self.ws_url = self.url.replace('http://', 'ws://').replace('https://', 'wss://') + '/api/websocket'
        self.session: Optional[aiohttp.ClientSession] = None
        self.websocket: Optional[aiohttp.ClientWebSocketResponse] = None
        self.message_id = 1
        self.connected = False
        self.entities: Dict[str, Dict] = {}
        self._lock = asyncio.Lock()  # Lock for WebSocket operations
        
    async def connect(self):
        """Connect to Home Assistant WebSocket API."""
        try:
            self.session = aiohttp.ClientSession()
            self.websocket = await self.session.ws_connect(self.ws_url)
            
            # Receive auth required message
            msg = await self.websocket.receive_json()
            if msg['type'] != 'auth_required':
                raise Exception(f"Unexpected message type: {msg['type']}")
                
            # Send auth message
            await self.websocket.send_json({
                'type': 'auth',
                'access_token': self.token
            })
            
            # Receive auth result
            msg = await self.websocket.receive_json()
            if msg['type'] != 'auth_ok':
                raise Exception(f"Authentication failed: {msg}")
                
            self.connected = True
            logger.info("Connected to Home Assistant")
            
        except Exception as e:
            logger.error(f"Failed to connect to Home Assistant: {e}")
            await self.disconnect()
            raise
            
    async def disconnect(self):
        """Disconnect from Home Assistant."""
        self.connected = False
        if self.websocket:
            await self.websocket.close()
        if self.session:
            await self.session.close()
        logger.info("Disconnected from Home Assistant")
        
    async def send_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a command to Home Assistant and wait for response.
        
        Args:
            command: Command dictionary
            
        Returns:
            Response dictionary
        """
        if not self.connected:
            raise Exception("Not connected to Home Assistant")
        
        async with self._lock:
            command['id'] = self.message_id
            self.message_id += 1
            
            await self.websocket.send_json(command)
            
            # Wait for response with matching ID
            while True:
                msg = await self.websocket.receive_json()
                if msg.get('id') == command['id']:
                    return msg
                
    async def get_states(self) -> List[Dict[str, Any]]:
        """Get all entity states from Home Assistant."""
        response = await self.send_command({
            'type': 'get_states'
        })
        
        if response.get('success'):
            return response.get('result', [])
        return []
        
    async def get_entities_with_label(self, label: str) -> List[Dict[str, Any]]:
        """
        Get all entities that have a specific label.
        
        Args:
            label: Label name to filter by
            
        Returns:
            List of entity states
        """
        # Get all states
        all_states = await self.get_states()
        
        # Filter entities with the specified label
        labeled_entities = []
        for state in all_states:
            entity_id = state.get('entity_id', '')
            # Get entity registry entry
            try:
                registry_response = await self.send_command({
                    'type': 'config/entity_registry/get',
                    'entity_id': entity_id
                })
                
                if registry_response.get('success'):
                    labels = registry_response.get('result', {}).get('labels', [])
                    if label in labels:
                        labeled_entities.append(state)
            except:
                # If entity not in registry, check attributes
                labels = state.get('attributes', {}).get('labels', [])
                if label in labels or label in str(state.get('attributes', {})):
                    labeled_entities.append(state)
                    
        self.entities = {e['entity_id']: e for e in labeled_entities}
        logger.info(f"Found {len(labeled_entities)} entities with label '{label}'")
        return labeled_entities
        
    async def call_service(self, domain: str, service: str, entity_id: str, **kwargs):
        """
        Call a Home Assistant service.
        
        Args:
            domain: Service domain (e.g., 'light', 'switch')
            service: Service name (e.g., 'turn_on', 'turn_off')
            entity_id: Target entity ID
            **kwargs: Additional service data
        """
        service_data = {
            'entity_id': entity_id,
            **kwargs
        }
        
        response = await self.send_command({
            'type': 'call_service',
            'domain': domain,
            'service': service,
            'service_data': service_data
        })
        
        if not response.get('success'):
            logger.error(f"Service call failed: {response}")
            
    async def turn_on(self, entity_id: str, **kwargs):
        """Turn on an entity."""
        domain = entity_id.split('.')[0]
        await self.call_service(domain, 'turn_on', entity_id, **kwargs)
        
    async def turn_off(self, entity_id: str):
        """Turn off an entity."""
        domain = entity_id.split('.')[0]
        await self.call_service(domain, 'turn_off', entity_id)
        
    async def set_brightness(self, entity_id: str, brightness: int):
        """
        Set brightness of a light (0-255).
        
        Args:
            entity_id: Light entity ID
            brightness: Brightness value (0-255)
        """
        await self.turn_on(entity_id, brightness=brightness)
        
    async def set_rgb(self, entity_id: str, r: int, g: int, b: int):
        """
        Set RGB color of a light.
        
        Args:
            entity_id: Light entity ID
            r: Red value (0-255)
            g: Green value (0-255)
            b: Blue value (0-255)
        """
        await self.turn_on(entity_id, rgb_color=[r, g, b])
        
    async def test_connection(self) -> bool:
        """
        Test connection to Home Assistant.
        
        Returns:
            True if connection successful
        """
        try:
            if not self.connected:
                await self.connect()
            states = await self.get_states()
            return len(states) > 0
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
