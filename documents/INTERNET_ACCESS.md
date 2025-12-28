# Hướng dẫn truy cập Stream từ Internet

## Có 3 cách chính:

## 1. Port Forwarding trên Router (Khuyến nghị cho ổn định)

### Bước 1: Cấu hình Static IP cho máy chạy server
```powershell
# Xem IP hiện tại
ipconfig

# Ghi lại:
# - IPv4 Address: 192.168.1.XXX
# - Default Gateway: 192.168.1.1
# - DNS Server
```

Vào **Control Panel** → **Network Connections** → **Properties** → **IPv4**:
- Chọn "Use the following IP address"
- Nhập IP tĩnh (ví dụ: 192.168.1.100)
- Subnet mask: 255.255.255.0
- Default gateway: IP của router (thường là 192.168.1.1)
- DNS: 8.8.8.8, 8.8.4.4

### Bước 2: Port Forwarding trên Router
1. Truy cập router: http://192.168.1.1 (hoặc 192.168.0.1)
2. Login (admin/admin hoặc xem mật khẩu dưới router)
3. Tìm **Port Forwarding** / **Virtual Server** / **NAT**
4. Thêm rule:
   ```
   Service Name: Stream Server
   External Port: 8503
   Internal IP: 192.168.1.100 (IP máy server)
   Internal Port: 8503
   Protocol: TCP
   ```
5. Save và reboot router

### Bước 3: Mở Firewall trên Windows
```powershell
# Run as Administrator
New-NetFirewallRule -DisplayName "Stream Server Public" `
  -Direction Inbound `
  -LocalPort 8503 `
  -Protocol TCP `
  -Action Allow `
  -Profile Public
```

### Bước 4: Lấy IP Public
```powershell
# Kiểm tra IP public của bạn
curl ifconfig.me
# Hoặc truy cập: https://whatismyipaddress.com/
```

### Bước 5: Truy cập từ internet
```
Stream URL: http://<IP_PUBLIC>:8503/hls/stream.m3u8
API: http://<IP_PUBLIC>:8503/api/stream/start
```

### Lưu ý về IP động:
Nếu IP public thay đổi, dùng **Dynamic DNS** (xem phần cuối)

---

## 2. Ngrok (Nhanh nhất cho testing, có giới hạn)

### Cài đặt Ngrok:
1. Tải từ: https://ngrok.com/download
2. Đăng ký tài khoản free tại: https://ngrok.com/
3. Giải nén và copy authtoken

### Sử dụng:
```powershell
# Authenticate
ngrok config add-authtoken <YOUR_TOKEN>

# Expose port 8503
ngrok http 8503
```

Output:
```
Forwarding   https://abc123.ngrok.io -> http://localhost:8503
```

### Truy cập:
```
Stream URL: https://abc123.ngrok.io/hls/stream.m3u8
API: https://abc123.ngrok.io/api/stream/start
```

### Ưu điểm:
- ✅ Cực nhanh, không cần config router
- ✅ Có HTTPS tự động
- ✅ Tốt cho demo, testing

### Nhược điểm:
- ❌ URL thay đổi mỗi lần restart (free plan)
- ❌ Có giới hạn băng thông
- ❌ Có thể bị lag nếu nhiều người xem

---

## 3. Deploy lên VPS (Tốt nhất cho production)

### Thuê VPS (DigitalOcean, AWS, Vultr, etc.)
```bash
# Giá ~$5-10/tháng
# IP public cố định
# Băng thông cao
```

### Setup trên VPS (Ubuntu):
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Install FFmpeg
sudo apt install -y ffmpeg

# Install PM2 (process manager)
sudo npm install -g pm2

# Clone/Upload code
cd /var/www
git clone <your-repo>
cd duanbaove/backend

# Install dependencies
npm install

# Start with PM2
pm2 start server.js --name stream-server
pm2 startup
pm2 save

# Configure firewall
sudo ufw allow 8503/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### Truy cập:
```
Stream URL: http://<VPS_IP>:8503/hls/stream.m3u8
```

### Với Domain & HTTPS (Nginx + Let's Encrypt):
```bash
# Install Nginx
sudo apt install -y nginx certbot python3-certbot-nginx

