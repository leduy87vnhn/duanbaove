import ffmpeg from 'fluent-ffmpeg';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);


// RTSP stream URL
const RTSP_URL = 'rtsp://admin:Abcd121%40@113.185.6.120:8554/Streaming/Channels/101';
// Fallback video file (nên thay bằng file mp4 thực tế trong resources)
const FALLBACK_VIDEO = path.join(__dirname, '../resources/fallback.mp4');

// Loại nguồn hiện tại: 'rtsp' hoặc 'file'
let currentSource = 'rtsp';

// Directory to store HLS segments
const HLS_DIR = path.join(__dirname, '../resources/hls');

// Ensure HLS directory exists
if (!fs.existsSync(HLS_DIR)) {
  fs.mkdirSync(HLS_DIR, { recursive: true });
}

let streamProcess = null;
let isStreaming = false;


// Hàm start stream với nguồn chỉ định (rtsp hoặc file)
function startStreamSource(source) {
  let input, inputOpts;
  if (source === 'rtsp') {
    input = RTSP_URL;
    inputOpts = [
      '-rtsp_transport', 'tcp',
      '-analyzeduration', '10000000',
      '-probesize', '10000000',
      '-fflags', 'nobuffer',
      '-flags', 'low_delay'
    ];
  } else {
    input = FALLBACK_VIDEO;
    inputOpts = [];
  }

  cleanHLSDirectory();
  streamProcess = ffmpeg(input)
    .inputOptions(inputOpts)
    .outputOptions([
      '-c:v', 'copy',
      '-c:a', 'aac',
      '-b:a', '128k',
      '-f', 'hls',
      '-hls_time', '4',
      '-hls_list_size', '10',
      '-hls_flags', 'delete_segments+append_list',
      '-hls_segment_filename', path.join(HLS_DIR, 'segment_%03d.ts'),
      '-hls_allow_cache', '1',
      '-hls_segment_type', 'mpegts',
      '-preset', 'ultrafast',
      '-tune', 'zerolatency'
    ])
    .output(path.join(HLS_DIR, 'stream.m3u8'))
    .on('start', (commandLine) => {
      console.log(`🎥 [AUTO] FFmpeg started with source: ${source}`);
      isStreaming = true;
      currentSource = source;
    })
    .on('error', (err, stdout, stderr) => {
      console.error(`❌ [AUTO] FFmpeg error with source ${source}:`, err.message);
      console.error('FFmpeg stderr:', stderr);
      isStreaming = false;
      streamProcess = null;
      // Nếu đang dùng RTSP thì fallback sang file
      if (source === 'rtsp') {
        setTimeout(() => {
          console.log('🔄 [AUTO] Fallback to local video');
          startStreamSource('file');
        }, 1000);
      }
    })
    .on('end', () => {
      console.log(`✅ [AUTO] Stream ended for source: ${source}`);
      isStreaming = false;
      streamProcess = null;
      // Nếu kết thúc bất thường, luôn fallback sang file
      if (source === 'rtsp') {
        setTimeout(() => {
          startStreamSource('file');
        }, 1000);
      }
    });
  streamProcess.run();
}

// Tự động start stream khi server khởi động
export function autoStartStream() {
  if (!isStreaming) {
    try {
      startStreamSource('rtsp');
    } catch (error) {
      console.error('❌ [AUTO] Error starting stream:', error);
      // Nếu lỗi thì fallback luôn
      startStreamSource('file');
    }
    // Định kỳ 15 phút thử lại RTSP nếu đang dùng file
    setInterval(() => {
      if (currentSource !== 'rtsp') {
        console.log('🔄 [AUTO] Try to reconnect RTSP source...');
        startStreamSource('rtsp');
      }
    }, 15 * 60 * 1000);
  }
}

/**
 * Start RTSP to HLS conversion with buffering
 */
