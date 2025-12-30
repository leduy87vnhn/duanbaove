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

## 7. (Khuyến nghị) Chạy server bằng PM2 để tự động restart khi lỗi
```bash
sudo npm install -g pm2
pm2 start server.js --name stream-server
pm2 save
pm2 startup
```

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
