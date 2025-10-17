"""
Entity Mapping and DMX Conversion Module
Maps Home Assistant entities to DMX channels and handles value conversion
"""
import json
import logging
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class EntityType(Enum):
    """Types of entities we can control."""
    SWITCH = "switch"
    DIMMER = "dimmer"
    RGB = "rgb"
    RGBW = "rgbw"
    RGBWW = "rgbww"
    COLOR_TEMP = "color_temp"
    UNKNOWN = "unknown"


@dataclass
class EntityMapping:
    """Mapping configuration for a single entity."""
    entity_id: str
    entity_type: EntityType
    dmx_channel: int
    name: str = ""
    rgb_channels: List[int] = None  # For RGB/RGBW: [R, G, B] or [R, G, B, W]
    
    def __post_init__(self):
        if self.rgb_channels is None:
            self.rgb_channels = []
            
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'entity_id': self.entity_id,
            'entity_type': self.entity_type.value,
            'dmx_channel': self.dmx_channel,
            'name': self.name,
            'rgb_channels': self.rgb_channels
        }
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'EntityMapping':
        """Create from dictionary."""
        data['entity_type'] = EntityType(data['entity_type'])
        return cls(**data)


class EntityMapper:
    """Manages entity-to-DMX channel mappings and conversions."""
    
    SWITCH_THRESHOLD = 125  # DMX value above which switch turns on
    
    def __init__(self, config_file: str = 'entity_mappings.json'):
        """
        Initialize entity mapper.
        
        Args:
            config_file: Path to JSON file storing mappings
        """
        self.config_file = config_file
        self.mappings: Dict[str, EntityMapping] = {}
        self.channel_to_entity: Dict[int, str] = {}
        self.load_mappings()
        
    def load_mappings(self):
        """Load mappings from JSON file."""
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                self.mappings = {
                    entity_id: EntityMapping.from_dict(mapping)
                    for entity_id, mapping in data.items()
                }
                self._rebuild_channel_index()
                logger.info(f"Loaded {len(self.mappings)} entity mappings")
        except FileNotFoundError:
            logger.info("No existing mappings file found")
        except Exception as e:
            logger.error(f"Error loading mappings: {e}")
            
    def save_mappings(self):
        """Save mappings to JSON file."""
        try:
            data = {
                entity_id: mapping.to_dict()
                for entity_id, mapping in self.mappings.items()
            }
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.mappings)} entity mappings")
        except Exception as e:
            logger.error(f"Error saving mappings: {e}")
            
    def _rebuild_channel_index(self):
        """Rebuild the channel-to-entity index."""
        self.channel_to_entity = {}
        for entity_id, mapping in self.mappings.items():
            self.channel_to_entity[mapping.dmx_channel] = entity_id
            # Also index RGB channels
            for channel in mapping.rgb_channels:
                self.channel_to_entity[channel] = entity_id
                
    def detect_entity_type(self, entity_state: Dict[str, Any]) -> EntityType:
        """
        Detect entity type from its state.
        
        Args:
            entity_state: Entity state dictionary from Home Assistant
            
        Returns:
            Detected entity type
        """
        entity_id = entity_state.get('entity_id', '')
        attributes = entity_state.get('attributes', {})
        
        # Check domain
        domain = entity_id.split('.')[0]
        
        if domain == 'switch':
            return EntityType.SWITCH
            
        if domain == 'light':
            supported_features = attributes.get('supported_color_modes', [])
            
            # Check for RGB/RGBW support
            if 'rgbw' in supported_features or 'rgbww' in supported_features:
                return EntityType.RGBW
            if 'rgb' in supported_features or 'hs' in supported_features:
                return EntityType.RGB
            if 'brightness' in supported_features:
                return EntityType.DIMMER
                
            # Fallback: check if brightness attribute exists
            if 'brightness' in attributes:
                return EntityType.DIMMER
                
            return EntityType.SWITCH
            
        return EntityType.UNKNOWN
        
    def auto_assign_channels(self, entities: List[Dict[str, Any]], start_channel: int = 1):
        """
        Automatically assign DMX channels to entities.
        
        Args:
            entities: List of entity states from Home Assistant
            start_channel: Starting DMX channel number
        """
        current_channel = start_channel
        
        for entity_state in entities:
            entity_id = entity_state.get('entity_id')
            if entity_id in self.mappings:
                continue  # Skip already mapped entities
                
            entity_type = self.detect_entity_type(entity_state)
            name = entity_state.get('attributes', {}).get('friendly_name', entity_id)
            
            if entity_type == EntityType.RGB:
                # RGB needs 3 consecutive channels
                rgb_channels = [current_channel + 1, current_channel + 2, current_channel + 3]
                mapping = EntityMapping(
                    entity_id=entity_id,
                    entity_type=entity_type,
                    dmx_channel=current_channel,  # Master dimmer/switch
                    name=name,
                    rgb_channels=rgb_channels
                )
                current_channel += 4  # Master + R + G + B
                
            elif entity_type == EntityType.RGBW:
                # RGBW needs 4 consecutive channels
                rgb_channels = [current_channel + 1, current_channel + 2, current_channel + 3, current_channel + 4]
                mapping = EntityMapping(
                    entity_id=entity_id,
                    entity_type=entity_type,
                    dmx_channel=current_channel,  # Master dimmer/switch
                    name=name,
                    rgb_channels=rgb_channels
                )
                current_channel += 5  # Master + R + G + B + W
                
            else:
                # Switch or dimmer needs 1 channel
                mapping = EntityMapping(
                    entity_id=entity_id,
                    entity_type=entity_type,
                    dmx_channel=current_channel,
                    name=name
                )
                current_channel += 1
                
            self.mappings[entity_id] = mapping
            logger.info(f"Auto-assigned {entity_id} ({entity_type.value}) to channel {mapping.dmx_channel}")
            
        self._rebuild_channel_index()
        self.save_mappings()
        
    def update_mapping(self, entity_id: str, dmx_channel: int, entity_type: EntityType = None):
        """
        Update or create a mapping for an entity.
        
        Args:
            entity_id: Entity ID
            dmx_channel: DMX channel to assign
            entity_type: Optional entity type override
        """
        if entity_id in self.mappings:
            mapping = self.mappings[entity_id]
            old_channel = mapping.dmx_channel
            mapping.dmx_channel = dmx_channel
            
            # Update RGB channels if entity is RGB/RGBW/RGBWW
            if mapping.entity_type == EntityType.RGB:
                mapping.rgb_channels = [dmx_channel + 1, dmx_channel + 2, dmx_channel + 3]
            elif mapping.entity_type == EntityType.RGBW:
                mapping.rgb_channels = [dmx_channel + 1, dmx_channel + 2, dmx_channel + 3, dmx_channel + 4]
            elif mapping.entity_type == EntityType.RGBWW:
                mapping.rgb_channels = [dmx_channel + 1, dmx_channel + 2, dmx_channel + 3, dmx_channel + 4, dmx_channel + 5]
            
            if entity_type:
                mapping.entity_type = entity_type
                # Update RGB channels based on new type
                if entity_type == EntityType.RGB:
                    mapping.rgb_channels = [dmx_channel + 1, dmx_channel + 2, dmx_channel + 3]
                elif entity_type == EntityType.RGBW:
                    mapping.rgb_channels = [dmx_channel + 1, dmx_channel + 2, dmx_channel + 3, dmx_channel + 4]
                elif entity_type == EntityType.RGBWW:
                    mapping.rgb_channels = [dmx_channel + 1, dmx_channel + 2, dmx_channel + 3, dmx_channel + 4, dmx_channel + 5]
                else:
                    mapping.rgb_channels = []
        else:
            mapping = EntityMapping(
                entity_id=entity_id,
                entity_type=entity_type or EntityType.UNKNOWN,
                dmx_channel=dmx_channel
            )
            self.mappings[entity_id] = mapping
            
        self._rebuild_channel_index()
        self.save_mappings()
        
    def remove_mapping(self, entity_id: str):
        """Remove a mapping."""
        if entity_id in self.mappings:
            del self.mappings[entity_id]
            self._rebuild_channel_index()
            self.save_mappings()
            
    def get_all_mappings(self) -> List[EntityMapping]:
        """Get all current mappings."""
        return list(self.mappings.values())
        
    def dmx_to_ha_switch(self, dmx_value: int) -> bool:
        """
        Convert DMX value to switch state.
        
        Args:
            dmx_value: DMX value (0-255)
            
        Returns:
            True for ON, False for OFF
        """
        return dmx_value > self.SWITCH_THRESHOLD
        
    def dmx_to_ha_brightness(self, dmx_value: int) -> int:
        """
        Convert DMX value to Home Assistant brightness.
        
        Args:
            dmx_value: DMX value (0-255)
            
        Returns:
            HA brightness value (0-255)
        """
        return dmx_value
        
    def get_entity_commands(self, dmx_data: Dict[int, int]) -> List[Dict[str, Any]]:
        """
        Convert DMX channel data to Home Assistant commands.
        
        Args:
            dmx_data: Dictionary of {channel: value}
            
        Returns:
            List of command dictionaries
        """
        commands = []
        processed_entities = set()
        
        for mapping in self.mappings.values():
            if mapping.entity_id in processed_entities:
                continue
                
            entity_id = mapping.entity_id
            dmx_channel = mapping.dmx_channel
            
            if dmx_channel not in dmx_data:
                continue
                
            dmx_value = dmx_data[dmx_channel]
            
            if mapping.entity_type == EntityType.SWITCH:
                # Switch: ON if > threshold, OFF otherwise
                should_be_on = self.dmx_to_ha_switch(dmx_value)
                commands.append({
                    'entity_id': entity_id,
                    'action': 'turn_on' if should_be_on else 'turn_off'
                })
                
            elif mapping.entity_type == EntityType.DIMMER:
                # Dimmer: Map DMX value to brightness
                brightness = self.dmx_to_ha_brightness(dmx_value)
                if brightness > 0:
                    commands.append({
                        'entity_id': entity_id,
                        'action': 'turn_on',
                        'brightness': brightness
                    })
                else:
                    commands.append({
                        'entity_id': entity_id,
                        'action': 'turn_off'
                    })
                    
            elif mapping.entity_type == EntityType.COLOR_TEMP:
                # Color Temperature: Map DMX value to kelvin (2000-6500K)
                brightness = self.dmx_to_ha_brightness(dmx_value)
                if brightness > 0:
                    # Map 0-255 to 2000-6500K
                    kelvin = int(2000 + (dmx_value / 255.0) * 4500)
                    commands.append({
                        'entity_id': entity_id,
                        'action': 'turn_on',
                        'brightness': brightness,
                        'kelvin': kelvin
                    })
                else:
                    commands.append({
                        'entity_id': entity_id,
                        'action': 'turn_off'
                    })
                    
            elif mapping.entity_type in [EntityType.RGB, EntityType.RGBW, EntityType.RGBWW]:
                # RGB/RGBW/RGBWW: Get color values from assigned channels
                brightness = self.dmx_to_ha_brightness(dmx_value)
                
                if len(mapping.rgb_channels) >= 3:
                    r = dmx_data.get(mapping.rgb_channels[0], 0)
                    g = dmx_data.get(mapping.rgb_channels[1], 0)
                    b = dmx_data.get(mapping.rgb_channels[2], 0)
                    
                    if brightness > 0:
                        command = {
                            'entity_id': entity_id,
                            'action': 'turn_on',
                            'brightness': brightness
                        }
                        
                        # Add color based on type
                        if mapping.entity_type == EntityType.RGBW and len(mapping.rgb_channels) >= 4:
                            # RGBW: Use rgbw_color parameter
                            w = dmx_data.get(mapping.rgb_channels[3], 0)
                            command['rgbw_color'] = [r, g, b, w]
                        elif mapping.entity_type == EntityType.RGBWW and len(mapping.rgb_channels) >= 5:
                            # RGBWW: Use rgbww_color parameter (R, G, B, CW, WW)
                            cw = dmx_data.get(mapping.rgb_channels[3], 0)
                            ww = dmx_data.get(mapping.rgb_channels[4], 0)
                            command['rgbww_color'] = [r, g, b, cw, ww]
                        else:
                            # RGB: Use rgb_color parameter
                            command['rgb_color'] = [r, g, b]
                            
                        commands.append(command)
                    else:
                        commands.append({
                            'entity_id': entity_id,
                            'action': 'turn_off'
                        })
                        
            processed_entities.add(entity_id)
            
        return commands
