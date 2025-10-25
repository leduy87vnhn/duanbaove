import express from 'express';
import dotenv from 'dotenv';
import cors from 'cors';
import morgan from 'morgan';
import { Client } from 'pg';
import monitorRouter from './routers/monitorRouter.js';

dotenv.config();
const app = express();
app.use(cors());
app.use(express.json());
app.use(morgan('dev'));

// DB connection
const client = new Client({
  host: process.env.DB_HOST,
  port: process.env.DB_PORT,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  database: process.env.DB_NAME,
});
client.connect()
  .then(() => console.log('✅ Connected to PostgreSQL'))
  .catch(err => console.error('❌ DB error', err));

// Routers
app.use('/api/monitor', monitorRouter);

// Start server
const PORT = process.env.PORT || 8503;
app.listen(PORT, () => console.log(`🚀 Backend running on port ${PORT}`));