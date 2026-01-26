import React, { useEffect, useState } from 'react';
import axios from 'axios';
import ReactPlayer from 'react-player';

const MonitorVideo = ({ onRtspUrlChange }) => {
  const [rtsp, setRtsp] = useState('');
  const [hlsPublic, setHlsPublic] = useState('');
  const [rtspOut, setRtspOut] = useState('');

  useEffect(() => {
    const apiUrl = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8503';
    axios.get(`${apiUrl}/api/monitor/video`)
      .then(res => {
        setRtsp(res.data.hls_internal || '');
        setHlsPublic(res.data.hls_public || '');
        const rtspValue = res.data.rtsp || '';
        setRtspOut(rtspValue);
        if (onRtspUrlChange) {
          onRtspUrlChange(rtspValue);
        }
      })
      .catch(err => console.error('API error:', err));
  }, [onRtspUrlChange]);

  const handleRtspChange = (e) => {
    const newValue = e.target.value;
    setRtspOut(newValue);
    if (onRtspUrlChange) {
      onRtspUrlChange(newValue);
    }
  };

  return (
    <div style={{ padding: '20px', position: 'relative' }}>
      <h2 style={{ textAlign: 'center' }}>Camera Monitoring</h2>
      {(hlsPublic || rtspOut) && (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 18px auto',
          background: '#fff',
          padding: '12px 18px',
          borderRadius: 8,
          boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
          fontSize: 15,
          minWidth: 320,
          maxWidth: 420
        }}>
          {hlsPublic && <>
            <span style={{ fontWeight: 600 }}>Link VLC (public HLS):</span><br />
            <input
              type="text"
              value={hlsPublic}
              readOnly
              style={{ width: 320, fontSize: 14, border: '1px solid #ccc', borderRadius: 4, padding: '4px 8px', marginTop: 4, marginBottom: 10 }}
              onFocus={e => e.target.select()}
            />
          </>}
          {rtspOut !== null && <>
            <span style={{ fontWeight: 600 }}>Link RTSP (gốc):</span><br />
            <input
              type="text"
              value={rtspOut}
              onChange={handleRtspChange}
              style={{ width: 320, fontSize: 14, border: '1px solid #ccc', borderRadius: 4, padding: '4px 8px', marginTop: 4 }}
              onFocus={e => e.target.select()}
              placeholder="Nhập RTSP URL..."
            />
          </>}
        </div>
      )}
      {rtsp ? (
        <ReactPlayer url={rtsp} controls playing />
      ) : (
        <p style={{ textAlign: 'center' }}>Loading camera stream...</p>
      )}
    </div>
  );
};

export default MonitorVideo;