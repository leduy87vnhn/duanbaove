import time
import requests
import threading
from flask import Flask, render_template
from flask_socketio import SocketIO
import logging

class Config:
    THINGSBOARD_TOKEN = 'tGZ5ZOcgP64j10xGLaVB'
    THINGSBOARD_API_URL = f'https://demo.thingsboard.io/api/v1/{THINGSBOARD_TOKEN}/telemetry'
    SOCKETIO_PORT = 5000
    POLL_INTERVAL = 2  # Số giây mỗi lần poll

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s][%(levelname)s] %(message)s'
)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

last_lat = None
last_lon = None

def poll_thingsboard():
    global last_lat, last_lon
    while True:
        try:
            resp = requests.get(Config.THINGSBOARD_API_URL, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                lat = data.get('gps_latitude', [{}])[0].get('value') if data.get('gps_latitude') else None
                lon = data.get('gps_longitude', [{}])[0].get('value') if data.get('gps_longitude') else None
                if lat is not None and lon is not None:
                    lat, lon = float(lat), float(lon)
                    # Chỉ emit nếu có thay đổi (giảm tải web)
                    if lat != last_lat or lon != last_lon:
                        last_lat, last_lon = lat, lon
                        socketio.emit('gps_update', {'lat': lat, 'lon': lon})
                        logging.info(f"Emit gps_update: {lat}, {lon}")
            else:
                logging.warning(f"REST API lỗi: {resp.status_code}")
        except Exception as e:
            logging.error(f"Lỗi REST API: {e}")
        time.sleep(Config.POLL_INTERVAL)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == "__main__":
    threading.Thread(target=poll_thingsboard, daemon=True).start()
    socketio.run(app, host='0.0.0.0', port=Config.SOCKETIO_PORT)
