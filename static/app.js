// WebSocket connection
let ws = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadConfig();
    loadStatus();
    loadEntities();
    connectWebSocket();
});

// WebSocket connection
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        console.log('WebSocket connected');
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'status') {
            updateStatusUI(data.data);
        }
    };
    
    ws.onclose = () => {
        console.log('WebSocket disconnected, reconnecting...');
        setTimeout(connectWebSocket, 3000);
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
}

// Load configuration
async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        const config = await response.json();
        
        document.getElementById('haUrl').value = config.HA_URL || '';
        document.getElementById('haToken').value = config.HA_TOKEN || '';
        document.getElementById('artnetUniverse').value = config.ARTNET_UNIVERSE || '0';
        document.getElementById('artnetBindIp').value = config.ARTNET_BIND_IP || '0.0.0.0';
        document.getElementById('artnetPort').value = config.ARTNET_BIND_PORT || '6454';
        document.getElementById('dmxStartChannel').value = config.DMX_START_CHANNEL || '1';
    } catch (error) {
        console.error('Error loading config:', error);
    }
}

// Save configuration
async function saveConfig() {
    const config = {
        ha_url: document.getElementById('haUrl').value,
        ha_token: document.getElementById('haToken').value,
        artnet_universe: parseInt(document.getElementById('artnetUniverse').value),
        artnet_bind_ip: document.getElementById('artnetBindIp').value,
        artnet_bind_port: parseInt(document.getElementById('artnetPort').value),
        dmx_start_channel: parseInt(document.getElementById('dmxStartChannel').value)
    };
    
    try {
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage('Configuration saved successfully!', 'success');
            toggleConfig();
        } else {
            showMessage('Error saving configuration: ' + result.detail, 'error');
        }
    } catch (error) {
        console.error('Error saving config:', error);
        showMessage('Error saving configuration', 'error');
    }
}

// Load status
async function loadStatus() {
    try {
        const response = await fetch('/api/status');
        const status = await response.json();
        updateStatusUI(status);
    } catch (error) {
        console.error('Error loading status:', error);
    }
}

// Update status UI
function updateStatusUI(status) {
    // Update badges
    const artnetBadge = document.getElementById('artnetBadge');
    const haBadge = document.getElementById('haBadge');
    const entitiesBadge = document.getElementById('entitiesBadge');
    
    if (status.artnet_running) {
        artnetBadge.textContent = 'ONLINE';
        artnetBadge.className = 'badge badge-online';
    } else {
        artnetBadge.textContent = 'OFFLINE';
        artnetBadge.className = 'badge badge-offline';
    }
    
    if (status.ha_connected) {
        haBadge.textContent = 'CONNECTED';
        haBadge.className = 'badge badge-online';
    } else {
        haBadge.textContent = 'DISCONNECTED';
        haBadge.className = 'badge badge-offline';
    }
    
    entitiesBadge.textContent = status.entities_loaded || 0;
    
    // Update status message
    document.getElementById('statusMessage').textContent = status.status_message || 'Ready';
    
    // Update buttons
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const refreshBtn = document.getElementById('refreshBtn');
    
    if (status.is_running) {
        startBtn.style.display = 'none';
        stopBtn.style.display = 'inline-flex';
        refreshBtn.disabled = false;
    } else {
        startBtn.style.display = 'inline-flex';
        stopBtn.style.display = 'none';
        refreshBtn.disabled = true;
    }
}

// Start bridge
async function startBridge() {
    try {
        const response = await fetch('/api/start', { method: 'POST' });
        const result = await response.json();
        
        if (response.ok) {
            showMessage('Bridge started successfully!', 'success');
            await loadStatus();
            await loadEntities();
        } else {
            showMessage('Error starting bridge: ' + result.detail, 'error');
        }
    } catch (error) {
        console.error('Error starting bridge:', error);
        showMessage('Error starting bridge', 'error');
    }
}

// Stop bridge
async function stopBridge() {
    try {
        const response = await fetch('/api/stop', { method: 'POST' });
        const result = await response.json();
        
        if (response.ok) {
            showMessage('Bridge stopped successfully!', 'success');
            await loadStatus();
        } else {
            showMessage('Error stopping bridge: ' + result.detail, 'error');
        }
    } catch (error) {
        console.error('Error stopping bridge:', error);
        showMessage('Error stopping bridge', 'error');
    }
}

