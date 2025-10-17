# 🎭 OrcheStream - Art-Net to Home Assistant Bridge

A powerful Python application that bridges Art-Net DMX protocol to Home Assistant, allowing you to control your smart home devices using professional DMX lighting controllers. Features a beautiful modern web UI built with FastAPI for easy configuration and real-time monitoring.

## ✨ Features

- **🌐 Art-Net DMX Receiver**: Listens for Art-Net packets on your network
- **🏠 Home Assistant Integration**: WebSocket API connection for real-time control with concurrent call protection
- **🔍 Automatic Entity Discovery**: Finds all entities with "orchestream" label
- **🎨 Advanced Entity Types Support**:
  - **Switch**: Simple ON/OFF control (DMX threshold >125)
  - **Dimmer**: Brightness control (0-255)
  - **RGB**: Full color control with 4 channels (Master + R, G, B)
  - **RGBW**: RGB + White with 5 channels (Master + R, G, B, W)
  - **RGBWW**: RGB + Cold/Warm White with 6 channels (Master + R, G, B, CW, WW)
  - **Color Temperature**: Kelvin control (2000-6500K)
- **💅 Modern Web UI**: Beautiful gradient interface with real-time updates
- **⚙️ Manual Configuration**: Full control over entity types and DMX channel assignment
- **📊 Live Status Monitoring**: Real-time Art-Net and Home Assistant connection status
- **🔄 WebSocket Updates**: Instant UI updates via WebSocket connection
- **🎯 Channel Throttling**: Smart command throttling to prevent overwhelming Home Assistant

## Architecture

```
DMX Controller → Art-Net → Bridge Application → WebSocket → Home Assistant → Smart Devices
```

## Installation

### Prerequisites

- Python 3.8 or higher
- Home Assistant instance with WebSocket API enabled
- DMX/Art-Net controller or software (e.g., QLC+, LightKey, etc.)

### Setup

1. **Clone or download this repository**

```bash
cd ola-webhook
```

2. **Install dependencies**

```bash
pip install -r requirements.txt
```

3. **Configure environment variables**

Copy `.env.example` to `.env` and edit with your settings:

```bash
cp .env.example .env
```

Or use the web UI to configure (recommended).

## Configuration

### Home Assistant Setup

