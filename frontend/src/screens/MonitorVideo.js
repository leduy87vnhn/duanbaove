import React, { useEffect, useState } from 'react';
import axios from 'axios';
import ReactPlayer from 'react-player';

const MonitorVideo = () => {
  const [rtsp, setRtsp] = useState('');
  const [hlsPublic, setHlsPublic] = useState('');
  const [rtspOut, setRtspOut] = useState('');

  useEffect(() => {
    const apiUrl = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8503';
    axios.get(`${apiUrl}/api/monitor/video`)
      .then(res => {
        setRtsp(res.data.hls_internal || '');
        setHlsPublic(res.data.hls_public || '');
        setRtspOut(res.data.rtsp || '');
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
      {(hlsPublic || rtspOut) && (
        <div style={{ position: 'absolute', top: 10, right: 10, background: '#fff', padding: '10px 14px', borderRadius: 6, boxShadow: '0 2px 8px rgba(0,0,0,0.08)', fontSize: 13, zIndex: 10, minWidth: 280 }}>
          {hlsPublic && <>
            <span style={{ fontWeight: 600 }}>Link VLC (public HLS):</span><br />
            <input
              type="text"
              value={hlsPublic}
              readOnly
              style={{ width: 260, fontSize: 13, border: '1px solid #ccc', borderRadius: 4, padding: '2px 6px', marginTop: 4, marginBottom: 8 }}
              onFocus={e => e.target.select()}
            />
            <br />
          </>}
          {rtspOut && <>
            <span style={{ fontWeight: 600 }}>Link RTSP (gốc):</span><br />
            <input
              type="text"
              value={rtspOut}
              readOnly
              style={{ width: 260, fontSize: 13, border: '1px solid #ccc', borderRadius: 4, padding: '2px 6px', marginTop: 4 }}
              onFocus={e => e.target.select()}
            />
          </>}
        </div>
      )}
    </div>
  );
};

export default MonitorVideo;