export const startStream = (req, res) => {
  if (isStreaming) {
    return res.json({ 
      success: true, 
      message: 'Stream đã đang chạy',
      streamUrl: '/hls/stream.m3u8'
    });
  }

  try {
    // Clean up old segments
    cleanHLSDirectory();

    // Configure ffmpeg for RTSP to HLS conversion with buffering
    streamProcess = ffmpeg(RTSP_URL)
      .inputOptions([
        '-rtsp_transport', 'tcp',  // Use TCP for more stable connection
        '-analyzeduration', '10000000',  // Analyze for 10 seconds
        '-probesize', '10000000',  // Probe 10MB
        '-fflags', 'nobuffer',
        '-flags', 'low_delay'
      ])
      .outputOptions([
        '-c:v', 'copy',  // Copy video codec (no re-encoding for performance)
        '-c:a', 'aac',   // Audio codec
        '-b:a', '128k',  // Audio bitrate
        '-f', 'hls',     // HLS format
        '-hls_time', '4',  // 4 seconds per segment (good for buffering)
        '-hls_list_size', '10',  // Keep 10 segments (40 seconds buffer)
        '-hls_flags', 'delete_segments+append_list',  // Delete old segments
        '-hls_segment_filename', path.join(HLS_DIR, 'segment_%03d.ts'),
        '-hls_allow_cache', '1',  // Allow caching for better compatibility
        '-hls_segment_type', 'mpegts',  // MPEG-TS for better Windows app support
        '-preset', 'ultrafast',  // Fast encoding
        '-tune', 'zerolatency'   // Low latency tuning
      ])
      .output(path.join(HLS_DIR, 'stream.m3u8'))
      .on('start', (commandLine) => {
        console.log('🎥 FFmpeg started:', commandLine);
        isStreaming = true;
      })
      .on('error', (err, stdout, stderr) => {
        console.error('❌ FFmpeg error:', err.message);
        console.error('FFmpeg stderr:', stderr);
        isStreaming = false;
        streamProcess = null;
      })
      .on('end', () => {
        console.log('✅ Stream ended');
        isStreaming = false;
        streamProcess = null;
      });

    streamProcess.run();

    res.json({ 
      success: true, 
      message: 'Stream đã được khởi động',
      streamUrl: '/hls/stream.m3u8',
      note: 'Stream có delay 5-10 giây để buffer, giảm lag'
    });

  } catch (error) {
    console.error('❌ Error starting stream:', error);
    res.status(500).json({ 
      success: false, 
      message: 'Không thể khởi động stream',
      error: error.message 
    });
  }
};

/**
 * Stop the streaming process
 */
export const stopStream = (req, res) => {
  if (!isStreaming || !streamProcess) {
    return res.json({ 
      success: false, 
      message: 'Stream không đang chạy' 
    });
  }

  try {
    streamProcess.kill('SIGKILL');
    streamProcess = null;
    isStreaming = false;
    
    // Clean up segments
    cleanHLSDirectory();

    res.json({ 
      success: true, 
      message: 'Stream đã được dừng' 
    });
  } catch (error) {
    console.error('❌ Error stopping stream:', error);
    res.status(500).json({ 
      success: false, 
      message: 'Không thể dừng stream',
      error: error.message 
    });
  }
};

/**
 * Get stream status
 */
export const getStreamStatus = (req, res) => {
  res.json({ 
    isStreaming,
    streamUrl: isStreaming ? '/hls/stream.m3u8' : null,
    hlsDirectory: HLS_DIR
  });
};

/**
 * Get RTSP link (legacy support)
 */
export const getRTSPLink = (req, res) => {
  res.json({ 
    rtsp: RTSP_URL,
    hls: isStreaming ? '/hls/stream.m3u8' : null,
    note: 'Sử dụng HLS endpoint để có buffer tốt hơn'
  });
};

/**
 * Clean HLS directory
 */
function cleanHLSDirectory() {
  try {
    const files = fs.readdirSync(HLS_DIR);
    files.forEach(file => {
      const filePath = path.join(HLS_DIR, file);
      fs.unlinkSync(filePath);
    });
    console.log('🧹 Cleaned HLS directory');
  } catch (error) {
    console.error('❌ Error cleaning HLS directory:', error);
  }
}

// Clean up on process exit
process.on('exit', () => {
  if (streamProcess) {
    streamProcess.kill('SIGKILL');
  }
  cleanHLSDirectory();
});
