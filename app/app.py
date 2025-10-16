import sys
import json
import logging
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QSplitter, QDialog)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer, QObject, pyqtSlot
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import QUrl
import paho.mqtt.client as mqtt
import cv2
from PyQt6.QtGui import QImage, QPixmap, QFont

# Logging setup
logging.basicConfig(level=logging.INFO, format="[%(asctime)s][%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ==================== MQTT Thread ====================
class MQTTThread(QThread):
    gps_update = pyqtSignal(float, float)
    connection_status = pyqtSignal(bool, str)
    
    def __init__(self, host, token):
        super().__init__()
        self.host = host
        self.token = token
        self.client = None
        self.running = True
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected to ThingsBoard MQTT")
            self.connection_status.emit(True, "Connected to MQTT Server")
            client.subscribe("v1/devices/me/telemetry")
        else:
            logger.error(f"MQTT Connection failed: {rc}")
            self.connection_status.emit(False, f"Connection Error: {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        logger.warning(f"Disconnected from MQTT (rc={rc})")
        self.connection_status.emit(False, "Disconnected from Server")
    
    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            if 'gps_latitude' in payload and 'gps_longitude' in payload:
                lat = float(payload['gps_latitude'])
                lon = float(payload['gps_longitude'])
                logger.info(f"GPS Update: {lat}, {lon}")
                self.gps_update.emit(lat, lon)
        except Exception as e:
            logger.error(f"Error parsing MQTT message: {e}")
    
    def run(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.client.username_pw_set(self.token)
        
        try:
            self.client.connect(self.host, 1883, 60)
            self.client.loop_forever()
        except Exception as e:
            logger.error(f"MQTT Connection error: {e}")
            self.connection_status.emit(False, f"Error: {e}")
    
    def stop(self):
        self.running = False
        if self.client:
            self.client.disconnect()
            self.client.loop_stop()

# ==================== RTSP Camera Thread ====================
class RTSPThread(QThread):
    frame_ready = pyqtSignal(QImage)
    connection_status = pyqtSignal(bool, str)
    
    def __init__(self, rtsp_url):
        super().__init__()
        self.rtsp_url = rtsp_url
        self.running = False
        
    def run(self):
        self.running = True
        cap = cv2.VideoCapture(self.rtsp_url)
        
        if not cap.isOpened():
            logger.error("Cannot connect to RTSP stream")
            self.connection_status.emit(False, "Cannot connect to camera")
            return
        
        self.connection_status.emit(True, "Camera connected")
        logger.info("RTSP stream connected")
        
        while self.running:
            ret, frame = cap.read()
            if ret:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                self.frame_ready.emit(qt_image)
            else:
                logger.warning("Failed to read frame")
                break
        
        cap.release()
        logger.info("RTSP stream closed")
    
    def stop(self):
        self.running = False

# ==================== Camera Dialog Window ====================
class CameraDialog(QDialog):
    def __init__(self, parent=None, rtsp_url=""):
        super().__init__(parent)
        self.setWindowTitle("📹 Live Camera Stream")
        self.setModal(False)
        self.resize(960, 600)
        self.rtsp_url = rtsp_url
        self.rtsp_thread = None
        
        self.init_ui()
        self.start_camera()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = QWidget()
        header.setStyleSheet("background: #2c3e50; padding: 10px;")
        header_layout = QHBoxLayout(header)
        
        title = QLabel("📹 Live Camera Stream")
        title.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        self.status_label = QLabel("⚪ Connecting...")
        self.status_label.setStyleSheet("color: #ecf0f1; font-size: 13px; padding: 5px 10px; background: rgba(255,255,255,0.1); border-radius: 3px;")
        header_layout.addWidget(self.status_label)
        
        close_btn = QPushButton("✖ Close")
        close_btn.clicked.connect(self.close_camera)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #e74c3c; 
                color: white; 
                padding: 8px 20px; 
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #c0392b;
            }
        """)
        header_layout.addWidget(close_btn)
        
        layout.addWidget(header)
        
        # Video display
        self.video_label = QLabel()
        self.video_label.setStyleSheet("background: black;")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(640, 360)
        layout.addWidget(self.video_label)
    
    def start_camera(self):
        self.rtsp_thread = RTSPThread(self.rtsp_url)
        self.rtsp_thread.frame_ready.connect(self.display_frame)
        self.rtsp_thread.connection_status.connect(self.on_camera_status)
        self.rtsp_thread.start()
    
    def display_frame(self, image):
        label_width = self.video_label.width()
        label_height = self.video_label.height()
        
        max_width = min(label_width, 1920)
        max_height = min(label_height, 1080)
        
        scaled_pixmap = QPixmap.fromImage(image).scaled(
            max_width, max_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation
        )
        self.video_label.setPixmap(scaled_pixmap)
    
    def on_camera_status(self, connected, message):
        if connected:
            self.status_label.setText(f"🟢 {message}")
            self.status_label.setStyleSheet("color: #2ecc71; font-size: 13px; padding: 5px 10px; background: rgba(46,204,113,0.2); border-radius: 3px;")
        else:
            self.status_label.setText(f"🔴 {message}")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 13px; padding: 5px 10px; background: rgba(231,76,60,0.2); border-radius: 3px;")
    
    def close_camera(self):
        if self.rtsp_thread:
            self.rtsp_thread.stop()
            self.rtsp_thread.wait()
        self.close()
    
    def closeEvent(self, event):
        if self.rtsp_thread:
            self.rtsp_thread.stop()
            self.rtsp_thread.wait()
        event.accept()

# ==================== Main Window ====================
class GPSCameraApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GPS Tracking & Camera Viewer")
        self.setGeometry(100, 100, 1200, 800)
        
        # Configuration
        self.THINGSBOARD_HOST = "demo.thingsboard.io"
        self.ACCESS_TOKEN = "tGZ5ZOcgP64j10xGLaVB"
        self.RTSP_URL = "rtsp://admin:Abcd121%40@113.185.6.120:8554/Streaming/Channels/101"
        self.VIETMAP_API_KEY = "2eada1a08ba9a656491f1e14cc0224ee5ea4d611c8adae41"
        
        # GPS Data
        self.current_lat = 21.028511
        self.current_lon = 105.804817
        self.gps_history = []
        self.auto_follow = True
        
        # Threads
        self.mqtt_thread = None
        self.camera_dialog = None
        
        self.init_ui()
        self.start_mqtt()
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ===== Top Control Bar =====
        control_bar = QWidget()
        control_bar.setStyleSheet("background: #34495e; padding: 8px;")
        control_layout = QHBoxLayout(control_bar)
        control_layout.setSpacing(10)
        
        # Status
        self.status_label = QLabel("🔴 Connecting...")
        self.status_label.setStyleSheet("""
            background: rgba(231,76,60,0.2); 
            color: #e74c3c; 
            padding: 8px 15px; 
            border-radius: 4px; 
            font-weight: 600;
            font-size: 13px;
        """)
        control_layout.addWidget(self.status_label)
        
        # GPS Coords
        self.gps_label = QLabel("📍 Lat: --- | Lon: ---")
        self.gps_label.setStyleSheet("""
            background: rgba(52,152,219,0.2); 
            color: #3498db; 
            padding: 8px 15px; 
            border-radius: 4px;
            font-size: 13px;
        """)
        control_layout.addWidget(self.gps_label)
        
        # Last update
        self.update_label = QLabel("No data")
        self.update_label.setStyleSheet("""
            background: rgba(241,196,15,0.2); 
            color: #f1c40f; 
            padding: 8px 15px; 
            border-radius: 4px;
            font-size: 13px;
        """)
        control_layout.addWidget(self.update_label)
        
        control_layout.addStretch()
        
        # Buttons
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_history)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background: #3498db; 
                color: white; 
                padding: 8px 20px; 
                border: none;
                border-radius: 4px; 
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #2980b9;
            }
        """)
        control_layout.addWidget(self.clear_btn)
        
        self.follow_btn = QPushButton("Auto Follow: ON")
        self.follow_btn.clicked.connect(self.toggle_follow)
        self.follow_btn.setStyleSheet("""
            QPushButton {
                background: #27ae60; 
                color: white; 
                padding: 8px 20px; 
                border: none;
                border-radius: 4px; 
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #229954;
            }
        """)
        control_layout.addWidget(self.follow_btn)
        
        main_layout.addWidget(control_bar)
        
        # ===== Map View =====
        self.map_view = QWebEngineView()
        self.load_map()
        main_layout.addWidget(self.map_view)
    
    def load_map(self):
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
            <style>
                body {{ margin: 0; padding: 0; }}
                #map {{ width: 100vw; height: 100vh; }}
            </style>
        </head>
        <body>
            <div id="map"></div>
            <script>
                var map = L.map('map').setView([{self.current_lat}, {self.current_lon}], 13);
                L.tileLayer('https://maps.vietmap.vn/maps/tiles/tm/{{z}}/{{x}}/{{y}}@2x.png?apikey={self.VIETMAP_API_KEY}', {{
                    attribution: '© VietMap.vn', maxZoom: 18
                }}).addTo(map);
                
                var xeIcon = L.icon({{
                    iconUrl: 'https://cdn-icons-png.flaticon.com/512/252/252025.png',
                    iconSize: [44, 44],
                    iconAnchor: [22, 44],
                    popupAnchor: [0, -44]
                }});
                
                var marker = L.marker([{self.current_lat}, {self.current_lon}], {{icon: xeIcon}}).addTo(map);
                marker.bindPopup('<b>📍 Current Location</b><br><small>Click to open live camera</small>');
                
                var latlngs = [[{self.current_lat}, {self.current_lon}]];
                var polyline = L.polyline(latlngs, {{color: '#3498db', weight: 4}}).addTo(map);
                
                // Setup WebChannel
                new QWebChannel(qt.webChannelTransport, function(channel) {{
                    window.bridge = channel.objects.bridge;
                    
                    // Marker click event
                    marker.on('click', function() {{
                        console.log('Marker clicked!');
                        if (window.bridge) {{
                            window.bridge.openCamera();
                        }}
                    }});
                }});
                
                function updateGPS(lat, lon) {{
                    marker.setLatLng([lat, lon]);
                    latlngs.push([lat, lon]);
                    polyline.setLatLngs(latlngs);
                    map.setView([lat, lon], 16);
                }}
                
                function clearHistory() {{
                    latlngs = [[marker.getLatLng().lat, marker.getLatLng().lng]];
                    polyline.setLatLngs(latlngs);
                }}
            </script>
        </body>
        </html>
        """
        self.map_view.setHtml(html)
        
        # Setup WebChannel Bridge
        class Bridge(QObject):
            def __init__(self, parent):
                super().__init__()
                self.parent = parent
            
            @pyqtSlot()
            def openCamera(self):
                logger.info("Bridge: openCamera called")
                self.parent.open_camera_from_marker()
        
        self.bridge = Bridge(self)
        self.channel = QWebChannel()
        self.channel.registerObject('bridge', self.bridge)
        self.map_view.page().setWebChannel(self.channel)
    
    def start_mqtt(self):
        self.mqtt_thread = MQTTThread(self.THINGSBOARD_HOST, self.ACCESS_TOKEN)
        self.mqtt_thread.gps_update.connect(self.on_gps_update)
        self.mqtt_thread.connection_status.connect(self.on_mqtt_status)
        self.mqtt_thread.start()
    
    def on_gps_update(self, lat, lon):
        self.current_lat = lat
        self.current_lon = lon
        self.gps_history.append((lat, lon))
        
        self.gps_label.setText(f"📍 Lat: {lat:.6f} | Lon: {lon:.6f}")
        now = datetime.now().strftime("%H:%M:%S")
        self.update_label.setText(f"{now}")
        
        if self.auto_follow:
            self.map_view.page().runJavaScript(f"updateGPS({lat}, {lon});")
    
    def on_mqtt_status(self, connected, message):
        if connected:
            self.status_label.setText(f"🟢 {message}")
            self.status_label.setStyleSheet("""
                background: rgba(46,204,113,0.2); 
                color: #2ecc71; 
                padding: 8px 15px; 
                border-radius: 4px; 
                font-weight: 600;
                font-size: 13px;
            """)
        else:
            self.status_label.setText(f"🔴 {message}")
            self.status_label.setStyleSheet("""
                background: rgba(231,76,60,0.2); 
                color: #e74c3c; 
                padding: 8px 15px; 
                border-radius: 4px; 
                font-weight: 600;
                font-size: 13px;
            """)
    
    def clear_history(self):
        self.gps_history = []
        self.map_view.page().runJavaScript("clearHistory();")
        logger.info("GPS history cleared")
    
    def toggle_follow(self):
        self.auto_follow = not self.auto_follow
        if self.auto_follow:
            self.follow_btn.setText("📍 Auto Follow: ON")
            self.follow_btn.setStyleSheet("""
                QPushButton {
                    background: #27ae60; 
                    color: white; 
                    padding: 8px 20px; 
                    border: none;
                    border-radius: 4px; 
                    font-weight: bold;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background: #229954;
                }
            """)
        else:
            self.follow_btn.setText("📍 Auto Follow: OFF")
            self.follow_btn.setStyleSheet("""
                QPushButton {
                    background: #95a5a6; 
                    color: white; 
                    padding: 8px 20px; 
                    border: none;
                    border-radius: 4px; 
                    font-weight: bold;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background: #7f8c8d;
                }
            """)
    
    def open_camera_from_marker(self):
        """Called when marker is clicked"""
        logger.info("Opening camera dialog...")
        
        # Close existing dialog if any
        if self.camera_dialog:
            self.camera_dialog.close()
        
        # Create and show new camera dialog
        self.camera_dialog = CameraDialog(self, self.RTSP_URL)
        self.camera_dialog.show()
    
    def closeEvent(self, event):
        if self.mqtt_thread:
            self.mqtt_thread.stop()
            self.mqtt_thread.wait()
        if self.camera_dialog:
            self.camera_dialog.close()
        event.accept()

# ==================== Main ====================
def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern look
    window = GPSCameraApp()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()