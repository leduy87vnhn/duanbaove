# Hướng dẫn cài đặt Video Streaming Server trên Ubuntu

## 1. Cài đặt Node.js (nên dùng Node 18 hoặc 20)
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
node -v
npm -v
```

## 2. Cài đặt FFmpeg
```bash
sudo apt update
sudo apt install -y ffmpeg
ffmpeg -version
```

## 3. Cài đặt các package Node.js
```bash
cd /path/to/duanbaove/backend
npm install
```

## 4. Cấu hình môi trường
- Copy file `.env.example` thành `.env` và chỉnh sửa nếu cần:
```bash
cp .env.example .env
nano .env
```
- Đảm bảo các biến PORT, HOST, DB_* đúng nhu cầu (nếu không dùng DB có thể bỏ qua)
- Để server listen toàn bộ network: `HOST=0.0.0.0`

## 5. Mở port trên firewall (nếu có)
```bash
sudo ufw allow 8503/tcp
sudo ufw reload
```

## 6. Chạy server
```bash
npm start
```
- Server sẽ chạy tại: `http://<IP_MAY_CHU>:8503`
- Stream HLS: `http://<IP_MAY_CHU>:8503/hls/stream.m3u8`


## 7. Chạy server ngầm bằng PM2 (Khuyến nghị)

PM2 giúp service nodejs chạy ngầm, tự động restart khi lỗi, và tự khởi động lại khi reboot máy chủ.

### Cài đặt PM2 (chỉ cần 1 lần)
```bash
sudo npm install -g pm2
```

### Start service lần đầu
```bash
cd /path/to/duanbaove/backend
pm2 start server.js --name stream-server
```

### Lưu cấu hình để tự động restart khi reboot
```bash
pm2 save
pm2 startup
# Làm theo hướng dẫn dòng lệnh sau khi chạy pm2 startup (chạy lệnh export hoặc sudo như hướng dẫn)
```

### Các lệnh quản lý service
- Xem trạng thái: `pm2 status`
- Xem log: `pm2 logs stream-server`
- Restart: `pm2 restart stream-server`
- Stop: `pm2 stop stream-server`
- Xóa khỏi pm2: `pm2 delete stream-server`

### Kiểm tra service sau reboot
Sau khi reboot máy chủ, service sẽ tự chạy lại. Kiểm tra bằng:
```bash
pm2 status
pm2 logs stream-server
```

### Tham khảo thêm: https://pm2.keymetrics.io/

## 8. Test stream
- Dùng VLC, browser, hoặc file test-stream.html
- Đảm bảo RTSP camera truy cập được từ server

## 9. (Tùy chọn) Reverse Proxy với Nginx để có HTTPS
```bash
sudo apt install -y nginx certbot python3-certbot-nginx
# Tạo file cấu hình nginx cho domain hoặc subdomain
# Xem ví dụ trong INTERNET_ACCESS.md
```

## 10. Troubleshooting
- Xem log: `pm2 logs stream-server` hoặc log terminal
- Kiểm tra port: `sudo lsof -i :8503`
- Kiểm tra firewall: `sudo ufw status`
- Kiểm tra ffmpeg: `ffmpeg -version`

---

**Tham khảo thêm:**
- [QUICKSTART.md](QUICKSTART.md)
- [INTERNET_ACCESS.md](INTERNET_ACCESS.md)
- [SERVER_INFO.md](SERVER_INFO.md)

**Chúc bạn thành công!**
