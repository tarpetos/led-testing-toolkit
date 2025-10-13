let ws = null;
let leds = {};
let devicesData = {};
let currentPlayerStatus = {is_playing: false};
let ledPositions = {};

function openTab(evt, tabName) {
    const tabContents = document.getElementsByClassName("tab-content");
    for (let i = 0; i < tabContents.length; i++) {
        tabContents[i].style.display = "none";
    }

    const tabLinks = document.getElementsByClassName("tab-link");
    for (let i = 0; i < tabLinks.length; i++) {
        tabLinks[i].className = tabLinks[i].className.replace(" active", "");
    }

    document.getElementById(tabName).style.display = "block";
    evt.currentTarget.className += " active";
}

function updateFileList(fileList, files) {
    fileList.innerHTML = "";
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const fileItem = document.createElement("div");
        fileItem.className = "file-item";
        fileItem.textContent = file.name;
        fileList.appendChild(fileItem);
    }
}

function setupDropZone(dropZoneId, inputId, fileListId, multiple, callback) {
    const dropZone = document.getElementById(dropZoneId);
    const fileInput = document.getElementById(inputId);
    const fileList = fileListId ? document.getElementById(fileListId) : null;

    dropZone.addEventListener("click", () => fileInput.click());

    fileInput.addEventListener("change", (e) => {
        if (e.target.files.length) {
            if (fileList) {
                if (multiple) {
                    updateFileList(fileList, e.target.files);
                } else {
                    updateFileList(fileList, [e.target.files[0]]);
                }
            }
            if (callback) {
                callback(e.target.files);
            }
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
            fileInput.files = e.dataTransfer.files;
            if (fileList) {
                if (multiple) {
                    updateFileList(fileList, e.dataTransfer.files);
                } else {
                    updateFileList(fileList, [e.dataTransfer.files[0]]);
                }
            }
            if (callback) {
                callback(e.dataTransfer.files);
            }
        }
        dropZone.classList.remove("drop-zone--over");
    });
}

function openSubTab(evt, tabName) {
    const tabContents = document.getElementsByClassName("sub-tab-content");
    for (let i = 0; i < tabContents.length; i++) {
        tabContents[i].style.display = "none";
    }

    const tabLinks = document.getElementsByClassName("sub-tab-link");
    for (let i = 0; i < tabLinks.length; i++) {
        tabLinks[i].className = tabLinks[i].className.replace(" active", "");
    }

    document.getElementById(tabName).style.display = "block";
    evt.currentTarget.className += " active";
}

function openModal(src) {
    const modal = document.getElementById("plot-modal");
    const modalImg = document.getElementById("modal-plot-img");
    modal.style.display = "flex";
    modalImg.src = src;
}

function showProcessingAnimation(outputDiv, form) {
    const submitButton = form.querySelector('button[type="submit"]');
    if (submitButton) {
        submitButton.disabled = true;
    }
    outputDiv.innerHTML = `
        <div class="processing-animation">
            <div class="spinner"></div>
            <p>Processing request...</p>
        </div>`;
}

function hideProcessingAnimation(form) {
    const submitButton = form.querySelector('button[type="submit"]');
    if (submitButton) {
        submitButton.disabled = false;
    }
}

