import sys
import os
import json
import logging
import time
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QDialog
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QObject, pyqtSlot, QMutex
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtGui import QImage, QPixmap, QFont
import websocket
import cv2
import numpy as np

logging.basicConfig(level=logging.INFO, format="[%(asctime)s][%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ============ WebSocket Thread ============
class ThingsBoardWSThread(QThread):
    gps_update = pyqtSignal(float, float)
    connection_status = pyqtSignal(bool, str)
    
    def __init__(self, jwt_token, device_id):
        super().__init__()
        self.jwt_token = jwt_token
        self.device_id = device_id
        self.ws = None
        self.running = True
        self.url = f"wss://demo.thingsboard.io/api/ws/plugins/telemetry?token={jwt_token}"
    
    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            logger.info("=" * 60)
            logger.info(f"WebSocket Message Received:")
            logger.info(f"   Data: {data}")
            
            if isinstance(data, dict) and 'data' in data:
                telemetry = data['data']
                logger.info(f"   Telemetry: {telemetry}")
                
                if ('gps_latitude' in telemetry and 'gps_longitude' in telemetry 
                    and telemetry['gps_latitude'] and telemetry['gps_longitude']):
                    
                    gps_latitude = telemetry['gps_latitude'][0][1]
                    gps_longitude = telemetry['gps_longitude'][0][1]
                    
                    lat = float(gps_latitude)
                    lon = float(gps_longitude)
                    
                    logger.info(f"GPS Extracted: Lat={lat}, Lon={lon}")
                    logger.info("=" * 60 + "\n")
                    self.gps_update.emit(lat, lon)
                else:
                    logger.warning(f"GPS data not found in telemetry")
                    logger.warning(f"   Available keys: {list(telemetry.keys())}")
                    logger.info("=" * 60 + "\n")
            else:
                logger.warning(f"Message format unexpected: {data}")
                logger.info("=" * 60 + "\n")
                
        except Exception as e:
            logger.error(f"Error parsing WebSocket message: {e}")
            logger.info("=" * 60 + "\n")
    
    def on_error(self, ws, error):
        logger.error(f"WebSocket error: {error}")
        self.connection_status.emit(False, f"Error: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        logger.warning(f"WebSocket closed: code={close_status_code}, msg={close_msg}")
        self.connection_status.emit(False, "Disconnected from Server")
    
    def on_open(self, ws):
        logger.info("WebSocket connected!")
        self.connection_status.emit(True, "Connected to Server")
        
        sub_cmd = {
            "tsSubCmds": [
                {
                    "entityType": "DEVICE",
                    "entityId": self.device_id,
                    "scope": "LATEST_TELEMETRY",
                    "cmdId": 1
                }
            ],
            "historyCmds": [],
            "attrSubCmds": []
        }
        ws.send(json.dumps(sub_cmd))
        logger.info(f"Sent subscribe command for device: {self.device_id}")
    
    def run(self):
        while self.running:
            try:
                logger.info(f"Connecting to WebSocket...")
                self.ws = websocket.WebSocketApp(
                    self.url,
                    on_message=self.on_message,
                    on_error=self.on_error,
                    on_close=self.on_close,
                    on_open=self.on_open
                )
                self.ws.run_forever()
            except Exception as e:
                logger.error(f"WebSocket connection error: {e}")
                self.connection_status.emit(False, f"Connection Error: {e}")
            
            if self.running:
                logger.info("Reconnecting in 5 seconds...")
                time.sleep(5)
    
    def stop(self):
        self.running = False
        if self.ws:
            self.ws.close()

# ============ IMPROVED RTSP Thread with Better Error Handling ============
class RTSPThread(QThread):
    frame_ready = pyqtSignal(QImage)
    connection_status = pyqtSignal(bool, str)
    
    def __init__(self, rtsp_url):
        super().__init__()
        self.rtsp_url = rtsp_url
        self.running = False
        self.mutex = QMutex()
        self.cap = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 3
        
    def run(self):
        self.running = True
        self.reconnect_attempts = 0
        
        while self.running and self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                logger.info(f"Attempting to connect to RTSP stream... (Attempt {self.reconnect_attempts + 1})")
                if self.cap is not None:
                    self.cap.release()
                    time.sleep(0.5)
                self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                self.cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
                self.cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)
                
                if not self.cap.isOpened():
                    logger.error("Cannot connect to RTSP stream")
                    self.connection_status.emit(False, "Cannot connect to camera")
                    self.reconnect_attempts += 1
                    time.sleep(2)
                    continue
                
                self.connection_status.emit(True, "Camera connected")
                logger.info("RTSP stream connected successfully")
                self.reconnect_attempts = 0  
                
                consecutive_failures = 0
                max_consecutive_failures = 30 
                
                while self.running:
                    try:
                        self.mutex.lock()
                        if self.cap is None or not self.cap.isOpened():
                            self.mutex.unlock()
                            break
                        
                        ret, frame = self.cap.read()
                        self.mutex.unlock()
                        
                        if ret and frame is not None:
                            consecutive_failures = 0
                            
                            try:
                        
                                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                                h, w, ch = rgb_frame.shape
                                
                                if h > 0 and w > 0:
                                    bytes_per_line = ch * w
                                    qt_image = QImage(
                                        rgb_frame.data, 
                                        w, h, 
                                        bytes_per_line, 
                                        QImage.Format.Format_RGB888
                                    ).copy()  
                                    
                                    self.frame_ready.emit(qt_image)
                            except Exception as e:
                                logger.warning(f"Frame processing error: {e}")
                                consecutive_failures += 1
                        else:
                            consecutive_failures += 1
                            logger.warning(f"Failed to read frame (consecutive failures: {consecutive_failures})")
                            
                            if consecutive_failures >= max_consecutive_failures:
                                logger.error(f"Too many consecutive failures ({consecutive_failures}), reconnecting...")
                                break
                        
                        time.sleep(0.033)  # ~30 FPS
                        
                    except Exception as e:
                        logger.error(f"Error in frame reading loop: {e}")
                        consecutive_failures += 1
                        if consecutive_failures >= max_consecutive_failures:
                            break
                        time.sleep(0.1)

                logger.info("Exiting frame reading loop, cleaning up...")
                self.mutex.lock()
                if self.cap is not None:
                    self.cap.release()
                    self.cap = None
                self.mutex.unlock()
                
                if self.running:
                    self.reconnect_attempts += 1
                    if self.reconnect_attempts < self.max_reconnect_attempts:
                        logger.info(f"Reconnecting in 3 seconds... (Attempt {self.reconnect_attempts + 1}/{self.max_reconnect_attempts})")
                        self.connection_status.emit(False, f"Reconnecting... ({self.reconnect_attempts}/{self.max_reconnect_attempts})")
                        time.sleep(3)
                    
            except Exception as e:
                logger.error(f"RTSP Thread error: {e}")
                self.reconnect_attempts += 1
                if self.running and self.reconnect_attempts < self.max_reconnect_attempts:
                    time.sleep(2)

        self.mutex.lock()
        if self.cap is not None:
            try:
                self.cap.release()
            except:
                pass
            self.cap = None
        self.mutex.unlock()
        
        logger.info("RTSP thread stopped")
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            self.connection_status.emit(False, "Max reconnection attempts reached")
    
    def stop(self):
        logger.info("Stopping RTSP thread...")
        self.running = False
        self.mutex.lock()
        if self.cap is not None:
            try:
                self.cap.release()
            except:
                pass
            self.cap = None
        self.mutex.unlock()

# ============ Camera Dialog ============
class CameraDialog(QDialog):
    def __init__(self, parent=None, rtsp_url=""):
        super().__init__(parent)
        self.setWindowTitle("📹 Live Camera Stream")
        self.setModal(False)
        self.resize(1280, 800)
        self.rtsp_url = rtsp_url
        self.rtsp_thread = None
        self.init_ui()
        self.start_camera()
        
    def init_ui(self):
        self.setStyleSheet("""
            QDialog { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #232526, stop:1 #485563); 
                border-radius: 18px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = QWidget()
        header.setStyleSheet("background: #29323c; padding: 14px; border-top-left-radius: 18px; border-top-right-radius: 18px;")
        header_layout = QHBoxLayout(header)
        
        title = QLabel("📹 Live Camera Stream")
        title.setStyleSheet("color: white; font-size: 19px; font-weight: bold; letter-spacing:1px;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        self.status_label = QLabel("⚪ Connecting...")
        self.status_label.setStyleSheet("color: #ecf0f1; font-size: 15px; padding: 7px 16px; background: rgba(255,255,255,0.07); border-radius: 7px;")
        header_layout.addWidget(self.status_label)
        
        close_btn = QPushButton("✖ Close")
        close_btn.clicked.connect(self.close_camera)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #e74c3c;
                color: white;
                padding: 10px 28px;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                font-size: 15px;
                margin-left: 10px;
            }
            QPushButton:hover {
                background: #c0392b;
            }
        """)
        header_layout.addWidget(close_btn)
        layout.addWidget(header)
        
        # Video display
        self.video_label = QLabel()
        self.video_label.setStyleSheet("background: #151c24; border-bottom-left-radius: 18px; border-bottom-right-radius: 18px;")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(1200, 700)
        layout.addWidget(self.video_label)
        
    def start_camera(self):
        self.rtsp_thread = RTSPThread(self.rtsp_url)
        self.rtsp_thread.frame_ready.connect(self.display_frame)
        self.rtsp_thread.connection_status.connect(self.on_camera_status)
        self.rtsp_thread.start()
        
    def display_frame(self, image):
        try:
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
        except Exception as e:
            logger.error(f"Error displaying frame: {e}")
            
    def on_camera_status(self, connected, message):
        if connected:
            self.status_label.setText(f"🟢 {message}")
            self.status_label.setStyleSheet("color: #2ecc71; font-size: 15px; padding: 7px 16px; background: rgba(46,204,113,0.11); border-radius: 7px;")
        else:
            self.status_label.setText(f"🔴 {message}")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 15px; padding: 7px 16px; background: rgba(231,76,60,0.11); border-radius: 7px;")
            
    def close_camera(self):
        logger.info("Closing camera dialog...")
        if self.rtsp_thread:
            self.rtsp_thread.stop()
            self.rtsp_thread.wait(3000)  
            if self.rtsp_thread.isRunning():
                logger.warning("Force terminating RTSP thread")
                self.rtsp_thread.terminate()
        self.close()
        
    def closeEvent(self, event):
        logger.info("Camera dialog closeEvent triggered")
        if self.rtsp_thread:
            self.rtsp_thread.stop()
            self.rtsp_thread.wait(3000)
            if self.rtsp_thread.isRunning():
                self.rtsp_thread.terminate()
        event.accept()

# ============ Main Window ============
class GPSCameraApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GPS Tracking & Camera Viewer")
        self.setGeometry(60, 30, 1440, 850)
        
        # ===== CONFIG =====
        self.JWT_TOKEN = "eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJ2dmFuaDIxMDIwM0BnbWFpbC5jb20iLCJ1c2VySWQiOiJiNWVmYjdmMC00YTJmLTExZjAtOTY2NC1mZjEzZWNjYjQ3ZmYiLCJzY29wZXMiOlsiVEVOQU5UX0FETUlOIl0sInNlc3Npb25JZCI6ImNmNmRhYTU0LTQzNGUtNDgzMC1hYjgyLTY5NjFjNmU2NzI1MSIsImV4cCI6MTc2MjE3ODQ4NCwiaXNzIjoidGhpbmdzYm9hcmQuaW8iLCJpYXQiOjE3NjAzNzg0ODQsImZpcnN0TmFtZSI6IkFuaCIsImxhc3ROYW1lIjoiVsWpIiwiZW5hYmxlZCI6dHJ1ZSwicHJpdmFjeVBvbGljeUFjY2VwdGVkIjp0cnVlLCJpc1B1YmxpYyI6ZmFsc2UsInRlbmFudElkIjoiYjVjMzUwYzAtNGEyZi0xMWYwLTk2NjQtZmYxM2VjY2I0N2ZmIiwiY3VzdG9tZXJJZCI6IjEzODE0MDAwLTFkZDItMTFiMi04MDgwLTgwODA4MDgwODA4MCJ9.V1UF2qYI9R_ucDtcZglRcybLdbGKDhCkH_nQrduisaqJwWM-048TLvew9QgYV58dk5RCv7_1lxE8WeFfJnik3g"
        self.DEVICE_ID = "afe86c60-8f3c-11f0-a9b5-792e2194a5d4"
        self.RTSP_URL = "rtsp://admin:Abcd121%40@113.185.6.120:8554/Streaming/Channels/101"
        # self.RTSP_URL = "rtsp://admin:Abcd121%40@10.42.0.68:8554/Streaming/Channels/101"
        self.VIETMAP_API_KEY = "2eada1a08ba9a656491f1e14cc0224ee5ea4d611c8adae41"
        
        self.current_lat = 21.028667
        self.current_lon = 105.805050
        self.gps_history = []
        self.is_connected = False
        self.camera_dialog = None
        self.auto_follow = True
        self.init_ui()
        self.start_websocket()
        
    def init_ui(self):
        app_font = QFont("Inter", 13)
        QApplication.instance().setFont(app_font)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.map_view = QWebEngineView()
        self.map_view.setStyleSheet("border-radius: 0px;")
        self.load_map()
        main_layout.addWidget(self.map_view)
        
        self.floating_card = QFrame(self.map_view)
        self.floating_card.setStyleSheet("""
            QFrame {
                background: rgba(255,255,255,0.98);
                border-radius: 18px;
                border: 1.5px solid #E5EAF0;
            }
        """)
        self.floating_card.setGeometry(30, 24, 430, 270)
        card_layout = QVBoxLayout(self.floating_card)
        card_layout.setContentsMargins(22, 18, 22, 16)
        card_layout.setSpacing(13)
        
        status_row = QHBoxLayout()
        self.status_icon = QLabel("🔵")
        self.status_icon.setStyleSheet("font-size: 20px;")
        status_row.addWidget(self.status_icon)
        self.status_label = QLabel("Connecting...")
        self.status_label.setStyleSheet("color: #f39c12; font-size: 17px; font-weight: 600; margin-left:6px;")
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        card_layout.addLayout(status_row)
        
        self.update_label = QLabel("Latest Updated: --:--:-- --/--/----")
        self.update_label.setStyleSheet("color: #227be5; font-size: 15px; font-weight: 500; margin-left: 4px;")
        card_layout.addWidget(self.update_label)
        
        self.gps_label = QLabel("Lat: --- | Lon: ---")
        self.gps_label.setStyleSheet("color: #222; font-size: 15px; font-weight: 500;")
        card_layout.addWidget(self.gps_label)
        
        btn_row = QVBoxLayout()
        
        self.follow_btn = QPushButton("Auto Follow: ON")
        self.follow_btn.setFixedSize(400,40)
        self.follow_btn.setStyleSheet("""
            QPushButton {
                background: #9b59b6;
                color: white;
                padding: 13px 0;
                border: none;
                border-radius: 9px;
                font-size: 15px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #8e44ad;
            }
        """)
        self.follow_btn.clicked.connect(self.toggle_auto_follow)
        btn_row.addWidget(self.follow_btn)
        
        self.clear_btn = QPushButton("Clear history")
        self.clear_btn.setFixedSize(400, 40)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background: #2979ff;
                color: white;
                padding: 13px 0;
                border: none;
                border-radius: 9px;
                font-size: 15px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #1769aa;
            }
        """)
        self.clear_btn.clicked.connect(self.clear_history)
        btn_row.addWidget(self.clear_btn)
        
        self.update_btn = QPushButton("Update current position")
        self.update_btn.setFixedSize(400,40)
        self.update_btn.setStyleSheet("""
            QPushButton {
                background: #43c465;
                color: white;
                padding: 13px 0;
                border: none;
                border-radius: 9px;
                font-size: 15px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #229954;
            }
        """)
        self.update_btn.clicked.connect(self.update_map_to_current_pos)
        btn_row.addWidget(self.update_btn)
        
        card_layout.addLayout(btn_row)
        self.floating_card.show()

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
                body {{ margin: 0; padding: 0; background: #f8faff; }}
                #map {{ width: 100vw; height: 100vh; }}
                .leaflet-popup-content-wrapper, .leaflet-popup-tip {{
                    border-radius: 10px;
                    background: #fff;
                }}
            </style>
        </head>
        <body>
            <div id="map"></div>
            <script>
                var map = L.map('map').setView([{self.current_lat}, {self.current_lon}], 16);
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
                new QWebChannel(qt.webChannelTransport, function(channel) {{
                    window.bridge = channel.objects.bridge;
                    marker.on('click', function() {{
                        if (window.bridge) window.bridge.openCamera();
                    }});
                }});
                function updateGPS(lat, lon) {{
                    marker.setLatLng([lat, lon]);
                    latlngs.push([lat, lon]);
                    polyline.setLatLngs(latlngs);
                }}
                function centerMap(lat, lon) {{
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
        
        class Bridge(QObject):
            def __init__(self, parent):
                super().__init__()
                self.parent = parent
            @pyqtSlot()
            def openCamera(self):
                self.parent.open_camera_from_marker()
                
        self.bridge = Bridge(self)
        self.channel = QWebChannel()
        self.channel.registerObject('bridge', self.bridge)
        self.map_view.page().setWebChannel(self.channel)

    def start_websocket(self):
        self.ws_thread = ThingsBoardWSThread(self.JWT_TOKEN, self.DEVICE_ID)
        self.ws_thread.gps_update.connect(self.on_gps_update)
        self.ws_thread.connection_status.connect(self.on_connection_status)
        self.ws_thread.start()

    def on_gps_update(self, lat, lon):
        self.current_lat = lat
        self.current_lon = lon
        self.gps_history.append((lat, lon))
        self.gps_label.setText(f"Lat: {lat:.6f} | Lon: {lon:.6f}")
        now = datetime.now().strftime("%H:%M:%S %d/%m/%Y")
        self.update_label.setText(f"Latest Updated: {now}")
        
        self.map_view.page().runJavaScript(f"updateGPS({lat}, {lon});")
        
        if self.auto_follow:
            self.map_view.page().runJavaScript(f"centerMap({lat}, {lon});")
    
    def toggle_auto_follow(self):
        self.auto_follow = not self.auto_follow
        if self.auto_follow:
            self.follow_btn.setText("Auto Follow: ON")
            self.follow_btn.setStyleSheet("""
                QPushButton {
                    background: #9b59b6;
                    color: white;
                    padding: 13px 0;
                    border: none;
                    border-radius: 9px;
                    font-size: 15px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: #8e44ad;
                }
            """)
            self.map_view.page().runJavaScript(f"centerMap({self.current_lat}, {self.current_lon});")
        else:
            self.follow_btn.setText("Auto Follow: OFF")
            self.follow_btn.setStyleSheet("""
                QPushButton {
                    background: #95a5a6;
                    color: white;
                    padding: 13px 0;
                    border: none;
                    border-radius: 9px;
                    font-size: 15px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: #7f8c8d;
                }
            """)

    def on_connection_status(self, connected, message):
        self.is_connected = connected
        if connected:
            self.status_icon.setText("🟢")
            self.status_label.setText("Connected to Server")
            self.status_label.setStyleSheet("color: #1ca431; font-size: 17px; font-weight: 600; margin-left:6px;")
        else:
            self.status_icon.setText("🔴")
            self.status_label.setText("Disconnected")
            self.status_label.setStyleSheet("color: #c0392b; font-size: 17px; font-weight: 600; margin-left:6px;")

    def clear_history(self):
        self.gps_history = []
        self.map_view.page().runJavaScript("clearHistory();")
        logger.info("GPS history cleared")

    def update_map_to_current_pos(self):
        self.map_view.page().runJavaScript(f"centerMap({self.current_lat}, {self.current_lon});")

    def open_camera_from_marker(self):
        logger.info("Opening camera from marker...")
        if self.camera_dialog and self.camera_dialog.isVisible():
            logger.info("Camera dialog already open")
            return
            
        if self.camera_dialog:
            self.camera_dialog.close()
            
        self.camera_dialog = CameraDialog(self, self.RTSP_URL)
        self.camera_dialog.show()

    def closeEvent(self, event):
        logger.info("Main window closing...")
        if hasattr(self, "ws_thread") and self.ws_thread:
            self.ws_thread.stop()
            self.ws_thread.wait(3000)
            
        if self.camera_dialog:
            self.camera_dialog.close()
            
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;tcp'
    
    window = GPSCameraApp()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()