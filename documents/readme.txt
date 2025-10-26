cd backend
sudo apt install npm
npm init -y
npm install express pg dotenv cors morgan

cat > .env <<'EOF'
PORT=8503
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=abcd@123
DB_NAME=monitoringdb
EOF


sudo -u postgres psql
CREATE DATABASE monitoringdb;
\q

cd ~/monitoring-system/frontend
npx create-react-app .
npm install axios react-player

sudo apt install ffmpeg -y

sudo ufw allow 8503
sudo ufw allow 8504
sudo ufw allow 8554
sudo ufw reload

pm2 start server.js --name backend-monitor
pm2 start "npx serve -s build -l 8504" --name frontend-monitor

pm2 start "ffmpeg -i rtsp://admin:Abcd121%40@113.185.6.120:8554/Streaming/Channels/101 -c:v libx264 -f flv -preset ultrafast -tune zerolatency rtmp://localhost/live/stream" --name camera-stream

pm2 save
pm2 startup