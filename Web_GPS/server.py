from flask import Flask, render_template
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import json
import threading
import logging

# =========================
# Configuration
# =========================
class Config:
    MQTT_BROKER = 'demo.thingsboard.io'
    MQTT_PORT = 1883
    MQTT_TOPIC = 'v1/devices/me/telemetry'
    MQTT_TOKEN = 'tGZ5ZOcgP64j10xGLaVB'  
    SOCKETIO_PORT = 5000

# =========================
# Logging setup
# =========================
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s][%(levelname)s] %(message)s'
)

# =========================
# Flask App Setup
# =========================
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")  # CORS cho frontend mọi nơi

# =========================
# MQTT Client Setup
# =========================
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logging.info("Connected to MQTT broker OK")
        client.subscribe(Config.MQTT_TOPIC)
    else:
        logging.warning(f"Failed to connect MQTT: {rc}")

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        logging.info(f"MQTT message received: {payload}")
        data = json.loads(payload)
        lat = data.get('gps_latitude')
        lon = data.get('gps_longitude')
        if lat is not None and lon is not None:
            try:
                lat, lon = float(lat), float(lon)
                # Kiểm tra hợp lệ
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    socketio.emit('gps_update', {'lat': lat, 'lon': lon})
                    logging.info(f"Emit gps_update: {lat}, {lon}")
                else:
                    logging.warning(f"GPS out of range: {lat}, {lon}")
            except ValueError:
                logging.warning(f"GPS not a float: {lat}, {lon}")
        else:
            logging.warning(f"MQTT no GPS data: {data}")
    except Exception as e:
        logging.error(f"MQTT error: {e}")

def start_mqtt():
    client = mqtt.Client()
    client.username_pw_set(Config.MQTT_TOKEN)
    client.on_connect = on_connect
    client.on_message = on_message
    # Option: Auto reconnect
    client.reconnect_delay_set(min_delay=1, max_delay=10)
    client.connect(Config.MQTT_BROKER, Config.MQTT_PORT, 60)
    client.loop_forever()

# =========================
# Flask route
# =========================
@app.route('/')
def index():
    return render_template('index.html')  # Đặt file index.html trong templates/

# =========================
# Main
# =========================
if __name__ == "__main__":
    threading.Thread(target=start_mqtt, daemon=True).start()
    socketio.run(app, host='0.0.0.0', port=Config.SOCKETIO_PORT)
