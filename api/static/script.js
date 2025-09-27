let ws = null;
let leds = {};
let devicesData = {};
let currentPlayerStatus = {is_playing: false};

window.onload = () => {
    controlPlayer('stop');
    connectWebSocket();
    loadDevices();
    setupEventListeners();
};

function setupEventListeners() {
    document.getElementById("deviceSelector").addEventListener("change", handleDeviceSelection);
    document.getElementById("etalonPatternSelector").addEventListener("change", selectEtalonPattern);
    document.getElementById("measuredCollectionSelector").addEventListener("change", selectMeasuredPattern);

    const dropZone = document.getElementById("dropZone");
    const logFileInput = document.getElementById("logFileInput");

    dropZone.addEventListener("click", () => logFileInput.click());
    logFileInput.addEventListener("change", (e) => {
        if (e.target.files.length) {
            handleLogFileUpload(e.target.files[0]);
        }
    });

    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("drop-zone--over");
    });
    ["dragleave", "dragend"].forEach((type) => {
        dropZone.addEventListener(type, (e) => {
            dropZone.classList.remove("drop-zone--over");
        });
    });
    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        if (e.dataTransfer.files.length) {
            logFileInput.files = e.dataTransfer.files;
            handleLogFileUpload(e.dataTransfer.files[0]);
        }
        dropZone.classList.remove("drop-zone--over");
    });

    document.getElementById("logPatternSelector").addEventListener("change", selectLogPattern);
}

async function handleLogFileUpload(file) {
    const logPatternSelector = document.getElementById("logPatternSelector");
    logPatternSelector.innerHTML = '<option value="">Parsing log file...</option>';
    logPatternSelector.disabled = true;

    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await fetch('/api/v1/parser/upload-log', {
            method: 'POST',
            body: formData,
        });

        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || "Failed to parse file");

        populateLogPatternSelector(result);
        updateStatus(`Log parsed. Found ${result.length} patterns.`, 'connected');

    } catch (error) {
        logPatternSelector.innerHTML = '<option value="">Parsing failed!</option>';
        alert("Error: " + error.message);
    }
}

function populateLogPatternSelector(patterns) {
    const logPatternSelector = document.getElementById("logPatternSelector");
    logPatternSelector.innerHTML = '<option value="">Select a pattern from log...</option>';

    patterns.forEach(pattern => {
        const text = `Pattern #${pattern.index + 1} (${pattern.duration.toFixed(2)}s)`;
        logPatternSelector.add(new Option(text, pattern.index));
    });

    logPatternSelector.disabled = false;
}

