// Automatically detect if we are running on Azure or Localhost
const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";

// AZURE_URL and API_KEY are loaded from ui/config.js (gitignored). See ui/config.example.js for setup.
const AZURE_URL = window.AZURE_URL || "";
const API_KEY   = window.API_KEY   || "";

// Set API and WebSocket URLs based on environment
const API = isLocal
    ? "http://127.0.0.1:8000"
    : `https://${AZURE_URL}`;

const WS_URL = isLocal
    ? "ws://127.0.0.1:8000"
    : `wss://${AZURE_URL}`;

// Wrapper for fetch that always attaches the API key header.
function apiFetch(url, options = {}) {
    options.headers = { ...(options.headers || {}), "X-API-Key": API_KEY };
    return fetch(url, options);
}

// Track rover path, current position, and active WebSocket connection
let lastPath = [], lastPos = null, ws = null;

// Get latest map and rover data from backend using 'fetch'. 
// 'async' allows to use 'await' while other processes continue without blocking.
async function refresh() {
    try {
        const mRes = await apiFetch(`${API}/map`);
        const mData = await mRes.json();
        const rRes = await apiFetch(`${API}/rovers`);
        const rData = await rRes.json();
        drawMap(mData.width, mData.height, mData.mines);
        drawRovers(rData);
    } catch (e) { console.warn("Backend link severed."); }
}

// Render grid map and mines
function drawMap(w, h, mines) {

    // Get the container element and set up a CSS grid based on map dimensions
    const container = document.getElementById('map-container');
    
    // Set grid dimensions dynamically
    container.style.gridTemplateColumns = `repeat(${w}, 38px)`;
    
    // Clear existing cells before redrawing
    container.innerHTML = '';

    // Go through each cell and create a div element for it. Render the mines. 
    for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
            const cell = document.createElement('div');
            cell.className = 'cell';

            //Check if there's a mine at this coordinate and render it. Also set up click handlers for adding/removing mines.
            const m = mines.find(mine => mine.x === x && mine.y === y);
            if (m) {
                cell.innerText = '💣';                  //Adds text
                cell.classList.add('mine');             //Applies the 'mine' css class to it.
            
                //Listens for clicks on this cell. When clicked, it deletes the mine from the map.
                cell.onclick = () => deleteMine(m.id);  

            } else {
                //Listens for clicks on this cell. When clicked, it adds a mine to the map.
                cell.onclick = () => addMine(x, y);
            }
            
            //Mark the path that has taken place already.
            if (lastPath.some(p => p.x === x && p.y === y)) cell.classList.add('path'), cell.innerText = '★';

            //Highlight the current position of the rover.
            if (lastPos && lastPos.x === x && lastPos.y === y) cell.classList.add('current'), cell.innerText = '🤖';
            container.appendChild(cell);
        }
    }
}

// Render the list of rovers in the sidebar, showing their status and action buttons.
function drawRovers(rovers) {
    const list = document.getElementById('rover-list');

    // Check rover count, and add placeholder if none.
    list.innerHTML = rovers.length ? '' : '<p style="color:var(--text-muted); text-align:center;">No rovers.</p>';
    
    // Create a div for each rover. Call the necessary functions when buttons are clicked.
    rovers.forEach(r => {
        const div = document.createElement('div');
        div.className = `rover-item ${r.status}`;
        div.innerHTML = `
            <div style="display:flex; justify-content:space-between; font-size:0.8rem;">
                <strong>UNIT-${r.id.toString().padStart(3, '0')}</strong>
                <span>${r.status.toUpperCase()}</span>
            </div>
            <div class="btn-group">
                <button class="btn-dispatch" onclick="dispatch(${r.id})">run</button>
                <button class="btn-live" onclick="startLive(${r.id})">real-time</button>  
                <button class="btn-update" style="background:var(--info); color:white; flex:1;" onclick="editRover(${r.id})">edit</button>
                <button class="btn-delete" onclick="deleteRover(${r.id})">🗑️</button>
            </div>
        `;

        // Append the rover div to the list container
        list.appendChild(div);
    });
}

// Send a command to dispatch the rover with the given ID. Update the path and position based on response, and refresh the display.
async function dispatch(id) {
    const res = await apiFetch(`${API}/rovers/${id}/dispatch`, {method:'POST'});
    const data = await res.json();
    lastPath = data.path || [];
    lastPos = data.latest_position || {x: data.x, y: data.y};
    updateLog(data); 
    refresh();
}

