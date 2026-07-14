let ws = null;
let leds = {};
let devicesData = {};
let currentPlayerStatus = {is_playing: false};
let ledPositions = {};

window.onload = () => {
    const modal = document.getElementById("plot-modal");
    const span = document.getElementsByClassName("close")[0];
    span.onclick = function () {
        modal.style.display = "none";
    }
    modal.addEventListener('click', (event) => {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    });
    setupDropZone("split-drop-zone", "split-input-files", "split-file-list", true);
    setupDropZone("source-drop-zone", "source-log-file", "source-file-list", false);
    setupDropZone("compare-log-drop-zone", "compare-log-file", "compare-log-file-list", false, (files) => {
        if (files.length) {
            const file = files[0];
            const logPatternSelector = document.getElementById("compare-log-pattern");
            const spinner = document.getElementById("compare-log-spinner");
            spinner.style.display = "flex";
            logPatternSelector.innerHTML = '<option value="">Parsing log file...</option>';
            logPatternSelector.disabled = true;
            const formData = new FormData();
            formData.append("file", file);
            fetch('/api/v1/parser/upload-log', {
                method: 'POST', body: formData,
            })
                .then(response => {
                    if (!response.ok) {
                        return response.text().then(text => {
                            throw new Error(text)
                        });
                    }
                    return response.json();
                })
                .then(result => {
                    populateLogPatternSelector(result, "compare-log-pattern");
                    updateStatus(`Log parsed. Found ${result.length} patterns.`, 'connected');
                })
                .catch(error => {
                    logPatternSelector.innerHTML = '<option value="">Parsing failed!</option>';
                    alert("Error: " + error.message);
                })
                .finally(() => {
                    spinner.style.display = "none";
                });
        }
    });

    setupDropZone("palette-drop-zone", "param-palette-file", null, false, (files) => {
        if (files.length > 0) {
            const file = files[0];
            const reader = new FileReader();
            reader.onload = (event) => {
                const content = event.target.result;
                document.getElementById('param-palette-text').value = content;
                document.getElementById('param-palette').value = content;
            };
            reader.readAsText(file);
        }
    });

    const savedPositions = localStorage.getItem('savedLedPositions');
    if (savedPositions) {
        ledPositions = JSON.parse(savedPositions);
    }
    connectWebSocket();
    loadDevices();
    setupEventListeners();
    setupPlayerControls();
    setupFormEventListeners();
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

    document.getElementById("compare-measured-collection").addEventListener("change", async (e) => {
        const collectionName = e.target.value;
        const recordSelector = document.getElementById("compare-measured-record");
        recordSelector.innerHTML = '<option value="">Loading records...</option>';
        recordSelector.disabled = true;

        if (collectionName) {
            try {
                const response = await fetch(`/api/v1/measured/${collectionName}/records`);
                if (!response.ok) throw new Error(`HTTP error ${response.status}`);
                const records = await response.json();
                recordSelector.innerHTML = '<option value="">Select a record...</option>';
                records.forEach((r, i) => recordSelector.add(new Option(`${i + 1} (${r})`, r)));
                recordSelector.disabled = false;
            } catch (error) {
                console.error("Error loading measured records:", error);
                recordSelector.innerHTML = '<option value="">Failed to load records</option>';
            }
        }
    });

    document.getElementById('source-type').addEventListener('change', (e) => {
        const sourceType = e.target.value;
        if (sourceType === 'log') {
            document.getElementById('source-log-fields').style.display = 'block';
            document.getElementById('source-db-fields').style.display = 'none';
        } else {
            document.getElementById('source-log-fields').style.display = 'none';
            document.getElementById('source-db-fields').style.display = 'block';
        }
    });

    const generationModeSelector = document.getElementById('param-generation-mode');
    const simpleParamsContainer = document.getElementById('simple-params-container');
    const paletteParamsContainer = document.getElementById('palette-params-container');
    const paletteTextInput = document.getElementById('param-palette-text');
    const hiddenPaletteInput = document.getElementById('param-palette');

    let simpleParamsCache = {};

    generationModeSelector.addEventListener('change', (e) => {
        if (e.target.value === 'simple') {
            simpleParamsContainer.style.display = 'block';
            paletteParamsContainer.style.display = 'none';
            hiddenPaletteInput.value = '';

            if (simpleParamsCache.numLeds !== undefined) {
                document.getElementById('param-num-leds').value = simpleParamsCache.numLeds;
                document.getElementById('param-color').value = simpleParamsCache.color;
                document.getElementById('param-fade').value = simpleParamsCache.fade;
                document.getElementById('param-sequence').value = simpleParamsCache.sequence;
            }
        } else {
            simpleParamsCache = {
                numLeds: document.getElementById('param-num-leds').value,
                color: document.getElementById('param-color').value,
                fade: document.getElementById('param-fade').value,
                sequence: document.getElementById('param-sequence').value
            };

            simpleParamsContainer.style.display = 'none';
            paletteParamsContainer.style.display = 'block';
        }
    });

    paletteTextInput.addEventListener('input', (e) => {
        hiddenPaletteInput.value = e.target.value;
    });

    setupOutputTypeSwitcher('param-output-type', 'param-output-target');
    setupOutputTypeSwitcher('source-output-type', 'source-output-target');
}