// Load entities
async function loadEntities() {
    try {
        const response = await fetch('/api/entities');
        const entities = await response.json();
        
        const content = document.getElementById('entitiesContent');
        
        if (entities.length === 0) {
            content.innerHTML = `
                <div class="empty-state">
                    <span class="empty-icon">📭</span>
                    <h3>No entities loaded yet</h3>
                    <p>Start the bridge to load entities with 'orchestream' label</p>
                </div>
            `;
        } else {
            content.innerHTML = `
                <table class="entities-table">
                    <thead>
                        <tr>
                            <th>Entity ID</th>
                            <th>Name</th>
                            <th>Type</th>
                            <th>Start Channel</th>
                            <th>Channel Details</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${entities.map(entity => `
                            <tr>
                                <td><span class="entity-id">${entity.entity_id}</span></td>
                                <td><strong>${entity.name}</strong></td>
                                <td>
                                    <select 
                                        class="type-select" 
                                        id="type-${entity.entity_id}"
                                        onchange="updateEntityType('${entity.entity_id}', this.value, document.getElementById('channel-${entity.entity_id}').value)"
                                    >
                                        <option value="switch" ${entity.type === 'switch' ? 'selected' : ''}>Switch</option>
                                        <option value="dimmer" ${entity.type === 'dimmer' ? 'selected' : ''}>Dimmer</option>
                                        <option value="rgb" ${entity.type === 'rgb' ? 'selected' : ''}>RGB</option>
                                        <option value="rgbw" ${entity.type === 'rgbw' ? 'selected' : ''}>RGBW</option>
                                        <option value="rgbww" ${entity.type === 'rgbww' ? 'selected' : ''}>RGBWW</option>
                                        <option value="color_temp" ${entity.type === 'color_temp' ? 'selected' : ''}>Color Temp</option>
                                    </select>
                                </td>
                                <td>
                                    <div class="channel-control">
                                        <input 
                                            type="number" 
                                            class="channel-input" 
                                            id="channel-${entity.entity_id}" 
                                            value="${entity.channel}" 
                                            min="1" 
                                            max="512"
                                            onchange="updateChannel('${entity.entity_id}', this.value)"
                                        />
                                    </div>
                                </td>
                                <td>
                                    <div class="channel-details">
                                        ${getChannelDetails(entity)}
                                    </div>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        }
    } catch (error) {
        console.error('Error loading entities:', error);
    }
}

// Get channel details for entity
function getChannelDetails(entity) {
    if (entity.type === 'switch' || entity.type === 'dimmer') {
        return `<span class="channel-badge">Ch ${entity.channel}</span>`;
    } else if (entity.type === 'color_temp') {
        return `<span class="channel-badge">Ch ${entity.channel} (Kelvin)</span>`;
    } else if (entity.type === 'rgb') {
        const channels = entity.rgb_channels.split(', ');
        return `
            <div class="channel-list">
                <span class="channel-badge channel-master">Master: ${entity.channel}</span>
                <span class="channel-badge channel-r">R: ${channels[0]}</span>
                <span class="channel-badge channel-g">G: ${channels[1]}</span>
                <span class="channel-badge channel-b">B: ${channels[2]}</span>
            </div>
        `;
    } else if (entity.type === 'rgbw') {
        const channels = entity.rgb_channels.split(', ');
        return `
            <div class="channel-list">
                <span class="channel-badge channel-master">Master: ${entity.channel}</span>
                <span class="channel-badge channel-r">R: ${channels[0]}</span>
                <span class="channel-badge channel-g">G: ${channels[1]}</span>
                <span class="channel-badge channel-b">B: ${channels[2]}</span>
                <span class="channel-badge channel-w">W: ${channels[3]}</span>
            </div>
        `;
    } else if (entity.type === 'rgbww') {
        const channels = entity.rgb_channels.split(', ');
        return `
            <div class="channel-list">
                <span class="channel-badge channel-master">Master: ${entity.channel}</span>
                <span class="channel-badge channel-r">R: ${channels[0]}</span>
                <span class="channel-badge channel-g">G: ${channels[1]}</span>
                <span class="channel-badge channel-b">B: ${channels[2]}</span>
                <span class="channel-badge channel-w">CW: ${channels[3]}</span>
                <span class="channel-badge channel-w">WW: ${channels[4]}</span>
            </div>
        `;
    }
    return '';
}

// Update entity type
async function updateEntityType(entityId, type, channel) {
    try {
        const response = await fetch(`/api/entities/${encodeURIComponent(entityId)}/type`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                entity_type: type,
                dmx_channel: parseInt(channel)
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage(`Type updated to ${type.toUpperCase()}`, 'success');
            await loadEntities();
        } else {
            showMessage('Error updating type: ' + result.detail, 'error');
        }
    } catch (error) {
        console.error('Error updating type:', error);
        showMessage('Error updating type', 'error');
    }
}

// Update entity channel
async function updateChannel(entityId, channel) {
    try {
        const response = await fetch(`/api/entities/${encodeURIComponent(entityId)}/channel?channel=${channel}`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage(`Channel updated to ${channel}`, 'success');
            await loadEntities();
        } else {
            showMessage('Error updating channel: ' + result.detail, 'error');
        }
    } catch (error) {
        console.error('Error updating channel:', error);
        showMessage('Error updating channel', 'error');
    }
}

// Refresh entities
async function refreshEntities() {
    try {
        const response = await fetch('/api/entities/refresh', { method: 'POST' });
        const result = await response.json();
        
        if (response.ok) {
            showMessage('Entities refreshed successfully!', 'success');
            await loadEntities();
            await loadStatus();
        } else {
            showMessage('Error refreshing entities: ' + result.detail, 'error');
        }
    } catch (error) {
        console.error('Error refreshing entities:', error);
        showMessage('Error refreshing entities', 'error');
    }
}

// Toggle configuration panel
function toggleConfig() {
    const configCard = document.getElementById('configCard');
    if (configCard.style.display === 'none') {
        configCard.style.display = 'block';
        loadConfig();
    } else {
        configCard.style.display = 'none';
    }
}

// Show message
function showMessage(message, type) {
    const statusMessage = document.getElementById('statusMessage');
    statusMessage.textContent = message;
    statusMessage.style.color = type === 'success' ? '#10b981' : '#ef4444';
    
    setTimeout(() => {
        statusMessage.style.color = '#6b7280';
    }, 3000);
}
