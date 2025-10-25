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