async function handleLogFileUpload(file) {
    const logPatternSelector = document.getElementById("logPatternSelector");
    logPatternSelector.innerHTML = '<option value="">Parsing log file...</option>';
    logPatternSelector.disabled = true;
    const formData = new FormData();
    formData.append("file", file);
    try {
        const response = await fetch('/api/v1/parser/upload-log', {
            method: 'POST', body: formData,
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || "Failed to parse file");
        populateLogPatternSelector(result, "logPatternSelector");
        updateStatus(`Log parsed. Found ${result.length} patterns.`, 'connected');
    } catch (error) {
        logPatternSelector.innerHTML = '<option value="">Parsing failed!</option>';
        alert("Error: " + error.message);
    }
}

function populateLogPatternSelector(patterns, selectorId) {
    const logPatternSelector = document.getElementById(selectorId);
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
    const port = location.port || (location.protocol === "http:" ? 80 : 443);
    const usePort = location.port ? `:${location.port}` : (port !== (location.protocol === "http:" ? 80 : 443) ? `:${port}` : "");
    const wsUrl = `${protocol}//${location.hostname}${usePort}/api/v1/ws/led`;
    const ws = new WebSocket(wsUrl);
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

function updateUIFromState(status, newLeds, oldIsPlayingStatus) {
    const playerWrapper = document.getElementById("player-wrapper");
    if (status.has_pattern) {
        if (playerWrapper.classList.contains('hidden')) {
            playerWrapper.classList.remove('collapsed');
            playerWrapper.classList.add('expanded');
        }
        playerWrapper.classList.remove('hidden');
    } else {
        playerWrapper.classList.add('hidden');
    }
    const isPlaying = status.is_playing;
    document.getElementById("playBtn").classList.toggle('playing', isPlaying);
    const timeInfo = `${formatTime(status.current_time)} / ${formatTime(status.total_duration)}`;
    document.getElementById("timeInfo").textContent = timeInfo;
    const slider = document.getElementById("progressSlider");
    slider.max = status.total_duration;
    slider.value = status.current_time;
    updateSliderFill(slider);
    const newLedKeys = Object.keys(newLeds);
    const currentLedKeys = Object.keys(leds);
    if (status.has_pattern && (newLedKeys.length > 0 && JSON.stringify(newLedKeys.sort()) !== JSON.stringify(currentLedKeys.sort()))) {
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

async function loadDevices() {
    try {
        const response = await fetch("/api/v1/devices/");
        if (!response.ok) throw new Error(`HTTP error ${response.status}`);
        devicesData = await response.json();

        const deviceSelector = document.getElementById("deviceSelector");
        const compareMeasuredSelector = document.getElementById("compare-measured-collection");

        deviceSelector.innerHTML = '<option value="">Select a device...</option>';
        compareMeasuredSelector.innerHTML = '<option value="">Select a collection...</option>';

        let allMeasuredCollections = [];
        for (const deviceName in devicesData) {
            deviceSelector.add(new Option(deviceName, deviceName));
            if (devicesData[deviceName].measured_collections) {
                devicesData[deviceName].measured_collections.forEach(collection => {
                    allMeasuredCollections.push(collection);
                });
            }
        }

        allMeasuredCollections.sort().forEach(collection => {
            compareMeasuredSelector.add(new Option(collection, collection));
        });

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
    [etalonSelector, measuredSelector].forEach((el) => (el.disabled = true));
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
            method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body),
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || "Failed to load pattern");
        updateStatus(result.message, "connected");
    } catch (error) {
        alert("Error: " + error.message);
    }
}

function updateStatus(message, type) {
    const statusEl = document.getElementById("status");
    if (statusEl) {
        statusEl.textContent = message;
        statusEl.className = `status ${type}`;
    }
}
