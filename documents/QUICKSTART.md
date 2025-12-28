# Quick Start Guide - Stream Server

## Bước 1: Cài đặt FFmpeg (Windows)

### Tải về:
https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-full.7z

### Thêm vào PATH:
1. Giải nén vào `C:\ffmpeg`
2. Thêm `C:\ffmpeg\bin` vào System PATH
3. Restart PowerShell
4. Test: `ffmpeg -version`

## Bước 2: Cài đặt & Chạy Server

```powershell
# Vào thư mục backend
cd backend

# Cài đặt packages
npm install

# Chạy server
npm start
```

Server sẽ chạy tại: `http://localhost:8503`

## Bước 3: Sử dụng Stream

### Từ Web (cùng mạng LAN):
```
1. Mở browser: http://localhost:3000
2. Click "Start Stream"
3. Đợi 5 giây
4. Video sẽ tự động play
```

### Từ mạng khác hoặc Internet:
**Xem hướng dẫn chi tiết tại: [INTERNET_ACCESS.md](INTERNET_ACCESS.md)**

Quick options:
- **Port Forwarding**: Mở port 8503 trên router → `http://<IP_PUBLIC>:8503/hls/stream.m3u8`
- **Ngrok**: `ngrok http 8503` → `https://xxx.ngrok.io/hls/stream.m3u8`
- **VPS**: Deploy lên cloud server

### Từ Windows App (cùng mạng):
```
Stream URL: http://localhost:8503/hls/stream.m3u8

Hoặc từ máy khác trong LAN:
http://<IP_LOCAL>:8503/hls/stream.m3u8

Từ Internet (sau khi config):
http://<IP_PUBLIC>:8503/hls/stream.m3u8
```

## Bước 4: Test với VLC (Khuyến nghị)

```
1. Mở VLC Media Player
2. Media → Open Network Stream (Ctrl+N)
3. Nhập URL: http://localhost:8503/hls/stream.m3u8
4. Play
```

## API Endpoints:

```
POST http://localhost:8503/api/stream/start   # Bắt đầu stream
POST http://localhost:8503/api/stream/stop    # Dừng stream
GET  http://localhost:8503/api/stream/status  # Kiểm tra status
```

## Test bằng curl:

```powershell
# Start stream
curl -X POST http://localhost:8503/api/stream/start

# Check status
curl http://localhost:8503/api/stream/status

# Stop stream
curl -X POST http://localhost:8503/api/stream/stop
```

## Troubleshooting:

### Lỗi "ffmpeg not found":
- Kiểm tra PATH: `echo $env:PATH`
- Test ffmpeg: `ffmpeg -version`
- Restart PowerShell sau khi thêm PATH

### Stream không chạy:
- Kiểm tra RTSP URL trong `streamController.js`
- Kiểm tra camera có online không
- Xem log trong terminal

### Mở port cho máy khác truy cập:
```powershell
# Run as Administrator
New-NetFirewallRule -DisplayName "Stream Server" -Direction Inbound -LocalPort 8503 -Protocol TCP -Action Allow
```

## Ưu điểm:
- ✅ Buffer 40 giây → giảm lag
- ✅ Delay 5-10 giây là acceptable
- ✅ Hoạt động với mọi Windows app (VLC, C#, Python, etc.)
- ✅ HTTP-based → dễ qua firewall
- ✅ Không cần encode lại → tiết kiệm CPU