1. **Create a Long-Lived Access Token**:
   - In Home Assistant, go to your profile (click your username in bottom left)
   - Scroll down to "Long-Lived Access Tokens"
   - Click "Create Token"
   - Give it a name (e.g., "Art-Net Bridge")
   - Copy the token (you won't be able to see it again!)

2. **Label your entities**:
   - Go to Settings → Devices & Services
   - For each entity you want to control via DMX, add the label "orchestream"
   - The bridge will automatically discover these entities

### Bridge Configuration

You can configure the bridge either via:

1. **Web UI** (recommended):
   - Start the application
   - Click "⚙️ Configure" button
   - Fill in your settings
   - Click "Save Configuration"

2. **Manual .env file editing**:

```env
# Home Assistant Configuration
HA_URL=http://homeassistant.local:8123
HA_TOKEN=your_long_lived_access_token_here

# Art-Net Configuration
ARTNET_UNIVERSE=0
ARTNET_BIND_IP=0.0.0.0
ARTNET_BIND_PORT=6454

# DMX Configuration
DMX_START_CHANNEL=1
```

### Configuration Options

- **HA_URL**: Your Home Assistant URL (include http:// or https://)
- **HA_TOKEN**: Long-lived access token from Home Assistant
- **ARTNET_UNIVERSE**: Art-Net universe to listen to (0-32767)
- **ARTNET_BIND_IP**: IP address to bind to (0.0.0.0 for all interfaces)
- **ARTNET_BIND_PORT**: UDP port for Art-Net (default 6454)
- **DMX_START_CHANNEL**: Starting channel for auto-assignment (default 1)

## 🚀 Usage

### Start the Application

```bash
python app.py
```

Or with uvicorn directly:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

The web interface will be available at `http://localhost:8000`

### 🎨 Using the Web UI

#### 1. **Configure Settings**
   - Click "⚙️ Settings" to open the configuration panel
   - Enter your Home Assistant URL and access token
   - Configure Art-Net settings (universe, IP, port)
   - Set DMX start channel
   - Click "💾 Save Configuration"

#### 2. **Start the Bridge**
   - Click the "▶️ Start Bridge" button
   - The bridge will connect to Home Assistant
   - It will automatically discover entities with "orchestream" label
   - Initial DMX channels will be auto-assigned

#### 3. **Configure Entity Types**
   - In the Entity Mappings table, use the **dropdown** to select entity type:
     - Switch
     - Dimmer
     - RGB
     - RGBW
     - RGBWW
     - Color Temp
   - Set the **Start Channel** for each entity
   - RGB/RGBW/RGBWW channels are **automatically calculated**
   - Changes are **saved immediately**

#### 4. **Monitor Status**
   - **Art-Net**: Shows ONLINE/OFFLINE status
   - **Home Assistant**: Shows CONNECTED/DISCONNECTED status
   - **Entities**: Number of loaded entities
   - Status messages show current operations

#### 5. **View Channel Details**
   - Each entity shows its assigned channels with color-coded badges:
     - 🔵 **Master**: Main brightness/switch channel
     - 🔴 **R**: Red channel
     - 🟢 **G**: Green channel
     - 🔵 **B**: Blue channel
     - ⚪ **W/CW/WW**: White channels

#### 6. **Refresh Entities**
   - Click "🔄 Refresh" to reload entities from Home Assistant
   - Useful after adding new entities or labels

### Controlling Your Devices

Once the bridge is running, send Art-Net DMX data to the configured universe:

#### Switches
- DMX value 0-125: Switch OFF
- DMX value 126-255: Switch ON

#### Dimmers
- DMX value 0: Light OFF
- DMX value 1-255: Brightness level

#### RGB Lights
- Channel X: Master brightness/switch
- Channel X+1: Red (0-255)
- Channel X+2: Green (0-255)
- Channel X+3: Blue (0-255)

#### RGBW Lights
- Channel X: Master brightness/switch
- Channel X+1: Red (0-255)
- Channel X+2: Green (0-255)
- Channel X+3: Blue (0-255)
- Channel X+4: White (0-255)

#### RGBWW Lights
- Channel X: Master brightness/switch
- Channel X+1: Red (0-255)
- Channel X+2: Green (0-255)
- Channel X+3: Blue (0-255)
- Channel X+4: Cold White (0-255)
- Channel X+5: Warm White (0-255)

#### Color Temperature
- Channel X: DMX 0 = 2000K (warm), DMX 255 = 6500K (cool)

## 📊 DMX Channel Assignment

You can manually configure DMX channels for each entity via the web UI:

### Channel Requirements by Type

| Entity Type | Channels | Example (start=1) |
|-------------|----------|-------------------|
| **Switch** | 1 | Ch 1 |
| **Dimmer** | 1 | Ch 1 |
| **RGB** | 4 | Master:1, R:2, G:3, B:4 |
| **RGBW** | 5 | Master:1, R:2, G:3, B:4, W:5 |
| **RGBWW** | 6 | Master:1, R:2, G:3, B:4, CW:5, WW:6 |
| **Color Temp** | 1 | Ch 1 (Kelvin) |

### Example Channel Layout

Configure your entities with custom start channels:
- **Switch 1** → Channel 1
- **Dimmer 1** → Channel 2  
- **RGB Light 1** → Channels 10-13 (10=master, 11=R, 12=G, 13=B)
- **RGBW Light 1** → Channels 20-24 (20=master, 21=R, 22=G, 23=B, 24=W)
- **RGBWW Light 1** → Channels 30-35 (30=master, 31=R, 32=G, 33=B, 34=CW, 35=WW)

## Troubleshooting

### Bridge won't start
- Check Home Assistant URL and token are correct
- Ensure Home Assistant is accessible from the bridge machine
- Verify the token has not expired

### No entities found
- Ensure entities have the "orchestream" label in Home Assistant
- Click "Refresh Entities" after adding labels
- Check Home Assistant logs for API access issues

### Art-Net not receiving
- Verify the correct universe is configured
- Check firewall settings (UDP port 6454)
- Ensure Art-Net controller is sending to the correct IP/universe
- Try binding to 0.0.0.0 to listen on all interfaces

### Entities not responding
- Check entity IDs are correct in the mapping table
- Verify entities are actually controllable in Home Assistant
- Check Home Assistant logs for service call errors
- Ensure DMX values are in valid range (0-255)

## 🙏 Credits

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework for building APIs
- [Uvicorn](https://www.uvicorn.org/) - Lightning-fast ASGI server
- [stupidArtnet](https://github.com/cpvalente/stupidArtnet) - Art-Net protocol handling
- [aiohttp](https://github.com/aio-libs/aiohttp) - Async HTTP client for WebSocket
- [python-dotenv](https://github.com/theskumar/python-dotenv) - Environment configuration

## 📚 Additional Resources

- **API Documentation**: Visit `http://localhost:8000/docs` for interactive Swagger UI
- **Configuration Guide**: See [CONFIGURATION.md](CONFIGURATION.md) for detailed setup
- **Home Assistant Labels**: [Labels Documentation](https://www.home-assistant.io/docs/organizing/labels/)

## 💬 Support

For issues, questions, or contributions, please open an issue on the repository.

## 🎯 Roadmap

- [ ] Support for more entity types (covers, fans, etc.)
- [ ] Scene triggering via DMX
- [ ] Multiple Art-Net universe support
- [ ] DMX output to control non-HA devices
- [ ] Preset configurations for popular DMX controllers

---

**🎭 OrcheStream** - Orchestrate your smart home with professional lighting control protocols! 💡✨

## Development

### Project Structure

```
ola-webhook/
├── app.py                  # FastAPI web application
├── artnet_receiver.py      # Art-Net DMX packet receiver
├── ha_client.py            # Home Assistant WebSocket client (with async lock)
├── entity_mapper.py        # Entity-to-DMX channel mapping logic
├── config_manager.py       # Configuration file handler
├── bridge_controller.py    # Main bridge controller (with throttling)
├── static/                 # Web UI static files
│   ├── index.html         # Main HTML page
│   ├── style.css          # Styles with gradients and animations
│   └── app.js             # Frontend JavaScript
├── requirements.txt        # Python dependencies
├── .env.example           # Example environment configuration
├── entity_mappings.json   # Entity to DMX channel mappings
├── CONFIGURATION.md       # Detailed configuration guide
└── README.md              # This file
```

### 🔧 Extending the Bridge

To add support for new entity types:

1. Add new `EntityType` enum value in `entity_mapper.py`
2. Update the type mapping in `app.py` API endpoint
3. Add conversion logic in `get_entity_commands()` method
4. Update the frontend dropdown in `static/app.js`
5. Add channel calculation logic in `update_mapping()` if needed

### 🎨 Customizing the UI

The web interface uses:
- **Gradient background**: Purple to blue gradient
- **Color-coded badges**: Different colors for each channel type
- **Real-time updates**: WebSocket for instant status changes
- **Responsive design**: Works on desktop and mobile

Edit `static/style.css` to customize colors and layout.

## License

MIT License - Feel free to use and modify as needed.

