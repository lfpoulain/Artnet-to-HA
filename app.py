"""
FastAPI Web Application for Art-Net to Home Assistant Bridge
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
import logging
import json
from pathlib import Path

from bridge_controller import get_bridge
from config_manager import ConfigManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="OrcheStream Bridge",
    description="Art-Net to Home Assistant DMX Bridge",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
bridge = get_bridge()
config = ConfigManager()

# WebSocket connections for live updates
active_connections: List[WebSocket] = []


# Pydantic models
class ConfigUpdate(BaseModel):
    ha_url: str
    ha_token: str
    artnet_universe: int
    artnet_bind_ip: str
    artnet_bind_port: int
    dmx_start_channel: int


class StatusResponse(BaseModel):
    is_running: bool
    artnet_running: bool
    ha_connected: bool
    entities_loaded: int
    status_message: str


class EntityMapping(BaseModel):
    entity_id: str
    name: str
    type: str
    channel: int
    rgb_channels: str


# API Endpoints
@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main HTML page."""
    html_file = Path(__file__).parent / "static" / "index.html"
    if html_file.exists():
        return FileResponse(html_file)
    return HTMLResponse("<h1>OrcheStream Bridge</h1><p>Frontend not found. Please create static/index.html</p>")


@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """Get current bridge status."""
    status = bridge.get_status()
    return StatusResponse(
        is_running=bridge.running,
        artnet_running=status.get('artnet_running', False),
        ha_connected=status.get('ha_connected', False),
        entities_loaded=status.get('entities_loaded', 0),
        status_message="Running" if bridge.running else "Stopped"
    )


@app.post("/api/start")
async def start_bridge():
    """Start the bridge."""
    try:
        if bridge.running:
            raise HTTPException(status_code=400, detail="Bridge already running")
        
        # Set event loop
        loop = asyncio.get_event_loop()
        bridge.set_event_loop(loop)
        
        await bridge.start()
        
        # Notify WebSocket clients
        await broadcast_status()
        
        return {"status": "success", "message": "Bridge started"}
    except Exception as e:
        logger.error(f"Error starting bridge: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stop")
async def stop_bridge():
    """Stop the bridge."""
    try:
        if not bridge.running:
            raise HTTPException(status_code=400, detail="Bridge not running")
        
        await bridge.stop()
        
        # Notify WebSocket clients
        await broadcast_status()
        
        return {"status": "success", "message": "Bridge stopped"}
    except Exception as e:
        logger.error(f"Error stopping bridge: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config")
async def get_config():
    """Get current configuration."""
    return config.get_all()


@app.post("/api/config")
async def update_config(config_data: ConfigUpdate):
    """Update configuration."""
    try:
        config.set('HA_URL', config_data.ha_url)
        config.set('HA_TOKEN', config_data.ha_token)
        config.set('ARTNET_UNIVERSE', str(config_data.artnet_universe))
        config.set('ARTNET_BIND_IP', config_data.artnet_bind_ip)
        config.set('ARTNET_BIND_PORT', str(config_data.artnet_bind_port))
        config.set('DMX_START_CHANNEL', str(config_data.dmx_start_channel))
        
        return {"status": "success", "message": "Configuration saved"}
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/entities", response_model=List[EntityMapping])
async def get_entities():
    """Get entity mappings."""
    try:
        mappings = bridge.get_mappings()
        return [
            EntityMapping(
                entity_id=m.entity_id,
                name=m.name or m.entity_id,
                type=m.entity_type.value,
                channel=m.dmx_channel,
                rgb_channels=', '.join(map(str, m.rgb_channels)) if m.rgb_channels else '-'
            )
            for m in mappings
        ]
    except Exception as e:
        logger.error(f"Error getting entities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/entities/refresh")
async def refresh_entities():
    """Refresh entities from Home Assistant."""
    try:
        if not bridge.running:
            raise HTTPException(status_code=400, detail="Bridge not running")
        
        await bridge.refresh_entities()
        
        # Notify WebSocket clients
        await broadcast_status()
        
        return {"status": "success", "message": "Entities refreshed"}
    except Exception as e:
        logger.error(f"Error refreshing entities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class EntityTypeUpdate(BaseModel):
    entity_type: str
    dmx_channel: int


@app.post("/api/entities/{entity_id}/channel")
async def update_entity_channel(entity_id: str, channel: int):
    """Update DMX channel for an entity."""
    try:
        # Decode entity_id (URL encoded)
        from urllib.parse import unquote
        entity_id = unquote(entity_id)
        
        mapper = bridge.mapper
        if entity_id not in mapper.mappings:
            raise HTTPException(status_code=404, detail="Entity not found")
        
        mapper.update_mapping(entity_id, channel)
        
        return {"status": "success", "message": f"Channel updated to {channel}"}
    except Exception as e:
        logger.error(f"Error updating channel: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/entities/{entity_id}/type")
async def update_entity_type(entity_id: str, update: EntityTypeUpdate):
    """Update entity type and channel."""
    try:
        # Decode entity_id (URL encoded)
        from urllib.parse import unquote
        from entity_mapper import EntityType
        
        entity_id = unquote(entity_id)
        mapper = bridge.mapper
        
        # Convert string to EntityType
        type_map = {
            'switch': EntityType.SWITCH,
            'dimmer': EntityType.DIMMER,
            'rgb': EntityType.RGB,
            'rgbw': EntityType.RGBW,
            'rgbww': EntityType.RGBWW,
            'color_temp': EntityType.COLOR_TEMP
        }
        
        entity_type = type_map.get(update.entity_type.lower())
        if not entity_type:
            raise HTTPException(status_code=400, detail=f"Invalid entity type: {update.entity_type}")
        mapper.update_mapping(entity_id, update.dmx_channel, entity_type)
        
        return {"status": "success", "message": f"Entity type updated to {update.entity_type}"}
    except Exception as e:
        logger.error(f"Error updating entity type: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for live updates."""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        # Send initial status
        status = bridge.get_status()
        await websocket.send_json({
            "type": "status",
            "data": {
                "is_running": bridge.running,
                "artnet_running": status.get('artnet_running', False),
                "ha_connected": status.get('ha_connected', False),
                "entities_loaded": status.get('entities_loaded', 0)
            }
        })
        
        # Keep connection alive
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)


async def broadcast_status():
    """Broadcast status update to all connected WebSocket clients."""
    if not active_connections:
        return
    
    status = bridge.get_status()
    message = {
        "type": "status",
        "data": {
            "is_running": bridge.running,
            "artnet_running": status.get('artnet_running', False),
            "ha_connected": status.get('ha_connected', False),
            "entities_loaded": status.get('entities_loaded', 0)
        }
    }
    
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except:
            pass


# Mount static files
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
