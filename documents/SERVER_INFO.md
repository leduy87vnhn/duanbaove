# Stream Server - Thông tin truy cập

## 🌐 Thông tin Server

**IP Public:** `103.116.104.4`  
**Port:** `8503`

---

## 📺 Stream URLs

### HLS Stream (Dùng cho mọi thiết bị):
```
http://103.116.104.4:8503/hls/stream.m3u8
```

### API Endpoints:

**Start Stream:**
```bash
POST http://103.116.104.4:8503/api/stream/start
```

**Stop Stream:**
```bash
POST http://103.116.104.4:8503/api/stream/stop
```

**Check Status:**
```bash
GET http://103.116.104.4:8503/api/stream/status
```

**Get Info:**
```bash
GET http://103.116.104.4:8503/api/stream/info
```

---

## 🚀 Cách sử dụng nhanh

### 1. Test với VLC Media Player:
```
1. Mở VLC
2. Media → Open Network Stream (Ctrl+N)
3. Nhập URL: http://103.116.104.4:8503/hls/stream.m3u8
4. Play
```

### 2. Test bằng curl:
```bash
# Start stream
curl -X POST http://103.116.104.4:8503/api/stream/start

# Check status (đợi 3-5 giây)
curl http://103.116.104.4:8503/api/stream/status

# Stream sẽ có tại:
# http://103.116.104.4:8503/hls/stream.m3u8
```

### 3. Test bằng browser:
```
Mở: http://103.116.104.4:8503/hls/stream.m3u8
```

### 4. Từ smartphone (4G/WiFi):
```
1. Tải VLC for Mobile (iOS/Android)
2. Open Network Stream
3. Nhập: http://103.116.104.4:8503/hls/stream.m3u8
```

---

## 💻 Nhúng vào Windows Application

### C# WPF/WinForms (LibVLCSharp):
```csharp
const string STREAM_URL = "http://103.116.104.4:8503/hls/stream.m3u8";

// Start stream trước
var client = new HttpClient();
await client.PostAsync("http://103.116.104.4:8503/api/stream/start", null);

// Đợi 3 giây
await Task.Delay(3000);

// Play stream
var media = new Media(_libVLC, STREAM_URL, FromType.FromLocation);
_mediaPlayer.Play(media);
```

### Python:
```python
import vlc
import requests

STREAM_URL = "http://103.116.104.4:8503/hls/stream.m3u8"

# Start stream
requests.post('http://103.116.104.4:8503/api/stream/start')

# Wait and play
time.sleep(3)
player = vlc.MediaPlayer(STREAM_URL)
player.play()
```

### JavaScript/Web:
```javascript
const STREAM_URL = 'http://103.116.104.4:8503/hls/stream.m3u8';

// Start stream
await fetch('http://103.116.104.4:8503/api/stream/start', {
    method: 'POST'
});

// Wait
await new Promise(resolve => setTimeout(resolve, 3000));

// Play with HLS.js
const hls = new Hls();
hls.loadSource(STREAM_URL);
hls.attachMedia(video);
```

---

## ⚙️ Yêu cầu trên Server (103.116.104.4)

### 1. Firewall - Mở port 8503:
```powershell
# Windows Server - Run as Administrator
New-NetFirewallRule -DisplayName "Stream Server Public" `
  -Direction Inbound `
  -LocalPort 8503 `
  -Protocol TCP `
  -Action Allow `
  -Profile Any
```

### 2. Server phải chạy:
```powershell
cd d:\Projects\GiamSatBaoVe\code\duanbaove\backend
npm start
```

### 3. Kiểm tra server đang chạy:
```powershell
# Từ server
curl http://localhost:8503/api/stream/status

# Từ máy khác
curl http://103.116.104.4:8503/api/stream/status
```

---

## 🔧 Troubleshooting

### Không kết nối được:
```powershell
# Kiểm tra port có mở không
Test-NetConnection -ComputerName 103.116.104.4 -Port 8503

# Kiểm tra firewall
Get-NetFirewallRule -DisplayName "*Stream*"

# Kiểm tra server có đang chạy không
netstat -an | findstr 8503
```

### Stream không có video:
```bash
# 1. Kiểm tra status
curl http://103.116.104.4:8503/api/stream/status

# 2. Nếu isStreaming: false, start lại
curl -X POST http://103.116.104.4:8503/api/stream/start

# 3. Đợi 5 giây rồi thử lại
```

### Lag hoặc giật:
- Tăng buffer trong VLC: Tools → Preferences → Input/Codecs → Network caching: 3000ms
- Hoặc tăng buffer trong code (streamController.js): `hls_time: 6`, `hls_list_size: 15`

---

## 📱 Share link cho người khác

Gửi link này cho bất kỳ ai muốn xem:
```
http://103.116.104.4:8503/hls/stream.m3u8
```

**Lưu ý:** 
- Server phải đang chạy
- Stream phải được start (call API start)
- Đợi 3-5 giây sau khi start để segments được tạo

---

## 📊 Monitoring

### Xem log trên server:
```powershell
# Logs sẽ hiển thị trong terminal khi chạy npm start
# Hoặc nếu dùng PM2:
pm2 logs stream-server
```

### Kiểm tra segments đang được tạo:
```powershell
dir backend\resources\hls
```

---

## 🎯 Example Integration

### HTML Page đơn giản:
```html
<!DOCTYPE html>
<html>
<head>
    <title>Live Stream</title>
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
</head>
<body>
    <video id="video" controls width="100%"></video>
    <script>
        const video = document.getElementById('video');
        const hls = new Hls();
        hls.loadSource('http://103.116.104.4:8503/hls/stream.m3u8');
        hls.attachMedia(video);
        hls.on(Hls.Events.MANIFEST_PARSED, () => video.play());
    </script>
</body>
</html>
```

Save file này và mở trong browser từ bất kỳ đâu!

---

## ⚠️ Security Note

**Production nên:**
- Thêm authentication (API key)
- Dùng HTTPS (Nginx + SSL)
- Rate limiting
- IP whitelist nếu cần

Xem chi tiết trong [INTERNET_ACCESS.md](INTERNET_ACCESS.md)
