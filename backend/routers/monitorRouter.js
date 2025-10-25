import express from 'express';
import { getRTSPLink } from '../controllers/monitorController.js';
const router = express.Router();

router.get('/video', getRTSPLink);

export default router;