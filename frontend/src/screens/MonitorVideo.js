import React, { useEffect, useState } from 'react';
import axios from 'axios';
import ReactPlayer from 'react-player';

const MonitorVideo = () => {
  const [rtsp, setRtsp] = useState('');
  const [hlsPublic, setHlsPublic] = useState('');

  useEffect(() => {
    const apiUrl = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8503';
    axios.get(`${apiUrl}/api/monitor/video`)
      .then(res => {
        setRtsp(res.data.rtsp || res.data.hls_internal || '');
        setHlsPublic(res.data.hls_public || '');
      })
      .catch(err => console.error('API error:', err));
  }, []);

  return (
    <div style={{ padding: '20px', position: 'relative' }}>
      <h2>Camera Monitoring</h2>
      {rtsp ? (
        <ReactPlayer url={rtsp} controls playing />
      ) : (
        <p>Loading camera stream...</p>
      )}
      {hlsPublic && (
        <div style={{ position: 'absolute', top: 10, right: 10, background: '#fff', padding: '8px 12px', borderRadius: 6, boxShadow: '0 2px 8px rgba(0,0,0,0.08)', fontSize: 13, zIndex: 10 }}>
          <span style={{ fontWeight: 600 }}>Link VLC (public):</span><br />
          <input
            type="text"
            value={hlsPublic}
            readOnly
            style={{ width: 260, fontSize: 13, border: '1px solid #ccc', borderRadius: 4, padding: '2px 6px', marginTop: 4 }}
            onFocus={e => e.target.select()}
          />
        </div>
      )}
    </div>
  );
};

export default MonitorVideo;