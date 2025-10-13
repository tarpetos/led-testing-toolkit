function setupPlayerControls() {
    const playerWrapper = document.getElementById('player-wrapper');
    const fullscreenBtn = document.getElementById('fullscreenBtn');
    const resizeHandle = document.getElementById('resize-handle');
    const body = document.body;

    fullscreenBtn.addEventListener('click', () => {
        playerWrapper.classList.toggle('fullscreen');
        setTimeout(updateLedPixelPositions, 50);
    });

    resizeHandle.addEventListener('mousedown', function (e) {
        e.preventDefault();
        const startHeight = playerWrapper.offsetHeight;
        const startY = e.clientY;
        body.classList.add('is-resizing');

        function handleDragResize(e) {
            const newHeight = startHeight - (e.clientY - startY);
            const maxHeight = window.innerHeight - 150;
            const minStaticHeight = 150;

            if (newHeight >= minStaticHeight && newHeight < maxHeight) {
                playerWrapper.style.height = `${newHeight}px`;
            } else if (newHeight < minStaticHeight) {
                playerWrapper.style.height = `${minStaticHeight}px`;
            }
        }

        function stopDragResize() {
            body.classList.remove('is-resizing');
            document.removeEventListener('mousemove', handleDragResize);
            document.removeEventListener('mouseup', stopDragResize);

            updateLedPixelPositions();

            let maxLedBottom = 0;
            const ledElements = document.querySelectorAll('#ledContainer .led-item');
            ledElements.forEach(el => {
                maxLedBottom = Math.max(maxLedBottom, el.offsetTop + el.offsetHeight);
            });

            const firstLedItem = ledElements[0];
            const ledItemHeight = firstLedItem ? firstLedItem.offsetHeight : 0;
            const controlsHeight = document.querySelector('.player-controls-ui').offsetHeight;
            const PADDING = 10;

            const minHeightFromItemSize = ledItemHeight > 0 ? (ledItemHeight + controlsHeight + PADDING * 2) : controlsHeight;
            const minHeightFromContent = maxLedBottom > 0 ? (maxLedBottom + controlsHeight + PADDING) : controlsHeight;

            const requiredHeight = Math.max(minHeightFromItemSize, minHeightFromContent);
            const currentHeight = playerWrapper.offsetHeight;

            if (currentHeight < requiredHeight) {
                playerWrapper.style.height = `${requiredHeight}px`;
                updateLedPixelPositions();
            }
        }

        document.addEventListener('mousemove', handleDragResize);
        document.addEventListener('mouseup', stopDragResize);
    });
}

function updateLedPixelPositions() {
    const ledContainer = document.getElementById("ledContainer");
    const containerWidth = ledContainer.clientWidth;
    const containerHeight = ledContainer.clientHeight;
    if (containerWidth === 0 || containerHeight === 0) return;

    for (const ledId in ledPositions) {
        const ledItem = document.getElementById(`led-item-${ledId}`);
        if (ledItem) {
            const pos = ledPositions[ledId];
            const itemWidth = ledItem.offsetWidth;
            const itemHeight = ledItem.offsetHeight;
            const availableWidth = containerWidth - itemWidth;
            const availableHeight = containerHeight - itemHeight;

            ledItem.style.left = `${pos.x * availableWidth}px`;
            ledItem.style.top = `${pos.y * availableHeight}px`;
        }
    }
}

