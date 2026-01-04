import React, { useRef, useEffect } from 'react';
import Hls from 'hls.js';

const VIDEO_URL = 'http://172.10.0.2:8503/hls/stream.m3u8';

export default function VideoPlayer() {
  const videoRef = useRef();

  useEffect(() => {
    if (Hls.isSupported()) {
      const hls = new Hls();
      hls.loadSource(VIDEO_URL);
      hls.attachMedia(videoRef.current);
      return () => hls.destroy();
    } else if (videoRef.current && videoRef.current.canPlayType('application/vnd.apple.mpegurl')) {
      videoRef.current.src = VIDEO_URL;
    }
  }, []);

  return (
    <div style={{ textAlign: 'center', margin: 24 }}>
      <video ref={videoRef} controls style={{ width: '100%', maxWidth: 800 }} />
    </div>
  );
}
