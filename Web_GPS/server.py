import time
import json
import threading
from flask import Flask, render_template
from flask_socketio import SocketIO
import websocket
import logging

# ---- Cấu hình ----
class Config:
    THINGSBOARD_TOKEN = 'eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJ2dmFuaDIxMDIwM0BnbWFpbC5jb20iLCJ1c2VySWQiOiJiNWVmYjdmMC00YTJmLTExZjAtOTY2NC1mZjEzZWNjYjQ3ZmYiLCJzY29wZXMiOlsiVEVOQU5UX0FETUlOIl0sInNlc3Npb25JZCI6ImNmNmRhYTU0LTQzNGUtNDgzMC1hYjgyLTY5NjFjNmU2NzI1MSIsImV4cCI6MTc2MjE3ODQ4NCwiaXNzIjoidGhpbmdzYm9hcmQuaW8iLCJpYXQiOjE3NjAzNzg0ODQsImZpcnN0TmFtZSI6IkFuaCIsImxhc3ROYW1lIjoiVsWpIiwiZW5hYmxlZCI6dHJ1ZSwicHJpdmFjeVBvbGljeUFjY2VwdGVkIjp0cnVlLCJpc1B1YmxpYyI6ZmFsc2UsInRlbmFudElkIjoiYjVjMzUwYzAtNGEyZi0xMWYwLTk2NjQtZmYxM2VjY2I0N2ZmIiwiY3VzdG9tZXJJZCI6IjEzODE0MDAwLTFkZDItMTFiMi04MDgwLTgwODA4MDgwODA4MCJ9.V1UF2qYI9R_ucDtcZglRcybLdbGKDhCkH_nQrduisaqJwWM-048TLvew9QgYV58dk5RCv7_1lxE8WeFfJnik3g'
    DEVICE_ID = 'afe86c60-8f3c-11f0-a9b5-792e2194a5d4'  
    SOCKETIO_PORT = 5000

# ---- Logging ----
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s][%(levelname)s] %(message)s'
)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

def thingsboard_ws_thread():
    url = f"wss://demo.thingsboard.io/api/ws/plugins/telemetry?token={Config.THINGSBOARD_TOKEN}"

    def on_message(ws, message):
        try:
            data = json.loads(message)
            logging.info(f"Received messages: {data}\n")

            if isinstance(data, dict) and 'data' in data:
                telemetry = data['data']
                if ('gps_latitude' in telemetry and 'gps_longitude' in telemetry 
                    and telemetry['gps_latitude'] and telemetry['gps_longitude']):
                    gps_latitude = telemetry['gps_latitude'][0][1]
                    gps_longitude = telemetry['gps_longitude'][0][1]
                    socketio.emit('gps_update', {
                        'lat': float(gps_latitude),
                        'lon': float(gps_longitude)
                    })
                    logging.info(f"Emit gps_update: {gps_latitude}, {gps_longitude}\n")
                else:
                    logging.warning(f"Not found gps_latitude/gps_longitude in telemetry: {telemetry}")
            else:
                logging.warning(f"Message not contain field 'data' or is not dict: {data}")
        except Exception as e:
            logging.error(f"Error to handle message: {e}")



    def on_error(ws, error):
        logging.error(f"WebSocket error: {error}")

    def on_close(ws, close_status_code, close_msg):
        logging.warning(f"WebSocket closed: code={close_status_code}, msg={close_msg}. Reconnecting in 5s...")
        time.sleep(5)
        start_ws()  

    def on_open(ws):
        sub_cmd = {
            "tsSubCmds": [
                {
                    "entityType": "DEVICE",
                    "entityId": Config.DEVICE_ID,
                    "scope": "LATEST_TELEMETRY",
                    "cmdId": 1
                }
            ],
            "historyCmds": [],
            "attrSubCmds": []
        }
        ws.send(json.dumps(sub_cmd))
        logging.info("Sent to subscribe telemetry")

    def start_ws():
        ws = websocket.WebSocketApp(
            url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )
        ws.run_forever()

    start_ws()

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == "__main__":
    threading.Thread(target=thingsboard_ws_thread, daemon=True).start()
    socketio.run(app, host='0.0.0.0', port=Config.SOCKETIO_PORT)
