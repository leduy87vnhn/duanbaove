import sys
import os
import json
import logging
import time
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QDialog, QGridLayout
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

# ============ RTSP Thread ============
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
                        
                        time.sleep(0.033)
                        
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
    def __init__(self, parent=None, rtsp_url="", camera_name="Camera"):
        super().__init__(parent)
        self.setWindowTitle(f"📹 {camera_name}")
        self.setModal(False)
        self.resize(1280, 800)
        self.rtsp_url = rtsp_url
        self.camera_name = camera_name
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
        
        title = QLabel(f"📹 {self.camera_name}")
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
# ============ Dual Camera Dialog ============
class DualCameraDialog(QDialog):
    def __init__(self, parent=None, rtsp_url_1="", rtsp_url_2="", dialog_name="Dual Camera"):
        super().__init__(parent)
        self.setWindowTitle(f"📹 {dialog_name}")
        self.setModal(False)
        self.resize(1920, 800)
        self.rtsp_url_1 = rtsp_url_1
        self.rtsp_url_2 = rtsp_url_2
        self.dialog_name = dialog_name
        self.rtsp_thread_1 = None
        self.rtsp_thread_2 = None
        self.init_ui()
        self.start_cameras()
        
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
        
        title = QLabel(f"📹 {self.dialog_name}")
        title.setStyleSheet("color: white; font-size: 19px; font-weight: bold; letter-spacing:1px;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        self.status_label_1 = QLabel("⚪ Camera 1: Connecting...")
        self.status_label_1.setStyleSheet("color: #ecf0f1; font-size: 14px; padding: 7px 16px; background: rgba(255,255,255,0.07); border-radius: 7px; margin-right: 10px;")
        header_layout.addWidget(self.status_label_1)
        
        self.status_label_2 = QLabel("⚪ Camera 2: Connecting...")
        self.status_label_2.setStyleSheet("color: #ecf0f1; font-size: 14px; padding: 7px 16px; background: rgba(255,255,255,0.07); border-radius: 7px;")
        header_layout.addWidget(self.status_label_2)
        
        close_btn = QPushButton("✖ Close")
        close_btn.clicked.connect(self.close_cameras)
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
        
        # Video display area - 2 videos side by side
        video_container = QWidget()
        video_container.setStyleSheet("background: #151c24; border-bottom-left-radius: 18px; border-bottom-right-radius: 18px;")
        video_layout = QHBoxLayout(video_container)
        video_layout.setContentsMargins(10, 10, 10, 10)
        video_layout.setSpacing(10)
        
        # Camera 1
        cam1_frame = QFrame()
        cam1_frame.setStyleSheet("background: #1a2332; border-radius: 8px; border: 2px solid #3498db;")
        cam1_layout = QVBoxLayout(cam1_frame)
        cam1_layout.setContentsMargins(5, 5, 5, 5)
        
        cam1_title = QLabel("📹 Camera 1")
        cam1_title.setStyleSheet("color: #3498db; font-size: 16px; font-weight: bold; padding: 5px;")
        cam1_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cam1_layout.addWidget(cam1_title)
        
        self.video_label_1 = QLabel()
        self.video_label_1.setStyleSheet("background: #0d1117; border-radius: 5px;")
        self.video_label_1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label_1.setMinimumSize(900, 650)
        cam1_layout.addWidget(self.video_label_1)
        
        video_layout.addWidget(cam1_frame)
        
        # Camera 2
        cam2_frame = QFrame()
        cam2_frame.setStyleSheet("background: #1a2332; border-radius: 8px; border: 2px solid #e74c3c;")
        cam2_layout = QVBoxLayout(cam2_frame)
        cam2_layout.setContentsMargins(5, 5, 5, 5)
        
        cam2_title = QLabel("📹 Camera 2 - Drone")
        cam2_title.setStyleSheet("color: #e74c3c; font-size: 16px; font-weight: bold; padding: 5px;")
        cam2_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cam2_layout.addWidget(cam2_title)
        
        self.video_label_2 = QLabel()
        self.video_label_2.setStyleSheet("background: #0d1117; border-radius: 5px;")
        self.video_label_2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label_2.setMinimumSize(900, 650)
        cam2_layout.addWidget(self.video_label_2)
        
        video_layout.addWidget(cam2_frame)
        
        layout.addWidget(video_container)
        
    def start_cameras(self):
        # Start Camera 1
        self.rtsp_thread_1 = RTSPThread(self.rtsp_url_1)
        self.rtsp_thread_1.frame_ready.connect(self.display_frame_1)
        self.rtsp_thread_1.connection_status.connect(self.on_camera_status_1)
        self.rtsp_thread_1.start()
        
        # Start Camera 2
        self.rtsp_thread_2 = RTSPThread(self.rtsp_url_2)
        self.rtsp_thread_2.frame_ready.connect(self.display_frame_2)
        self.rtsp_thread_2.connection_status.connect(self.on_camera_status_2)
        self.rtsp_thread_2.start()
        
    def display_frame_1(self, image):
        try:
            label_width = self.video_label_1.width()
            label_height = self.video_label_1.height()
            
            scaled_pixmap = QPixmap.fromImage(image).scaled(
                label_width, label_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation
            )
            self.video_label_1.setPixmap(scaled_pixmap)
        except Exception as e:
            logger.error(f"Error displaying frame 1: {e}")
            
    def display_frame_2(self, image):
        try:
            label_width = self.video_label_2.width()
            label_height = self.video_label_2.height()
            
            scaled_pixmap = QPixmap.fromImage(image).scaled(
                label_width, label_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation
            )
            self.video_label_2.setPixmap(scaled_pixmap)
        except Exception as e:
            logger.error(f"Error displaying frame 2: {e}")
            
    def on_camera_status_1(self, connected, message):
        if connected:
            self.status_label_1.setText(f"🟢 Camera 1: {message}")
            self.status_label_1.setStyleSheet("color: #2ecc71; font-size: 14px; padding: 7px 16px; background: rgba(46,204,113,0.11); border-radius: 7px; margin-right: 10px;")
        else:
            self.status_label_1.setText(f"🔴 Camera 1: {message}")
            self.status_label_1.setStyleSheet("color: #e74c3c; font-size: 14px; padding: 7px 16px; background: rgba(231,76,60,0.11); border-radius: 7px; margin-right: 10px;")
            
    def on_camera_status_2(self, connected, message):
        if connected:
            self.status_label_2.setText(f"🟢 Camera 2: {message}")
            self.status_label_2.setStyleSheet("color: #2ecc71; font-size: 14px; padding: 7px 16px; background: rgba(46,204,113,0.11); border-radius: 7px;")
        else:
            self.status_label_2.setText(f"🔴 Camera 2: {message}")
            self.status_label_2.setStyleSheet("color: #e74c3c; font-size: 14px; padding: 7px 16px; background: rgba(231,76,60,0.11); border-radius: 7px;")
            
    def close_cameras(self):
        logger.info("Closing dual camera dialog...")
        if self.rtsp_thread_1:
            self.rtsp_thread_1.stop()
            self.rtsp_thread_1.wait(3000)
            if self.rtsp_thread_1.isRunning():
                self.rtsp_thread_1.terminate()
        if self.rtsp_thread_2:
            self.rtsp_thread_2.stop()
            self.rtsp_thread_2.wait(3000)
            if self.rtsp_thread_2.isRunning():
                self.rtsp_thread_2.terminate()
        self.close()
        
    def closeEvent(self, event):
        logger.info("Dual camera dialog closeEvent triggered")
        if self.rtsp_thread_1:
            self.rtsp_thread_1.stop()
            self.rtsp_thread_1.wait(3000)
            if self.rtsp_thread_1.isRunning():
                self.rtsp_thread_1.terminate()
        if self.rtsp_thread_2:
            self.rtsp_thread_2.stop()
            self.rtsp_thread_2.wait(3000)
            if self.rtsp_thread_2.isRunning():
                self.rtsp_thread_2.terminate()
        event.accept()
# ============ Multi-Camera Monitoring System ============
class MonitoringSystemUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hệ Thống Giám Sát Bảo Vệ Đưa Đón Cán Bộ")
        self.setGeometry(50, 50, 1600, 900)
        self.setStyleSheet("background: #3B4E2B;")
        
        # Config
        self.JWT_TOKEN = "eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJ2dmFuaDIxMDIwM0BnbWFpbC5jb20iLCJ1c2VySWQiOiJiNWVmYjdmMC00YTJmLTExZjAtOTY2NC1mZjEzZWNjYjQ3ZmYiLCJzY29wZXMiOlsiVEVOQU5UX0FETUlOIl0sInNlc3Npb25JZCI6ImNmNmRhYTU0LTQzNGUtNDgzMC1hYjgyLTY5NjFjNmU2NzI1MSIsImV4cCI6MTc2MjE3ODQ4NCwiaXNzIjoidGhpbmdzYm9hcmQuaW8iLCJpYXQiOjE3NjAzNzg0ODQsImZpcnN0TmFtZSI6IkFuaCIsImxhc3ROYW1lIjoiVsWpIiwiZW5hYmxlZCI6dHJ1ZSwicHJpdmFjeVBvbGljeUFjY2VwdGVkIjp0cnVlLCJpc1B1YmxpYyI6ZmFsc2UsInRlbmFudElkIjoiYjVjMzUwYzAtNGEyZi0xMWYwLTk2NjQtZmYxM2VjY2I0N2ZmIiwiY3VzdG9tZXJJZCI6IjEzODE0MDAwLTFkZDItMTFiMi04MDgwLTgwODA4MDgwODA4MCJ9.V1UF2qYI9R_ucDtcZglRcybLdbGKDhCkH_nQrduisaqJwWM-048TLvew9QgYV58dk5RCv7_1lxE8WeFfJnik3g"
        self.DEVICE_ID = "afe86c60-8f3c-11f0-a9b5-792e2194a5d4"
        self.RTSP_URL = "rtsp://admin:Abcd121%40@113.185.6.120:8554/Streaming/Channels/101"
        self.VIETMAP_API_KEY = "2eada1a08ba9a656491f1e14cc0224ee5ea4d611c8adae41"
        
        self.current_lat = 21.028667
        self.current_lon = 105.805050
        self.camera_dialogs = {}
        self.CAMERA_URLS = {
            "Xe 1": "rtsp://admin:Abcd121%40@113.185.6.120:8554/Streaming/Channels/101",
            "Xe 2": "rtsp://admin:Abcd121%40@113.185.6.120:8554/Streaming/Channels/101",
            "Xe 3": "rtsp://admin:Abcd121%40@113.185.6.120:8554/Streaming/Channels/101",
            "Tram 1": "rtsp://admin:Abcd121%40@113.185.6.120:8554/Streaming/Channels/101",
            "Drone": " rtsp://42.112.164.38:554/live/1_0"
        }
        self.init_ui()
        self.start_websocket()

        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # ===== HEADER =====
        header = QLabel("Hệ Thống Giám Sát Bảo Vệ Đưa Đón Cán Bộ")
        header.setStyleSheet("""
            background:#3B4E2B;
            color: white;
            font-size: 26px;
            font-weight: bold;
            padding: 18px;
            border-radius: 8px;
            letter-spacing: 1px;
        """)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header)
        
        # ===== CONTENT AREA =====
        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)
        
        # ===== LEFT PANEL - Videos =====
        left_panel = QFrame()
        left_panel.setStyleSheet("""
            background: #3B4E2B;
            border-radius: 8px;
        """)
        left_panel.setFixedWidth(240)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(15, 15, 15, 15)
        left_layout.setSpacing(12)
        
        # Video feeds - clickable
        self.video_frames = []
        for i in range(1, 4):
            video_frame = QFrame()
            video_frame.setStyleSheet("""
                QFrame {
                    background: #FFE135;
                    border-radius: 8px;
                    border: 2px solid #222;
                }
                QFrame:hover {
                    background: #FFE860;
                    border: 2px solid #222;
                }
            """)
            video_frame.setFixedHeight(100)
            video_frame.setFixedWidth(200)
            video_frame.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # Make clickable
            video_frame.mousePressEvent = lambda event, idx=i: self.open_camera(f"Xe {idx}")
            
            video_layout = QVBoxLayout(video_frame)
            video_layout.setContentsMargins(0, 0, 0, 0)
            
            video_label = QLabel(f"📹 Video xe {i}\n\n(Click để xem)")
            video_label.setStyleSheet("""
                background: rgba(0,0,0,0.3);
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 8px;
            """)
            video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            video_layout.addWidget(video_label)
            
            left_layout.addWidget(video_frame)
            self.video_frames.append(video_frame)
        
        # Tram 3 section
        tram_frame = QFrame()
        tram_frame.setFixedSize(200,300);
        tram_frame.setStyleSheet("""
            background: #4B5320;
            border-radius: 8px;
            border: 2px solid #222;
        """)
        tram_layout = QVBoxLayout(tram_frame)
        tram_layout.setContentsMargins(12, 12, 12, 12)
        
        tram_label = QLabel("Tram 3")
        tram_label.setFixedSize(100,50)
        tram_label.setStyleSheet("""
            color: white;
            font-size: 18px;
            font-weight: bold;
        """)
        tram_layout.addWidget(tram_label)
        
        video_tram_frame = QFrame()
        video_tram_frame.setStyleSheet("""
            QFrame {
                background: #FFE135;
                border-radius: 6px;
                border: 2px solid #555;
            }
            QFrame:hover {
                background: #FFE860;
                border: 2px solid #555;
            }
        """)
        video_tram_frame.setCursor(Qt.CursorShape.PointingHandCursor)
        video_tram_frame.mousePressEvent = lambda event: self.open_camera("Tram 1")
        
        video_tram_layout = QVBoxLayout(video_tram_frame)
        video_tram_label = QLabel("📹 Video tram 1\n\n(Click để xem)")
        video_tram_label.setStyleSheet("""
            color: #333;
            font-size: 14px;
            font-weight: bold;
            padding: 45px 20px;
        """)
        video_tram_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        video_tram_layout.addWidget(video_tram_label)
        tram_layout.addWidget(video_tram_frame)
        
        left_layout.addWidget(tram_frame)
        left_layout.addStretch()
        
        content_layout.addWidget(left_panel)
        
        # ===== RIGHT PANEL - Map =====
        right_panel = QFrame()
        right_panel.setStyleSheet("""
            background: #9FD356;
            border-radius: 8px;
        """)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        # Map title - thanh nhỏ
        map_title = QLabel("THỰC ĐỊA")
        map_title.setFixedHeight(50)
        map_title.setStyleSheet("""
            background: rgba(0,0,0,0.15);
            color: #1E4A5F;
            font-size: 20px;
            font-weight: bold;
            padding: 8px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
        """)
        map_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(map_title)
        
        # Map view - chiếm hết phần còn lại
        self.map_view = QWebEngineView()
        self.map_view.setStyleSheet("border: 3px solid #1E4A5F; background: white;")
        self.load_map()
        right_layout.addWidget(self.map_view)
        
        content_layout.addWidget(right_panel)
        main_layout.addLayout(content_layout)
        
        # ===== BOTTOM PANEL =====
        bottom_panel = QFrame()
        bottom_panel.setStyleSheet("""
            background: #3B4E2B;
            border-radius: 8px;
        """)
        bottom_panel.setFixedHeight(80)
        
        bottom_layout = QHBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(20, 15, 20, 15)
        bottom_layout.setSpacing(15)
        
        # Connection status
        self.status_label = QLabel("🔵 Connecting to Server...")
        self.status_label.setStyleSheet("""
            color: #f39c12;
            font-size: 16px;
            font-weight: bold;
            padding: 10px 20px;
            background: rgba(255,255,255,0.1);
            border-radius: 6px;
        """)
        bottom_layout.addWidget(self.status_label)
        
        # GPS info
        self.gps_label = QLabel("📍 GPS: ---, ---")
        self.gps_label.setStyleSheet("""
            color: white;
            font-size: 15px;
            font-weight: 500;
            padding: 10px 20px;
            background: rgba(255,255,255,0.05);
            border-radius: 6px;
        """)
        bottom_layout.addWidget(self.gps_label)
        
        bottom_layout.addStretch()
        btn_clear_history = QPushButton("Xóa Đường Đi")
        btn_clear_history.setFixedSize(140, 50)
        btn_clear_history.clicked.connect(self.clear_route_history)
        btn_clear_history.setStyleSheet("""
            QPushButton {
                background: #e67e22;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #d35400;
            }
        """)
        bottom_layout.addWidget(btn_clear_history)

        bottom_layout.addStretch()
        # Action buttons
        btn_login = QPushButton("Đăng Nhập/\nĐăng Xuất")
        btn_login.setFixedSize(140, 50)
        btn_login.setStyleSheet("""
            QPushButton {
                background: #FF6B35;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #E85A2B;
            }
        """)
        bottom_layout.addWidget(btn_login)
        
        btn_submit = QPushButton("Ngô Văn Thiện\n(Thiếu Tá)")
        btn_submit.setFixedSize(140, 50)
        btn_submit.setStyleSheet("""
            QPushButton {
                background: #4ECDC4;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #3FB8AF;
            }
        """)
        bottom_layout.addWidget(btn_submit)
        
        main_layout.addWidget(bottom_panel)

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
                #map {{ width: 100%; height: 100vh; }}
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
                marker.bindPopup('<b>📍 Vị trí hiện tại</b><br><small>Nhấn để xem camera</small>');
                
                var latlngs = [[{self.current_lat}, {self.current_lon}]];
                var polyline = L.polyline(latlngs, {{color: '#3498db', weight: 4}}).addTo(map);
                
                new QWebChannel(qt.webChannelTransport, function(channel) {{
                    window.bridge = channel.objects.bridge;
                    marker.on('click', function() {{
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
                    console.log('Route history cleared');
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
        self.gps_label.setText(f"📍 GPS: {lat:.6f}, {lon:.6f}")
        self.map_view.page().runJavaScript(f"updateGPS({lat}, {lon});")

    def on_connection_status(self, connected, message):
        if connected:
            self.status_label.setText(f"🟢 {message}")
            self.status_label.setStyleSheet("""
                color: #1ca431;
                font-size: 16px;
                font-weight: bold;
                padding: 10px 20px;
                background: rgba(28,164,49,0.15);
                border-radius: 6px;
            """)
        else:
            self.status_label.setText(f"🔴 {message}")
            self.status_label.setStyleSheet("""
                color: #c0392b;
                font-size: 16px;
                font-weight: bold;
                padding: 10px 20px;
                background: rgba(192,57,43,0.15);
                border-radius: 6px;
            """)
    def clear_route_history(self):
        """Clear route history on map"""
        logger.info("Clearing route history...")
        self.map_view.page().runJavaScript("clearHistory();")

    def open_camera(self, camera_name):
        logger.info(f"Opening camera: {camera_name}")
        
        # Check if we should open dual camera
        if camera_name in self.camera_dialogs:
            if self.camera_dialogs[camera_name].isVisible():
                logger.info(f"Camera {camera_name} already open")
                return
            else:
                self.camera_dialogs[camera_name].close()
        
        # Get RTSP URLs
        rtsp_url_1 = self.CAMERA_URLS.get(camera_name, self.RTSP_URL)
        rtsp_url_2 = self.CAMERA_URLS.get("Drone", "rtsp://42.112.164.38:554/live/1_0")
        
        # Open dual camera dialog
        dual_camera_dialog = DualCameraDialog(self, rtsp_url_1, rtsp_url_2, f"{camera_name} + Drone")
        self.camera_dialogs[camera_name] = dual_camera_dialog
        dual_camera_dialog.show()
    
    def open_camera_from_marker(self):
        """Open dual camera dialog when marker is clicked"""
        logger.info("Opening dual cameras from marker click...")
        
        camera_name = "Camera Marker"
        
        if camera_name in self.camera_dialogs:
            if self.camera_dialogs[camera_name].isVisible():
                logger.info(f"Dual camera already open")
                return
            else:
                self.camera_dialogs[camera_name].close()
        
        rtsp_url_1 = self.RTSP_URL
        rtsp_url_2 = self.CAMERA_URLS.get("Drone", "rtsp://42.112.164.38:554/live/1_0")
        
        dual_camera_dialog = DualCameraDialog(self, rtsp_url_1, rtsp_url_2, "Xe + Drone View")
        self.camera_dialogs[camera_name] = dual_camera_dialog
        dual_camera_dialog.show()

    def closeEvent(self, event):
        logger.info("Main window closing...")
        
        # Stop websocket
        if hasattr(self, "ws_thread") and self.ws_thread:
            self.ws_thread.stop()
            self.ws_thread.wait(3000)
        
        # Close all camera dialogs
        for camera_dialog in self.camera_dialogs.values():
            if camera_dialog:
                camera_dialog.close()
        
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;tcp'
    window = MonitoringSystemUI()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()