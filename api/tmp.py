import asyncio
import json
import re
from datetime import datetime
from typing import Annotated

import uvicorn
from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from loguru import logger

app = FastAPI(title="LED Visualization", description="Real-time LED status visualization")

current_leds: dict[int, tuple[int, int, int]] = {}
websocket_connections: list[WebSocket] = []


class LEDLogParser:
    def __init__(self):
        self.led_pattern = re.compile(r"LED(\d+)=\[(\d+),(\d+),(\d+)\]")

    def parse_line(self, line: str) -> list[tuple[int, int, int, int]]:
        matches = self.led_pattern.findall(line)
        results = []
        for match in matches:
            led_num = int(match[0])
            r, g, b = int(match[1]), int(match[2]), int(match[3])
            results.append((led_num, r, g, b))
        return results

    def get_max_led_from_log(self, log_content: str) -> int:
        max_led = 0
        for line in log_content.split("\n"):
            matches = self.led_pattern.findall(line)
            for match in matches:
                led_num = int(match[0])
                max_led = max(max_led, led_num)
        return max_led


parser = LEDLogParser()


async def broadcast_led_state() -> None:
    if websocket_connections and current_leds:
        message = {
            "type": "led_update",
            "leds": {str(k): {"r": v[0], "g": v[1], "b": v[2]} for k, v in current_leds.items()},
            "timestamp": datetime.now().isoformat(),
        }

        active_connections = []
        for connection in websocket_connections:
            try:
                await connection.send_text(json.dumps(message))
                active_connections.append(connection)
            except Exception as e:
                logger.error(f"Error sending message to client: {e!s}")
        websocket_connections[:] = active_connections


@app.post("/upload_log")
async def upload_log(file: Annotated[UploadFile, File()] = ...):  # noqa: ANN201
    global current_leds  # noqa: PLW0603

    log_content = await file.read()
    log_content = log_content.decode("utf-8")

    max_led = parser.get_max_led_from_log(log_content)
    current_leds = dict.fromkeys(range(1, max_led + 1), (0, 0, 0))
    asyncio.create_task(process_log_data(log_content))  # noqa: RUF006

    return {
        "status": "success",
        "message": f"Log uploaded successfully. Found {max_led} LEDs.",
        "led_count": max_led,
    }


async def process_log_data(log_content: str) -> None:
    lines = [line for line in log_content.split("\n") if "LED" in line and "[" in line]

    prev_timestamp = None

    for line in lines:
        timestamp_match = re.match(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+)", line)
        if timestamp_match:
            current_time = datetime.fromisoformat(timestamp_match.group(1).replace("+0300", ""))

            if prev_timestamp:
                delay = (current_time - prev_timestamp).total_seconds()
                delay = min(max(delay, 0.01), 2.0)
                await asyncio.sleep(delay)

            prev_timestamp = current_time
        else:
            await asyncio.sleep(0.1)

        led_updates = parser.parse_line(line)

        for led_num, r, g, b in led_updates:
            current_leds[led_num] = (r, g, b)

        if led_updates:
            await broadcast_led_state()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    websocket_connections.append(websocket)

    if current_leds:
        initial_message = {
            "type": "led_update",
            "leds": {str(k): {"r": v[0], "g": v[1], "b": v[2]} for k, v in current_leds.items()},
            "timestamp": datetime.now().isoformat(),
        }
        await websocket.send_text(json.dumps(initial_message))

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)