async function selectLogPattern() {
    const index = document.getElementById("logPatternSelector").value;
    if (index !== "") {
        try {
            const response = await fetch('/api/v1/parser/select-pattern', {
                method: 'POST',
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({index: parseInt(index)}),
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.detail || "Failed to load pattern");
            updateStatus(result.message, "connected");
        } catch (error) {
            alert("Error: " + error.message);
        }
    }
}

function connectWebSocket() {
    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(`${protocol}//${location.hostname}:${location.port || 8000}/api/v1/ws/led`);
    ws.onopen = () => updateStatus("Connected", "connected");
    ws.onmessage = handleWebSocketMessage;
    ws.onclose = () => {
        updateStatus("Disconnected", "disconnected");
        setTimeout(connectWebSocket, 3000);
    };
    ws.onerror = (error) => {
        updateStatus("Connection Error", "disconnected");
    };
}

function handleWebSocketMessage(event) {
    const data = JSON.parse(event.data);
    if (data.type === "player_update") {
        const oldStatus = currentPlayerStatus.is_playing;
        currentPlayerStatus = data.status;
        updateUIFromState(data.status, data.leds, oldStatus);
    }
}

function formatTime(seconds) {
    const min = Math.floor(seconds / 60);
    const sec = Math.floor(seconds % 60);
    return `${min.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
}

function updateUIFromState(status, newLeds, oldIsPlayingStatus) {
    const playerControls = document.getElementById("playerControls");
    playerControls.classList.toggle("hidden", !status.has_pattern);

    const isPlaying = status.is_playing;
    document.getElementById("playBtn").classList.toggle('playing', isPlaying);

    const timeInfo = `${formatTime(status.current_time)} / ${formatTime(status.total_duration)}`;
    document.getElementById("timeInfo").textContent = timeInfo;

    const slider = document.getElementById("progressSlider");
    slider.max = status.total_duration;
    slider.value = status.current_time;

    updateSliderFill(slider);

    const newLedKeys = Object.keys(newLeds);
    const gridLedKeys = Object.keys(leds);

    if (status.has_pattern && (newLedKeys.length > 0 && JSON.stringify(newLedKeys.sort()) !== JSON.stringify(gridLedKeys.sort()))) {
        createAndPositionLeds(newLeds);
    }

    if (!status.has_pattern) {
        document.getElementById("ledContainer").innerHTML = "";
        leds = {};
    }

    if (isPlaying !== oldIsPlayingStatus) {
        for (const ledId in leds) {
            leds[ledId].classList.toggle('playing', isPlaying);
        }
    }

    updateLEDs(newLeds);
}

function updateSliderFill(slider) {
    const progress = (slider.value / slider.max) * 100;
    slider.style.setProperty('--progress-percent', `${progress}%`);
}

function handleSliderInput(slider) {
    updateSliderFill(slider);
    seekToTime(slider.value);
}

async function loadDevices() {
    try {
        const response = await fetch("/api/v1/devices/");
        if (!response.ok) throw new Error(`HTTP error ${response.status}`);
        devicesData = await response.json();
        const deviceSelector = document.getElementById("deviceSelector");
        deviceSelector.innerHTML = '<option value="">Select a device...</option>';
        for (const deviceName in devicesData) {
            deviceSelector.add(new Option(deviceName, deviceName));
        }
    } catch (error) {
        updateStatus("Failed to load devices", "disconnected");
    }
}

function handleDeviceSelection() {
    const deviceName = document.getElementById("deviceSelector").value;
    const etalonSelector = document.getElementById("etalonPatternSelector");
    const measuredSelector = document.getElementById("measuredCollectionSelector");

    etalonSelector.innerHTML = '<option value="">Select etalon...</option>';
    measuredSelector.innerHTML = '<option value="">Select measured...</option>';
    [etalonSelector, measuredSelector].forEach(
        (el) => (el.disabled = true)
    );

    if (deviceName && devicesData[deviceName]) {
        const device = devicesData[deviceName];
        if (device.measured_collections?.length > 0) {
            device.measured_collections.forEach((c) => measuredSelector.add(new Option(c, c)));
            measuredSelector.disabled = false;
        }
        if (device.etalon_collection) {
            loadEtalonPatterns(deviceName);
        }
    }
}

async function loadEtalonPatterns(deviceName) {
    try {
        const response = await fetch(`/api/v1/devices/${deviceName}/etalon/patterns`);
        if (!response.ok) throw new Error(`HTTP error ${response.status}`);
        const patterns = await response.json();
        const etalonSelector = document.getElementById("etalonPatternSelector");
        patterns.forEach((p) => etalonSelector.add(new Option(p, p)));
        etalonSelector.disabled = false;
    } catch (error) {
        console.error("Error loading etalon patterns:", error);
    }
}

async function selectEtalonPattern() {
    const deviceName = document.getElementById("deviceSelector").value;
    const patternName = document.getElementById("etalonPatternSelector").value;
    if (deviceName && patternName) {
        await loadPattern(`/api/v1/devices/${deviceName}/etalon/select`, {pattern_name: patternName});
    }
}

async function selectMeasuredPattern() {
    const collectionName = document.getElementById("measuredCollectionSelector").value;
    const deviceName = document.getElementById("deviceSelector").value;
    if (deviceName && collectionName) {
        await loadPattern(`/api/v1/devices/${deviceName}/measured/select`, {collection_name: collectionName});
    }
}

async function loadPattern(url, body) {
    try {
        const response = await fetch(url, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(body),
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || "Failed to load pattern");
        updateStatus(result.message, "connected");
    } catch (error) {
        alert("Error: " + error.message);
    }
}

function createAndPositionLeds(ledsData) {
    const ledContainer = document.getElementById("ledContainer");
    ledContainer.innerHTML = "";
    leds = {};

    const ledKeys = Object.keys(ledsData);
    const ledElements = [];

    ledKeys.forEach((ledId) => {
        const ledItem = document.createElement("div");
        ledItem.className = "led-item";
        ledItem.id = `led-item-${ledId}`;
        ledItem.draggable = true;
        ledItem.style.position = 'absolute';

        ledItem.addEventListener("dragstart", handleDragStart);
        ledItem.addEventListener("dragend", handleDragEnd);

        const led = document.createElement("div");
        led.className = "led";
        led.id = `led-${ledId}`;

        const ledInfo = document.createElement("div");
        ledInfo.className = "led-overlay-info";
        ledInfo.innerHTML = `<div class="led-name">${ledId}</div>
                         <div class="led-rgb" id="led-rgb-${ledId}">(0,0,0)</div>`;

        led.append(ledInfo);
        ledItem.append(led);
        ledContainer.append(ledItem);

        leds[ledId] = led;
        ledElements.push(ledItem);
    });

    const N = ledElements.length;
    if (N === 0) return;

    const containerWidth = ledContainer.clientWidth;
    const containerHeight = ledContainer.clientHeight;
    const uniformItemWidth = ledElements[0].offsetWidth;
    const uniformItemHeight = ledElements[0].offsetHeight;

    const totalWidth = Math.ceil(Math.sqrt(N)) * uniformItemWidth;
    const totalHeight = Math.ceil(N / Math.ceil(Math.sqrt(N))) * uniformItemHeight;
    const startX = (containerWidth - totalWidth) / 2;
    const startY = (containerHeight - totalHeight) / 2;

    const itemsPerRow = Math.ceil(Math.sqrt(N));

    ledElements.forEach((ledItem, index) => {
        const row = Math.floor(index / itemsPerRow);
        const col = index % itemsPerRow;

        let xPos = startX + (col * uniformItemWidth);
        let yPos = startY + (row * uniformItemHeight);

        if (row % 2 === 1) {
            xPos = startX + ((itemsPerRow - 1 - col) * uniformItemWidth);
        }

        ledItem.style.left = `${xPos}px`;
        ledItem.style.top = `${yPos}px`;
    });
}

function updateLEDs(updatedLeds) {
    requestAnimationFrame(() => {
        for (const ledId in updatedLeds) {
            const ledElement = leds[ledId];
            if (ledElement) {
                const {r, g, b} = updatedLeds[ledId];
                ledElement.style.setProperty('--led-color', `${r}, ${g}, ${b}`);
                document.getElementById(`led-rgb-${ledId}`).textContent = `(${r},${g},${b})`;
            }
        }
    });
}

async function controlPlayer(action) {
    try {
        await fetch(`/api/v1/player/${action}`, {method: "POST"});
    } catch (e) {
        updateStatus('Connection to server lost. Please reload.', 'disconnected');
    }
}

async function seekToTime(time) {
    try {
        await fetch("/api/v1/player/seek", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({time: parseFloat(time)}),
        });
    } catch (e) {
        updateStatus('Connection to server lost. Please reload.', 'disconnected');
    }
}

function togglePlay() {
    controlPlayer(currentPlayerStatus.is_playing ? 'pause' : 'resume');
}

function stopPlayback() {
    controlPlayer('stop');
}

function updateStatus(message, type) {
    const statusEl = document.getElementById("status");
    if (statusEl) {
        statusEl.textContent = message;
        statusEl.className = `status ${type}`;
    }
}

let draggedElement = null;
let offsetX = 0;
let offsetY = 0;

function handleDragStart(e) {
    draggedElement = e.currentTarget;

    const rect = draggedElement.getBoundingClientRect();
    const containerRect = document.getElementById('ledContainer').getBoundingClientRect();

    offsetX = e.clientX - rect.left;
    offsetY = e.clientY - rect.top;

    draggedElement.style.position = 'absolute';
    draggedElement.style.left = `${rect.left - containerRect.left}px`;
    draggedElement.style.top = `${rect.top - containerRect.top}px`;

    e.dataTransfer.setDragImage(new Image(), 0, 0);

    setTimeout(() => {
        draggedElement.classList.add('dragging');
    }, 0);

    document.addEventListener('dragover', handleDrag);
    document.addEventListener('dragend', handleDragEnd, {once: true});
}

function handleDrag(e) {
    if (!draggedElement) return;
    e.preventDefault();

    const containerRect = document.getElementById('ledContainer').getBoundingClientRect();

    let x = e.clientX - containerRect.left - offsetX;
    let y = e.clientY - containerRect.top - offsetY;

    const minX = 0;
    const maxX = containerRect.width - draggedElement.offsetWidth;
    const minY = 0;
    const maxY = containerRect.height - draggedElement.offsetHeight;

    x = Math.max(minX, Math.min(x, maxX));
    y = Math.max(minY, Math.min(y, maxY));

    draggedElement.style.left = `${x}px`;
    draggedElement.style.top = `${y}px`;
}

function handleDragEnd(e) {
    document.removeEventListener('dragover', handleDrag);
    if (draggedElement) {
        draggedElement.classList.remove('dragging');
    }
    draggedElement = null;
}
