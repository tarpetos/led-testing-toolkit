function setupFormEventListeners() {
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
}
