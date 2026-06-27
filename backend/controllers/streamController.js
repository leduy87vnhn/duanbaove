/**
 * Stop fallback stream (dừng stream nếu đang phát fallback.mp4)
 */
export const stopFallbackStream = (req, res) => {
  if (!isStreaming || currentSource !== 'file' || !streamProcess) {
    return res.json({
      success: false,
      message: 'Fallback stream không đang chạy'
    });
  }
  try {
    streamProcess.kill('SIGKILL');
    streamProcess = null;
    isStreaming = false;
    cleanHLSDirectory();
    res.json({
      success: true,
      message: 'Fallback stream đã được dừng'
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      message: 'Không thể dừng fallback stream',
      error: error && error.message ? error.message : 'Unknown error'
    });
  }
};
/**
 * Start stream trực tiếp từ fallback.mp4
 */
export const startFallbackStream = (req, res) => {
  if (isStreaming) {
    return res.json({
      success: true,
      message: 'Stream đã đang chạy',
      streamUrl: '/hls/stream.m3u8',
      note: 'Đang phát video mẫu fallback.mp4'
    });
  }

  // Hàm phụ để start stream với nguồn chỉ định, trả về promise
  function startStreamWithSource(source) {
    return new Promise((resolve, reject) => {
      let input, inputOpts;
      input = FALLBACK_VIDEO;
      inputOpts = ['-stream_loop', '-1'];
      cleanHLSDirectory();
      streamProcess = ffmpeg(input)
        .inputOptions(inputOpts)
        .outputOptions([
          '-c:v', 'copy',
          '-c:a', 'aac',
          '-b:a', '128k',
          '-f', 'hls',
          '-hls_time', '2',
          '-hls_list_size', '3',
          '-hls_flags', 'delete_segments+append_list',
          '-hls_segment_filename', path.join(HLS_DIR, 'segment_%03d.ts'),
          '-hls_allow_cache', '1',
          '-hls_segment_type', 'mpegts',
          '-preset', 'ultrafast',
          '-tune', 'zerolatency'
        ])
        .output(path.join(HLS_DIR, 'stream.m3u8'))
        .on('start', (commandLine) => {
          console.log('🎥 [API] FFmpeg started with source: fallback');
          isStreaming = true;
          currentSource = 'file';
        })
        .on('error', (err, stdout, stderr) => {
          console.error('❌ [API] FFmpeg error with fallback:', err.message);
          console.error('FFmpeg stderr:', stderr);
          isStreaming = false;
          streamProcess = null;
          reject(err);
        })
        .on('end', () => {
          console.log('✅ [API] Stream ended for fallback');
          isStreaming = false;
          streamProcess = null;
        });
      streamProcess.run();
      resolve();
    });
  }

  startStreamWithSource('file')
    .then(() => {
      res.json({
        success: true,
        message: 'Stream đã được khởi động từ fallback.mp4',
        streamUrl: '/hls/stream.m3u8',
        note: 'Đang phát video mẫu fallback.mp4'
      });
    })
    .catch((err) => {
      res.status(500).json({
        success: false,
        message: 'Không thể khởi động stream từ fallback.mp4',
        error: err && err.message ? err.message : 'Unknown error'
      });
    });
};
import ffmpeg from 'fluent-ffmpeg';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);


// RTSP stream URL
const RTSP_URL = 'rtsp://admin:Abcd121%40@113.185.6.120:554/Streaming/Channels/101';
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

function normalizeRtspTransport(value) {
  return value === 'udp' ? 'udp' : 'tcp';
}


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
      '-hls_time', '2',
      '-hls_list_size', '3',
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

  // Lấy RTSP URL từ request body hoặc dùng mặc định
  const rtspUrl = (req.body && req.body.rtspUrl) ? req.body.rtspUrl : RTSP_URL;
  const rtspTransport = normalizeRtspTransport(req.body && req.body.rtspTransport);

  // Hàm phụ để start stream với nguồn chỉ định, trả về promise
  function startStreamWithSource(source, customRtspUrl = null) {
    return new Promise((resolve, reject) => {
      let input, inputOpts;
      if (source === 'rtsp') {
        input = customRtspUrl || RTSP_URL;
        inputOpts = [
          '-rtsp_transport', rtspTransport,
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
          console.log(`🎥 [API] FFmpeg started with source: ${source}`);
          if (source === 'rtsp') {
            console.log(`[API] RTSP input transport: ${rtspTransport}`);
          }
          if (source === 'rtsp' && customRtspUrl) {
            console.log(`📹 [API] Using custom RTSP URL: ${customRtspUrl}`);
          }
          isStreaming = true;
          currentSource = source;
        })
        .on('error', (err, stdout, stderr) => {
          console.error(`❌ [API] FFmpeg error with source ${source}:`, err.message);
          console.error('FFmpeg stderr:', stderr);
          isStreaming = false;
          streamProcess = null;
          reject(err);
        })
        .on('end', () => {
          console.log(`✅ [API] Stream ended for source: ${source}`);
          isStreaming = false;
          streamProcess = null;
        });
      streamProcess.run();
      // resolve ngay để trả về API, không chờ ffmpeg kết thúc
      resolve();
    });
  }

  // Thử RTSP, nếu lỗi thì fallback sang file
  startStreamWithSource('rtsp', rtspUrl)
    .then(() => {
      res.json({
        success: true,
        message: 'Stream đã được khởi động',
        streamUrl: '/hls/stream.m3u8',
        rtspTransport,
        note: 'Stream có delay 5-10 giây để buffer, giảm lag'
      });
    })
    .catch((err) => {
      console.log('🔄 [API] Fallback to local video');
      startStreamWithSource('file')
        .then(() => {
          res.json({
            success: true,
            message: 'Stream fallback sang video mẫu',
            streamUrl: '/hls/stream.m3u8',
            rtspTransport,
            note: 'Đang phát video mẫu do không kết nối được camera'
          });
        })
        .catch((err2) => {
          res.status(500).json({
            success: false,
            message: 'Không thể khởi động stream (cả RTSP và fallback đều lỗi)',
            error: err2.message
          });
        });
    });
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
