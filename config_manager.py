"""
Configuration Manager Module
Handles .env file reading and writing
"""
import os
from typing import Dict
from dotenv import load_dotenv, set_key, find_dotenv


class ConfigManager:
    """Manages application configuration from .env file."""
    
    DEFAULT_CONFIG = {
        'HA_URL': 'http://homeassistant.local:8123',
        'HA_TOKEN': '',
        'ARTNET_UNIVERSE': '0',
        'ARTNET_BIND_IP': '0.0.0.0',
        'ARTNET_BIND_PORT': '6454',
        'DMX_START_CHANNEL': '1',
    }
    
    def __init__(self, env_file: str = '.env'):
        """
        Initialize configuration manager.
        
        Args:
            env_file: Path to .env file
        """
        self.env_file = env_file
        self._ensure_env_file()
        load_dotenv(self.env_file)
        
    def _ensure_env_file(self):
        """Ensure .env file exists with default values."""
        if not os.path.exists(self.env_file):
            with open(self.env_file, 'w') as f:
                f.write("# Home Assistant Configuration\n")
                f.write(f"HA_URL={self.DEFAULT_CONFIG['HA_URL']}\n")
                f.write(f"HA_TOKEN={self.DEFAULT_CONFIG['HA_TOKEN']}\n\n")
                f.write("# Art-Net Configuration\n")
                f.write(f"ARTNET_UNIVERSE={self.DEFAULT_CONFIG['ARTNET_UNIVERSE']}\n")
                f.write(f"ARTNET_BIND_IP={self.DEFAULT_CONFIG['ARTNET_BIND_IP']}\n")
                f.write(f"ARTNET_BIND_PORT={self.DEFAULT_CONFIG['ARTNET_BIND_PORT']}\n\n")
                f.write("# DMX Configuration\n")
                f.write(f"DMX_START_CHANNEL={self.DEFAULT_CONFIG['DMX_START_CHANNEL']}\n")
                
    def get(self, key: str, default: str = '') -> str:
        """
        Get configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        return os.getenv(key, default)
        
    def get_int(self, key: str, default: int = 0) -> int:
        """
        Get configuration value as integer.
        
        Args:
            key: Configuration key
            default: Default value if key not found or invalid
            
        Returns:
            Configuration value as integer
        """
        try:
            return int(self.get(key, str(default)))
        except ValueError:
            return default
            
    def set(self, key: str, value: str):
        """
        Set configuration value and save to .env file.
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        set_key(self.env_file, key, value)
        # Reload to update environment
        load_dotenv(self.env_file, override=True)
        
    def get_all(self) -> Dict[str, str]:
        """
        Get all configuration values.
        
        Returns:
            Dictionary of all configuration values
        """
        config = {}
        for key in self.DEFAULT_CONFIG.keys():
            config[key] = self.get(key, self.DEFAULT_CONFIG[key])
        return config
        
    def update_all(self, config: Dict[str, str]):
        """
        Update multiple configuration values.
        
        Args:
            config: Dictionary of configuration key-value pairs
        """
        for key, value in config.items():
            if key in self.DEFAULT_CONFIG:
                self.set(key, value)
                
    def get_ha_config(self) -> Dict[str, str]:
        """Get Home Assistant configuration."""
        return {
            'url': self.get('HA_URL', self.DEFAULT_CONFIG['HA_URL']),
            'token': self.get('HA_TOKEN', self.DEFAULT_CONFIG['HA_TOKEN'])
        }
        
    def get_artnet_config(self) -> Dict[str, any]:
        """Get Art-Net configuration."""
        return {
            'universe': self.get_int('ARTNET_UNIVERSE', int(self.DEFAULT_CONFIG['ARTNET_UNIVERSE'])),
            'bind_ip': self.get('ARTNET_BIND_IP', self.DEFAULT_CONFIG['ARTNET_BIND_IP']),
            'port': self.get_int('ARTNET_BIND_PORT', int(self.DEFAULT_CONFIG['ARTNET_BIND_PORT']))
        }
        
    def get_dmx_start_channel(self) -> int:
        """Get DMX start channel."""
        return self.get_int('DMX_START_CHANNEL', int(self.DEFAULT_CONFIG['DMX_START_CHANNEL']))
