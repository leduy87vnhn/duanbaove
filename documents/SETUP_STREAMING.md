# Hướng dẫn Setup Server Stream Buffer

## Giới thiệu
Server này sẽ nhận RTSP stream từ camera, buffer lại và phát dưới dạng HLS để giảm lag khi xem qua mạng 4G yếu.

## Yêu cầu
1. **Node.js** (v14 trở lên)
2. **FFmpeg** - Phần mềm xử lý video

## Bước 1: Cài đặt FFmpeg

### Windows:
1. Tải FFmpeg từ: https://www.gyan.dev/ffmpeg/builds/
2. Chọn bản "ffmpeg-git-full.7z"
3. Giải nén vào thư mục (ví dụ: `C:\ffmpeg`)
4. Thêm vào PATH:
   - Mở "Environment Variables"
   - Thêm `C:\ffmpeg\bin` vào PATH
   - Restart terminal

### Kiểm tra cài đặt:
```bash
ffmpeg -version
```

## Bước 2: Cài đặt Node Dependencies

```bash
cd backend
npm install
```

## Bước 3: Chạy Server

```bash
npm start
# hoặc để dev mode với auto-restart:
npm run dev
```

## Bước 4: Sử dụng API

### 1. Khởi động stream buffer:
```bash
POST http://localhost:8503/api/stream/start
```

Response:
```json
{
  "success": true,
  "message": "Stream đã được khởi động",
  "streamUrl": "/hls/stream.m3u8",
  "note": "Stream có delay 5-10 giây để buffer, giảm lag"
}
```

### 2. Kiểm tra trạng thái:
```bash
GET http://localhost:8503/api/stream/status
```

### 3. Dừng stream:
```bash
POST http://localhost:8503/api/stream/stop
```

### 4. Xem stream:
```
URL: http://localhost:8503/hls/stream.m3u8
```

## Cách hoạt động:

1. **RTSP Input**: Server kết nối đến camera qua RTSP
2. **FFmpeg Processing**: 
   - Convert sang HLS format
   - Tạo các segment 4 giây/segment
   - Giữ 10 segments = 20 giây buffer
3. **HLS Output**: Phát qua HTTP, dễ xem trên web/mobile
4. **Buffering**: Delay 5-10 giây nhưng stream mượt hơn rất nhiều

## Tối ưu:

- **hls_time: 2 giây** - Mỗi segment 2 giây
- **hls_list_size: 10** - Giữ 10 segments (20s buffer)
- **Copy video codec** - Không encode lại, nhanh hơn
- **TCP transport** - Ổn định hơn UDP với mạng yếu

## Frontend Integration:

### HTML5 Video Player:
```html
<video id="stream" controls>
  <source src="http://localhost:8503/hls/stream.m3u8" type="application/x-mpegURL">
</video>
```

### Với HLS.js (tốt hơn):
```javascript
import Hls from 'hls.js';

const video = document.getElementById('video');
const hls = new Hls({
  maxBufferLength: 30, // Buffer 30 giây
  maxMaxBufferLength: 60 // Tối đa 60 giây
});

hls.loadSource('http://localhost:8503/hls/stream.m3u8');
hls.attachMedia(video);
```

## Troubleshooting:

### Lỗi "ffmpeg not found":
- Đảm bảo đã cài FFmpeg và thêm vào PATH
- Restart terminal sau khi thêm PATH
- Kiểm tra: `ffmpeg -version`

### Stream không chạy:
- Kiểm tra RTSP URL có đúng không
- Kiểm tra camera có online không
- Xem log trong terminal

### Lag vẫn còn:
- Tăng `hls_time` lên 6-8 giây
- Tăng `hls_list_size` lên 15-20
- Trade-off: Buffer lớn hơn = delay nhiều hơn nhưng mượt hơn

## Cấu hình RTSP URL:

Hiện tại trong code:
```javascript
const RTSP_URL = 'rtsp://admin:Abcd121%40@113.185.6.120:8554/Streaming/Channels/101';
```

Để thay đổi, sửa trong file `backend/controllers/streamController.js`

## Lưu ý:
- Delay 5-10 giây là bình thường cho HLS buffering
- Mạng 4G yếu sẽ vẫn giật nhưng ít hơn nhiều so với RTSP trực tiếp
- Server này nên chạy trên máy có kết nối tốt đến camera
