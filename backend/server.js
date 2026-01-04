import express from 'express';
import dotenv from 'dotenv';
import cors from 'cors';
import morgan from 'morgan';
// import { Client } from 'pg';
import path from 'path';
import { fileURLToPath } from 'url';
import monitorRouter from './routers/monitorRouter.js';
import streamRouter from './routers/streamRouter.js';
import { autoStartStream } from './controllers/streamController.js';
import { startFallbackStream } from './controllers/streamController.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

dotenv.config();
const app = express();

// CORS configuration for external access
app.use(cors({
  origin: '*',  // Allow all origins (change to specific domains in production)
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-API-Key']
}));

app.use(express.json());
app.use(morgan('dev'));

// Serve HLS static files
app.use('/hls', express.static(path.join(__dirname, 'resources/hls'), {
  setHeaders: (res, filePath) => {
    if (filePath.endsWith('.m3u8')) {
      res.setHeader('Content-Type', 'application/vnd.apple.mpegurl');
    } else if (filePath.endsWith('.ts')) {
      res.setHeader('Content-Type', 'video/mp2t');
    }
    // Allow CORS for streaming
    res.setHeader('Access-Control-Allow-Origin', '*');
  }
}));

// DB connection (tạm thời không sử dụng)
// const client = new Client({
//   host: process.env.DB_HOST,
//   port: process.env.DB_PORT,
//   user: process.env.DB_USER,
//   password: process.env.DB_PASSWORD,
//   database: process.env.DB_NAME,
// });
// client.connect()
//   .then(() => console.log('✅ Connected to PostgreSQL'))
//   .catch(err => console.error('❌ DB error', err));

// Routers
app.use('/api/monitor', monitorRouter);
app.use('/api/stream', streamRouter);

// Start server
const PORT = process.env.PORT || 8503;
const HOST = process.env.HOST || '0.0.0.0';  // Listen on all interfaces for external access

app.listen(PORT, HOST, () => {
  console.log(`🚀 Backend running on ${HOST}:${PORT}`);
  console.log(`📺 Stream URL: http://localhost:${PORT}/hls/stream.m3u8`);
  console.log(`🌐 API Docs: http://localhost:${PORT}/api/stream/status`);
  // Tự động start stream khi server khởi động
  //autoStartStream();
  //startFallbackStream();
});