// Send a single command over the active WebSocket and flash the matching D-pad button.
function sendCmd(cmd) {
    if (!ws || ws.readyState !== 1) return;
    ws.send(cmd);
    const btn = document.getElementById(`btn-${cmd}`);
    if (btn) {
        btn.classList.remove('pressed');
        void btn.offsetWidth; // force reflow so the animation restarts if pressed rapidly
        btn.classList.add('pressed');
        btn.addEventListener('animationend', () => btn.classList.remove('pressed'), { once: true });
    }
}

// Close the active WebSocket session from the disconnect button.
function disconnectLive() {
    if (ws) ws.close();
}

// Show or hide the live control panel and update its unit label.
function setLivePanel(active, unitId) {
    const panel = document.getElementById('live-panel');
    if (active) {
        document.getElementById('live-unit-label').innerText = `UNIT-${String(unitId).padStart(3, '0')}`;
        panel.classList.remove('hidden');
    } else {
        panel.classList.add('hidden');
    }
}

// Establish a WebSocket connection to receive real-time updates for the rover with the given ID. Update the path, position, and log based on incoming messages.
function startLive(id) {
    if (ws) ws.close();
    ws = new WebSocket(`${WS_URL}/ws/rovers/${id}/control?api_key=${API_KEY}`);
    const ind = document.getElementById('ws-indicator');

    // Run when connection is successfully established
    ws.onopen = () => {
        ind.innerText = `Socket: Active (Unit ${id})`;
        ind.className = "status-on";
        setLivePanel(true, id);
        updateLog({system: "Remote Link Established. Use the D-pad or keyboard to control the rover."});
    };

    // Run when a message is received from the server
    ws.onmessage = (e) => {
        const data = JSON.parse(e.data);

        // If the message contains new coordinates, update the rover's path and current position.
        if (data.x !== undefined) {
            lastPos = {x:data.x, y:data.y};
            lastPath.push({...lastPos});
        }

        // If the rover has been eliminated, close the WebSocket connection.
        if (data.status === "Eliminated") ws.close();

        // Update the log display with the new data and refresh the map and rover list.
        updateLog(data);
        refresh();
    };

    // Run when the WebSocket connection is closed (either by the client or server)
    ws.onclose = () => {
        ind.innerText = "Socket: Offline";
        ind.className = "status-off";
        setLivePanel(false);
        ws = null;
    };
}

// Map keypresses to rover commands and forward them through the active WebSocket.
window.addEventListener("keydown", (e) => {
    if (!ws || ws.readyState !== 1) return;
    const keyMap = { ArrowUp:'M', w:'M', ' ':'M', ArrowLeft:'L', a:'L', ArrowRight:'R', d:'R', f:'D' };
    if (keyMap[e.key]) { sendCmd(keyMap[e.key]); e.preventDefault(); }
});

// Send a request to the server to add a mine at the specified coordinates, then refresh the map display.
async function addMine(x, y) {
    await apiFetch(`${API}/mines`, {method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({x, y, serial_number: "SN-"+Math.floor(Math.random()*9000)})});
    refresh();
}

// Send a request to the server to create a new rover with the specified command sequence, then refresh the rover list display.
async function createRover() {
    const cmds = document.getElementById('new-cmds').value;
    const res = await apiFetch(`${API}/rovers`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({commands: cmds})});
    if (!res.ok) { const err = await res.json(); alert("Error: " + err.detail); return; }
    refresh();
}

// Prompt the user for a new command sequence for the rover with the given ID, send an update request to the server, and refresh the display based on the response.
async function editRover(id) {
    const newCmds = prompt("Enter new command sequence (e.g., LMRM):");
    if (newCmds === null) return;

    const res = await apiFetch(`${API}/rovers/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ commands: newCmds })
    });

    if (res.ok) {
        updateLog({ system: `Rover ${id} updated successfully.` });
        refresh();
    } else {
        const err = await res.json();
        alert("Error: " + err.detail);
    }
}

// Deletion functions for rovers and mines. Send a DELETE request to the server with the specified ID, then refresh the display.
async function deleteRover(id) { await apiFetch(`${API}/rovers/${id}`, {method:'DELETE'}); refresh(); }
async function deleteMine(id) { await apiFetch(`${API}/mines/${id}`, {method:'DELETE'}); refresh(); }

// Send a PUT request to the server with the new map dimensions, then refresh the display to show the updated map.
async function updateConfig() {
    const w = document.getElementById('w-input').value, h = document.getElementById('h-input').value;
    await apiFetch(`${API}/map`, {method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify({width: parseInt(w), height: parseInt(h)})});
    refresh();
}

// Update the log display area with the provided data, formatting it as a JSON string for readability.
function updateLog(d) { document.getElementById('json-display').innerText = "> " + JSON.stringify(d, null, 2); }

refresh();
setInterval(refresh, 5000);