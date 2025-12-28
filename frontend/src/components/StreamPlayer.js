import React, { useEffect, useRef, useState } from 'react';
import Hls from 'hls.js';
import '../scss/streamPlayer.scss';

const StreamPlayer = () => {
  const videoRef = useRef(null);
  const hlsRef = useRef(null);
  const [streamStatus, setStreamStatus] = useState({ isStreaming: false });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const API_BASE = 'http://localhost:8503/api/stream';
  const HLS_URL = 'http://localhost:8503/hls/stream.m3u8';

  // Fetch stream status
  const fetchStatus = async () => {
    try {
      const response = await fetch(`${API_BASE}/status`);
      const data = await response.json();
      setStreamStatus(data);
    } catch (err) {
      console.error('Error fetching status:', err);
    }
  };

  // Start stream
  const startStream = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/start`, { method: 'POST' });
      const data = await response.json();
      
      if (data.success) {
        setStreamStatus({ isStreaming: true });
        // Wait a bit for segments to be generated
        setTimeout(() => initializePlayer(), 3000);
      } else {
        setError(data.message);
      }
    } catch (err) {
      setError('Không thể khởi động stream: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  // Stop stream
  const stopStream = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/stop`, { method: 'POST' });
      const data = await response.json();
      
      if (data.success) {
        setStreamStatus({ isStreaming: false });
        if (hlsRef.current) {
          hlsRef.current.destroy();
          hlsRef.current = null;
        }
      }
    } catch (err) {
      setError('Không thể dừng stream: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  // Initialize HLS player
  const initializePlayer = () => {
    const video = videoRef.current;
    if (!video) return;

    if (Hls.isSupported()) {
      // Destroy existing instance
      if (hlsRef.current) {
        hlsRef.current.destroy();
      }

      // Create new HLS instance with buffering config
      const hls = new Hls({
        maxBufferLength: 30,        // Buffer 30 seconds
        maxMaxBufferLength: 60,     // Max 60 seconds
        maxBufferSize: 60 * 1000 * 1000, // 60MB
        maxBufferHole: 0.5,
        lowLatencyMode: false,      // Disable low latency for better buffering
        backBufferLength: 90,       // Keep 90s back buffer
      });

      hls.loadSource(HLS_URL);
      hls.attachMedia(video);

      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        console.log('✅ HLS manifest loaded');
        video.play().catch(err => {
          console.error('Auto-play failed:', err);
        });
      });

      hls.on(Hls.Events.ERROR, (event, data) => {
        console.error('HLS error:', data);
        if (data.fatal) {
          switch (data.type) {
            case Hls.ErrorTypes.NETWORK_ERROR:
              console.error('Network error, trying to recover...');
              hls.startLoad();
              break;
            case Hls.ErrorTypes.MEDIA_ERROR:
              console.error('Media error, trying to recover...');
              hls.recoverMediaError();
              break;
            default:
              setError('Lỗi không thể khôi phục');
              hls.destroy();
              break;
          }
        }
      });

      hlsRef.current = hls;
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      // Native HLS support (Safari)
      video.src = HLS_URL;
      video.addEventListener('loadedmetadata', () => {
        video.play();
      });
    }
  };

  // Check status on mount
  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000); // Check every 5s
    return () => clearInterval(interval);
  }, []);

  // Initialize player if already streaming
  useEffect(() => {
    if (streamStatus.isStreaming) {
      initializePlayer();
    }
  }, [streamStatus.isStreaming]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (hlsRef.current) {
        hlsRef.current.destroy();
      }
    };
  }, []);

  return (
    <div className="stream-player">
      <div className="stream-header">
        <h2>📹 Video Giám Sát (Buffered Stream)</h2>
        <div className="status-badge">
          {streamStatus.isStreaming ? (
            <span className="badge streaming">🟢 Đang Stream</span>
          ) : (
            <span className="badge stopped">🔴 Đã Dừng</span>
          )}
        </div>
      </div>

      <div className="video-container">
        <video
          ref={videoRef}
          className="video-player"
          controls
          playsInline
          muted={false}
        >
          Your browser does not support video playback.
        </video>
        
        {!streamStatus.isStreaming && !loading && (
          <div className="video-overlay">
            <p>Stream chưa được khởi động</p>
          </div>
        )}
      </div>

      {error && (
        <div className="error-message">
          ⚠️ {error}
        </div>
      )}

      <div className="stream-info">
        <p>ℹ️ Stream có độ trễ 5-10 giây để buffer, giảm lag khi mạng yếu</p>
      </div>

      <div className="stream-controls">
        <button
          className="btn btn-start"
          onClick={startStream}
          disabled={streamStatus.isStreaming || loading}
        >
          {loading ? '⏳ Đang xử lý...' : '▶️ Khởi Động Stream'}
        </button>
        
        <button
          className="btn btn-stop"
          onClick={stopStream}
          disabled={!streamStatus.isStreaming || loading}
        >
          ⏹️ Dừng Stream
        </button>

        <button
          className="btn btn-refresh"
          onClick={fetchStatus}
          disabled={loading}
        >
          🔄 Làm mới
        </button>
      </div>
    </div>
  );
};

export default StreamPlayer;