# Configure Nginx
sudo nano /etc/nginx/sites-available/stream
```

```nginx
server {
    listen 80;
    server_name stream.yourdomain.com;

    location / {
        proxy_pass http://localhost:8503;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /hls {
        proxy_pass http://localhost:8503/hls;
        add_header Cache-Control no-cache;
        add_header Access-Control-Allow-Origin *;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/stream /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Get SSL certificate
sudo certbot --nginx -d stream.yourdomain.com
```

### Truy cập với HTTPS:
```
Stream URL: https://stream.yourdomain.com/hls/stream.m3u8
```

---

## 4. Dynamic DNS (Cho IP public thay đổi)

### Dịch vụ DDNS miễn phí:
- **No-IP**: https://www.noip.com/
- **DuckDNS**: https://www.duckdns.org/
- **Dynu**: https://www.dynu.com/

### Ví dụ với No-IP:

1. Đăng ký tại: https://www.noip.com/
2. Tạo hostname: `mystream.ddns.net`
3. Tải **No-IP DUC** (Dynamic Update Client)
4. Cài đặt và login
5. Chọn hostname đã tạo

### Truy cập:
```
Stream URL: http://mystream.ddns.net:8503/hls/stream.m3u8
```

IP public thay đổi → DDNS tự động update DNS → Domain luôn trỏ đúng

---

## So sánh các phương pháp:

| Phương pháp | Chi phí | Độ ổn định | Tốc độ | Phù hợp |
|-------------|---------|------------|--------|---------|
| **Port Forwarding** | Free | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Gia đình, văn phòng |
| **Ngrok** | Free/Paid | ⭐⭐⭐ | ⭐⭐⭐ | Demo, testing |
| **VPS** | ~$5-10/tháng | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Production, nhiều người |

---

## Cập nhật Backend cho external access

### Thêm CORS config trong server.js:

```javascript
// Update CORS to allow all origins (hoặc specify domains)
app.use(cors({
  origin: '*',  // Hoặc ['https://yourdomain.com', 'http://yourip:port']
  credentials: true
}));
```

### Environment variables (.env):
```env
# Local
PORT=8503
HOST=0.0.0.0  # Listen on all interfaces

# Production
# Add your production settings
```

---

## Security Best Practices:

### 1. Authentication (Nên có cho production):
```javascript
// Thêm vào streamController.js
const API_KEY = process.env.API_KEY || 'your-secret-key';

export const startStream = (req, res) => {
  const apiKey = req.headers['x-api-key'];
  
  if (apiKey !== API_KEY) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  
  // ... existing code
};
```

### 2. Rate Limiting:
```bash
npm install express-rate-limit
```

```javascript
import rateLimit from 'express-rate-limit';

const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100 // limit each IP to 100 requests per windowMs
});

app.use('/api/', limiter);
```

### 3. HTTPS (Bắt buộc nếu expose ra internet):
- Dùng Nginx + Let's Encrypt (miễn phí)
- Hoặc Cloudflare (miễn phí, dễ dùng)

---

## Test từ Internet:

### Test bằng smartphone (4G):
1. Tắt WiFi, bật 4G
2. Mở VLC hoặc browser
3. Nhập: `http://<IP_PUBLIC>:8503/hls/stream.m3u8`

### Test bằng online tools:
- https://www.hls.js.org/demo/
- Paste stream URL và test

---

## Troubleshooting:

### Không kết nối được từ internet:
```powershell
# 1. Kiểm tra port có mở không
Test-NetConnection -ComputerName <IP_PUBLIC> -Port 8503

# 2. Kiểm tra firewall
Get-NetFirewallRule -DisplayName "Stream Server*"

# 3. Kiểm tra router có forward đúng không
# Login router và xem Port Forwarding status
```

### Stream lag từ internet:
- Tăng buffer: `hls_time: 6` và `hls_list_size: 15`
- Giảm bitrate nếu upload chậm
- Cân nhắc dùng VPS gần người xem

---

## Khuyến nghị:

**Cho sử dụng cá nhân/nội bộ:**
→ Port Forwarding + Dynamic DNS

**Cho testing/demo:**
→ Ngrok

**Cho production/nhiều người:**
→ VPS + Domain + HTTPS
