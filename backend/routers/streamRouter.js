import express from 'express';
import { 
  startStream,
  startFallbackStream, 
  stopStream, 
  getStreamStatus, 
  getRTSPLink 
} from '../controllers/streamController.js';

const router = express.Router();

// Start buffered stream
router.post('/start', startStream);

// Stop stream
router.post('/stop', stopStream);

// Get stream status
router.get('/status', getStreamStatus);

// Get RTSP link info
router.get('/info', getRTSPLink);

router.post('/start-fallback', startFallbackStream);

export default router;