function createAndPositionLeds(ledsData) {
    const ledContainer = document.getElementById("ledContainer");
    ledContainer.innerHTML = "";
    leds = {};
    const currentPatternPositions = {};
    const ledKeys = Object.keys(ledsData);

    ledKeys.forEach((ledId) => {
        const ledItem = document.createElement("div");
        ledItem.className = "led-item";
        ledItem.id = `led-item-${ledId}`;
        ledItem.draggable = true;
        ledItem.style.position = 'absolute';
        ledItem.addEventListener("dragstart", handleDragStart);
        const led = document.createElement("div");
        led.className = "led";
        led.id = `led-${ledId}`;
        const ledInfo = document.createElement("div");
        ledInfo.className = "led-overlay-info";
        ledInfo.innerHTML = `<div class="led-name">${ledId}</div><div class="led-rgb" id="led-rgb-${ledId}">(0,0,0)</div>`;
        led.append(ledInfo);
        ledItem.append(led);
        ledContainer.append(ledItem);
        leds[ledId] = led;
    });

    setTimeout(() => {
        const ledElements = Array.from(ledContainer.getElementsByClassName('led-item'));
        const N = ledElements.length;
        if (N === 0) return;

        const containerWidth = ledContainer.clientWidth;
        const containerHeight = ledContainer.clientHeight;
        const uniformItemWidth = ledElements[0].offsetWidth;
        const uniformItemHeight = ledElements[0].offsetHeight;

        const playerWrapper = document.getElementById('player-wrapper');
        if (playerWrapper.classList.contains('hidden') || !playerWrapper.style.height) {
            const controlsHeight = document.querySelector('.player-controls-ui').offsetHeight;
            const PADDING = 10;
            const requiredHeight = uniformItemHeight + controlsHeight + PADDING * 2;
            playerWrapper.style.height = `${requiredHeight}px`;
        }

        if (uniformItemWidth === 0 || uniformItemHeight === 0 || containerWidth === 0 || containerHeight === 0) {
            setTimeout(() => createAndPositionLeds(ledsData), 100);
            return;
        }

        const availableWidth = Math.max(1, containerWidth - uniformItemWidth);
        const availableHeight = Math.max(1, containerHeight - uniformItemHeight);

        let itemsPerRow = Math.floor(containerWidth / uniformItemWidth);
        if (itemsPerRow === 0) itemsPerRow = 1;

        const totalWidth = itemsPerRow * uniformItemWidth;
        const totalHeight = Math.ceil(N / itemsPerRow) * uniformItemHeight;

        const startX = Math.max(0, (containerWidth - totalWidth) / 2);
        const startY = Math.max(0, (containerHeight - totalHeight) / 2);

        ledElements.forEach((ledItem, index) => {
            const ledId = ledItem.id.replace('led-item-', '');
            if (ledPositions[ledId]) {
                currentPatternPositions[ledId] = ledPositions[ledId];
            } else {
                const row = Math.floor(index / itemsPerRow);
                const col = index % itemsPerRow;
                const xPos = startX + (col * uniformItemWidth);
                const yPos = startY + (row * uniformItemHeight);
                currentPatternPositions[ledId] = {
                    x: Math.max(0, Math.min(1, xPos / availableWidth)),
                    y: Math.max(0, Math.min(1, yPos / availableHeight))
                };
            }
        });
        ledPositions = currentPatternPositions;
        updateLedPixelPositions();
    }, 50);
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

function updateSliderFill(slider) {
    const progress = (slider.value / slider.max) * 100;
    slider.style.setProperty('--progress-percent', `${progress}%`);
}

function handleSliderInput(slider) {
    updateSliderFill(slider);
    seekToTime(slider.value);
}

let draggedElement = null;
let offsetX = 0;
let offsetY = 0;

function handleDragStart(e) {
    draggedElement = e.currentTarget;
    const rect = draggedElement.getBoundingClientRect();
    offsetX = e.clientX - rect.left;
    offsetY = e.clientY - rect.top;
    e.dataTransfer.effectAllowed = 'move';
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
        const ledId = draggedElement.id.replace('led-item-', '');
        const container = document.getElementById('ledContainer');
        const containerWidth = container.clientWidth;
        const containerHeight = container.clientHeight;
        const itemWidth = draggedElement.offsetWidth;
        const itemHeight = draggedElement.offsetHeight;

        if (containerWidth > itemWidth && containerHeight > itemHeight) {
            const finalX = parseFloat(draggedElement.style.left);
            const finalY = parseFloat(draggedElement.style.top);
            const availableWidth = containerWidth - itemWidth;
            const availableHeight = containerHeight - itemHeight;

            const newPosition = {
                x: Math.max(0, Math.min(1, finalX / availableWidth)),
                y: Math.max(0, Math.min(1, finalY / availableHeight))
            };

            ledPositions[ledId] = newPosition;

            const allSavedPositions = JSON.parse(localStorage.getItem('savedLedPositions') || '{}');
            allSavedPositions[ledId] = newPosition;
            localStorage.setItem('savedLedPositions', JSON.stringify(allSavedPositions));
        }
    }
    draggedElement = null;
}