@app.get("/", response_class=HTMLResponse)
async def get_dashboard():  # noqa: ANN201
    return HTMLResponse(
        content="""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LED Visualization Dashboard</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #1e1e1e, #2d2d2d);
            color: #ffffff;
            min-height: 100vh;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        h1 {
            text-align: center;
            margin-bottom: 30px;
            color: #00ff88;
            text-shadow: 0 0 20px rgba(0, 255, 136, 0.3);
        }

        .upload-section {
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 30px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }

        .upload-section h3 {
            margin-top: 0;
            color: #00ff88;
        }

        input[type="file"] {
            width: 100%;
            background: rgba(0, 0, 0, 0.5);
            border: 1px solid #00ff88;
            border-radius: 8px;
            color: #ffffff;
            padding: 10px;
            font-family: monospace;
        }

        button {
            background: linear-gradient(45deg, #00ff88, #00cc6a);
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            color: #000;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-top: 10px;
        }

        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(0, 255, 136, 0.4);
        }

        .led-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }

        .led {
            width: 100px;
            height: 100px;
            border-radius: 50%;
            margin: 0 auto;
            position: relative;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow:
                0 0 20px rgba(0, 0, 0, 0.3),
                inset 0 0 20px rgba(255, 255, 255, 0.1);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            color: rgba(255, 255, 255, 0.8);
            text-shadow: 0 0 5px rgba(0, 0, 0, 0.8);
        }

        .led-container {
            text-align: center;
            padding: 15px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            backdrop-filter: blur(5px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .led-label {
            margin-top: 10px;
            font-weight: bold;
            color: #00ff88;
        }

        .led-values {
            margin-top: 5px;
            font-size: 12px;
            color: #cccccc;
            font-family: monospace;
        }

        .status {
            text-align: center;
            margin: 20px 0;
            padding: 10px;
            border-radius: 8px;
            font-weight: bold;
        }

        .status.connected {
            background: rgba(0, 255, 136, 0.2);
            color: #00ff88;
            border: 1px solid #00ff88;
        }

        .status.disconnected {
            background: rgba(255, 0, 0, 0.2);
            color: #ff4444;
            border: 1px solid #ff4444;
        }

        .timestamp {
            text-align: center;
            color: #888;
            font-size: 12px;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔴🟢🔵 LED Visualization Dashboard</h1>

        <div class="upload-section">
            <h3>Upload Log File</h3>
            <input type="file" id="logFile" accept=".txt,.log">
            <button onclick="uploadLog()">Start Visualization</button>
        </div>

        <div id="status" class="status disconnected">
            Disconnected - Upload log file to start
        </div>

        <div id="ledGrid" class="led-grid">
            <!-- LEDs will be populated dynamically -->
        </div>

        <div id="timestamp" class="timestamp"></div>
    </div>

    <script>
        let ws = null;
        let leds = {};

        function connectWebSocket() {
            const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${location.host}/ws`);

            ws.onopen = function() {
                document.getElementById('status').textContent = 'Connected - Waiting for LED data';
                document.getElementById('status').className = 'status connected';
            };

            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                if (data.type === 'led_update') {
                    updateLEDs(data.leds);
                    document.getElementById('timestamp').textContent =
                        'Last update: ' + new Date(data.timestamp).toLocaleTimeString();
                }
            };

            ws.onclose = function() {
                document.getElementById('status').textContent = 'Disconnected';
                document.getElementById('status').className = 'status disconnected';
                // Reconnect after 3 seconds
                setTimeout(connectWebSocket, 3000);
            };

            ws.onerror = function() {
                document.getElementById('status').textContent = 'Connection Error';
                document.getElementById('status').className = 'status disconnected';
            };
        }

        function uploadLog() {
            const fileInput = document.getElementById('logFile');
            const file = fileInput.files[0];
            if (!file) {
                alert('Please select a log file first');
                return;
            }

            const formData = new FormData();
            formData.append('file', file);

            fetch('/upload_log', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    document.getElementById('status').textContent =
                        `${data.message} Starting visualization...`;
                    document.getElementById('status').className = 'status connected';
                    createLEDGrid(data.led_count);
                } else {
                    alert('Error uploading log: ' + data.message);
                }
            })
            .catch(error => {
                alert('Error: ' + error);
            });
        }

        function createLEDGrid(ledCount) {
            const grid = document.getElementById('ledGrid');
            grid.innerHTML = '';

            for (let i = 1; i <= ledCount; i++) {
                const container = document.createElement('div');
                container.className = 'led-container';

                const led = document.createElement('div');
                led.className = 'led';
                led.id = `led-${i}`;
                led.textContent = `LED${i}`;
                led.style.backgroundColor = 'rgb(20, 20, 20)';

                const label = document.createElement('div');
                label.className = 'led-label';
                label.textContent = `LED ${i}`;

                const values = document.createElement('div');
                values.className = 'led-values';
                values.id = `values-${i}`;
                values.textContent = 'RGB: [0,0,0]';

                container.appendChild(led);
                container.appendChild(label);
                container.appendChild(values);
                grid.appendChild(container);

                leds[i] = {r: 0, g: 0, b: 0};
            }
        }

        function updateLEDs(ledData) {
            Object.keys(ledData).forEach(ledNum => {
                const led = document.getElementById(`led-${ledNum}`);
                const values = document.getElementById(`values-${ledNum}`);

                if (led && values) {
                    const {r, g, b} = ledData[ledNum];

                    // Smooth transition using CSS
                    led.style.backgroundColor = `rgb(${r}, ${g}, ${b})`;

                    // Add glow effect for bright LEDs
                    const brightness = (r + g + b) / 3;
                    if (brightness > 50) {
                        led.style.boxShadow = `
                            0 0 20px rgba(${r}, ${g}, ${b}, 0.6),
                            0 0 40px rgba(${r}, ${g}, ${b}, 0.4),
                            inset 0 0 20px rgba(255, 255, 255, 0.1)
                        `;
                    } else {
                        led.style.boxShadow = `
                            0 0 20px rgba(0, 0, 0, 0.3),
                            inset 0 0 20px rgba(255, 255, 255, 0.1)
                        `;
                    }

                    values.textContent = `RGB: [${r},${g},${b}]`;
                    leds[ledNum] = {r, g, b};
                }
            });
        }

        // Initialize WebSocket connection
        connectWebSocket();
    </script>
</body>
</html>
    """,
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)  # noqa: S104