function setupOutputTypeSwitcher(selectId, inputId) {
    const typeSelector = document.getElementById(selectId);
    const targetInput = document.getElementById(inputId);

    if (!typeSelector || !targetInput) return;

    typeSelector.addEventListener('change', (e) => {
        if (e.target.value === 'db' && targetInput.value.endsWith('.log')) {
            targetInput.value = '';
        }
    });
}

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

    document.getElementById('split-logs-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const form = e.target;
        const files = form.querySelector('#split-input-files').files;
        if (files.length === 0) {
            alert("Please select at least one file.");
            return;
        }
        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i]);
        }
        formData.append('max_patterns', form.querySelector('#split-max-patterns').value);
        formData.append('output_dir', 'temp');
        formData.append('start_pattern', form.querySelector('#split-start-pattern').value);
        formData.append('end_pattern', form.querySelector('#split-end-pattern').value);

        const outputDiv = document.getElementById('split-logs-output');
        showProcessingAnimation(outputDiv, form);

        try {
            const response = await fetch('/api/v1/tools/split-logs', {
                method: 'POST', body: formData,
            });
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/zip')) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = 'split_logs.zip';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                outputDiv.innerHTML = `<p><strong>Status:</strong> success</p><p><strong>Message:</strong> Files processed and downloaded successfully.</p>`;
            } else {
                const result = await response.json();
                if (result.status === 'error') {
                    throw new Error(result.message);
                }
            }
        } catch (error) {
            outputDiv.innerHTML = `<p><strong>Error:</strong> ${error.message}</p>`;
        } finally {
            hideProcessingAnimation(form);
        }
    });

    document.getElementById('compare-patterns-form').addEventListener('submit', (e) => {
        e.preventDefault();
        const form = e.target;
        const measuredCollection = form.querySelector('#compare-measured-collection').value;
        const measuredRecord = form.querySelector('#compare-measured-record').value;
        const etalonDevice = form.querySelector('#compare-etalon-device').value;
        const etalonPattern = form.querySelector('#compare-etalon-pattern').value;

        const outputDiv = document.getElementById('compare-patterns-output');
        showProcessingAnimation(outputDiv, form);

        fetch('/api/v1/tools/compare-patterns', {
            method: 'POST', headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            }, body: new URLSearchParams({
                measured_collection: measuredCollection,
                measured_record: measuredRecord,
                etalon_device: etalonDevice,
                etalon_pattern: etalonPattern
            })
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
                if (result.status === 'error') {
                    throw new Error(result.message);
                }
                let plotsHtml = '<div class="plots-grid">';
                for (const led in result.results.leds) {
                    plotsHtml += '<div class="led-row">';
                    for (const color in result.results.leds[led]) {
                        const data = result.results.leds[led][color];
                        if (data.plot) {
                            plotsHtml += `<div class="plot-tile"><img src="data:image/png;base64,${data.plot}" onclick="openModal(this.src)" /></div>`;
                        } else {
                            plotsHtml += '<div class="plot-tile empty"><i class="fa-solid fa-ban"></i></div>';
                        }
                    }
                    plotsHtml += '</div>';
                }
                plotsHtml += '</div>';
                outputDiv.innerHTML = `<p><strong>Overall accuracy:</strong> ${result.results.overall_accuracy.toFixed(2)}%</p>${plotsHtml}`;
            })
            .catch(error => {
                console.error("Error in compare-patterns-form:", error);
                outputDiv.innerHTML = `<p><strong>Error:</strong> ${error.message}</p>`;
            })
            .finally(() => {
                hideProcessingAnimation(form);
            });
    });

    document.getElementById('compare-from-log-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const form = e.target;
        const patternIndex = form.querySelector('#compare-log-pattern').value;
        const etalonDevice = form.querySelector('#compare-log-etalon-device').value;
        const etalonPattern = form.querySelector('#compare-log-etalon-pattern').value;

        const outputDiv = document.getElementById('compare-from-log-output');
        showProcessingAnimation(outputDiv, form);

        fetch('/api/v1/tools/compare-log-pattern', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: new URLSearchParams({
                pattern_index: patternIndex,
                etalon_device: etalonDevice,
                etalon_pattern: etalonPattern
            })
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
                if (result.status === 'error') {
                    throw new Error(result.message);
                }
                let plotsHtml = '<div class="plots-grid">';
                for (const led in result.results.leds) {
                    plotsHtml += '<div class="led-row">';
                    for (const color in result.results.leds[led]) {
                        const data = result.results.leds[led][color];
                        if (data.plot) {
                            plotsHtml += `<div class="plot-tile"><img src="data:image/png;base64,${data.plot}" onclick="openModal(this.src)" /></div>`;
                        } else {
                            plotsHtml += '<div class="plot-tile empty"><i class="fa-solid fa-ban"></i></div>';
                        }
                    }
                    plotsHtml += '</div>';
                }
                plotsHtml += '</div>';
                outputDiv.innerHTML = `<p><strong>Overall accuracy:</strong> ${result.results.overall_accuracy.toFixed(2)}%</p>${plotsHtml}`;
            })
            .catch(error => {
                console.error("Error in compare-from-log-form:", error);
                outputDiv.innerHTML = `<p><strong>Error:</strong> ${error.message}</p>`;
            })
            .finally(() => {
                hideProcessingAnimation(form);
            });
    });

    document.getElementById('generate-etalons-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const form = e.target;
        const deviceName = form.querySelector('#generate-etalons-device-name').value;
        const patternName = form.querySelector('#generate-etalons-pattern-name').value;

        const outputDiv = document.getElementById('generate-etalons-output');
        showProcessingAnimation(outputDiv, form);

        try {
            const response = await fetch('/api/v1/tools/generate-etalons', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: new URLSearchParams({
                    device_name: deviceName,
                    pattern_name: patternName
                })
            });

            const responseText = await response.text();
            let result;
            try {
                const jsonStart = responseText.indexOf('{');
                if (jsonStart === -1) throw new Error("Invalid response: Not JSON.");
                const jsonString = responseText.substring(jsonStart);
                result = JSON.parse(jsonString);
            } catch (parseError) {
                throw new Error(`Failed to parse server response. Raw response: ${responseText}`);
            }

            if (!response.ok) throw new Error(result.detail || 'Failed to generate etalons');

            let plotsHtml = '<div class="plots-grid">';
            for (const led in result.plots) {
                plotsHtml += '<div class="led-row">';
                for (const color in result.plots[led]) {
                    plotsHtml += `<div class="plot-tile"><img src="data:image/png;base64,${result.plots[led][color]}" onclick="openModal(this.src)" /></div>`;
                }
                plotsHtml += '</div>';
            }
            plotsHtml += '</div>';
            outputDiv.innerHTML = `<p><strong>Status:</strong> ${result.status}</p><p><strong>Message:</strong> ${result.message}</p>${plotsHtml}`;
        } catch (error) {
            outputDiv.innerHTML = `<p><strong>Error:</strong> ${error.message}</p>`;
        } finally {
            hideProcessingAnimation(form);
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

    document.getElementById('generate-from-parameters-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const form = e.target;
        const formData = new FormData();
        const mode = form.querySelector('#param-generation-mode').value;

        const outputType = form.querySelector('#param-output-type').value;
        const outputTarget = form.querySelector('#param-output-target').value;

        if (outputType === 'log') {
            formData.append('output_file', outputTarget);
        } else {
            formData.append('save_to_db', outputTarget);
        }

        formData.append('mode', 'instant');
        formData.append('duration', form.querySelector('#param-duration').value);
        formData.append('interval', form.querySelector('#param-interval').value);
        formData.append('noise', form.querySelector('#param-noise').value);
        formData.append('lag', form.querySelector('#param-lag').value);
        formData.append('reporting_chance', form.querySelector('#param-reporting-chance').value);

        if (mode === 'simple') {
            formData.append('num_leds', form.querySelector('#param-num-leds').value);
            formData.append('color', form.querySelector('#param-color').value);
            formData.append('fade', form.querySelector('#param-fade').value);
            formData.append('sequence', form.querySelector('#param-sequence').value);
        } else {
            formData.append('palette', form.querySelector('#param-palette').value);
        }

        const outputDiv = document.getElementById('generate-from-parameters-output');
        showProcessingAnimation(outputDiv, form);

        try {
            const response = await fetch('/api/v1/tools/generate-from-parameters', {
                method: 'POST',
                body: formData,
            });
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('text/plain')) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = outputType === 'log' ? outputTarget : 'led_indication.log';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                outputDiv.innerHTML = `<p><strong>Status:</strong> success</p><p><strong>Message:</strong> File generated and downloaded successfully.</p>`;
            } else {
                const responseText = await response.text();
                let result;
                try {
                    const jsonStart = responseText.indexOf('{');
                    if (jsonStart === -1) throw new Error("Invalid response: Not JSON.");
                    const jsonString = responseText.substring(jsonStart);
                    result = JSON.parse(jsonString);
                } catch (parseError) {
                    throw new Error(`Failed to parse server response. Raw response: ${responseText}`);
                }

                if (!response.ok || result.status === 'error') {
                    throw new Error(result.detail || result.message || 'Failed to generate file');
                }
                outputDiv.innerHTML = `<p><strong>Status:</strong> ${result.status}</p><p><strong>Message:</strong> ${result.message}</p>`;
            }
        } catch (error) {
            outputDiv.innerHTML = `<p><strong>Error:</strong> ${error.message}</p>`;
        } finally {
            hideProcessingAnimation(form);
        }
    });

    document.getElementById('generate-from-source-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const form = e.target;
        const formData = new FormData();
        formData.append('mode', 'instant');
        formData.append('source_type', form.querySelector('#source-type').value);
        if (form.querySelector('#source-type').value === 'log') {
            const fileInput = form.querySelector('#source-log-file');
            if (fileInput.files.length > 0) {
                formData.append('file', fileInput.files[0]);
            }
        } else {
            formData.append('collection', form.querySelector('#source-db-collection').value);
            formData.append('pattern_name', form.querySelector('#source-db-pattern-name').value);
            formData.append('process_all', form.querySelector('#source-db-process-all').checked.toString());
        }

        const outputType = form.querySelector('#source-output-type').value;
        const outputTarget = form.querySelector('#source-output-target').value;

        if (outputType === 'log') {
            formData.append('output_dir', outputTarget);
        } else {
            formData.append('save_to_db', outputTarget);
        }

        formData.append('count', form.querySelector('#source-count').value);
        formData.append('noise', form.querySelector('#source-noise').value);
        formData.append('lag', form.querySelector('#source-lag').value);
        formData.append('reporting_chance', form.querySelector('#source-reporting-chance').value);
        formData.append('interval', form.querySelector('#source-interval').value);

        const outputDiv = document.getElementById('generate-from-source-output');
        showProcessingAnimation(outputDiv, form);

        try {
            const response = await fetch('/api/v1/tools/generate-from-source', {
                method: 'POST', body: formData,
            });

            const contentType = response.headers.get('content-type');

            if (contentType && (contentType.includes('application/zip') || contentType.includes('text/plain'))) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                const isZip = contentType.includes('application/zip');
                a.download = isZip ? 'generated_logs.zip' : (outputType === 'log' ? outputTarget : 'generated_log.log');
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                outputDiv.innerHTML = `<p><strong>Status:</strong> success</p><p><strong>Message:</strong> File(s) generated and downloaded successfully.</p>`;
            } else {
                const responseText = await response.text();
                let result;
                try {
                    const jsonStart = responseText.indexOf('{');
                    if (jsonStart === -1) throw new Error("Invalid response: Not JSON.");
                    const jsonString = responseText.substring(jsonStart);
                    result = JSON.parse(jsonString);
                } catch (parseError) {
                    throw new Error(`Failed to parse server response. Raw response: ${responseText}`);
                }

                if (!response.ok || result.status === 'error') {
                    throw new Error(result.detail || result.message || 'Failed to generate files');
                }
                outputDiv.innerHTML = `<p><strong>Status:</strong> ${result.status}</p><p><strong>Message:</strong> ${result.message}</p>`;
            }
        } catch (error) {
            outputDiv.innerHTML = `<p><strong>Error:</strong> ${error.message}</p>`;
        } finally {
            hideProcessingAnimation(form);
        }
    });

    const generationModeSelector = document.getElementById('param-generation-mode');
    const simpleParamsContainer = document.getElementById('simple-params-container');
    const paletteParamsContainer = document.getElementById('palette-params-container');
    const paletteTextInput = document.getElementById('param-palette-text');
    const hiddenPaletteInput = document.getElementById('param-palette');

    generationModeSelector.addEventListener('change', (e) => {
        if (e.target.value === 'simple') {
            simpleParamsContainer.style.display = 'block';
            paletteParamsContainer.style.display = 'none';
            hiddenPaletteInput.value = '';
        } else {
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

function formatTime(seconds) {
    const min = Math.floor(seconds / 60);
    const sec = Math.floor(seconds % 60);
    return `${min.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
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
