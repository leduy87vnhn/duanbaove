import React, { useEffect, useState } from 'react';
import axios from 'axios';
import ReactPlayer from 'react-player';

const MonitorVideo = () => {
  const [rtsp, setRtsp] = useState('');

    useEffect(() => {
    const apiUrl = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8503';
    axios.get(`${apiUrl}/api/monitor/video`)
        .then(res => setRtsp(res.data.rtsp))
        .catch(err => console.error('API error:', err));
    }, []);

  return (
    <div style={{ padding: '20px' }}>
      <h2>Camera Monitoring</h2>
      {rtsp ? (
        <ReactPlayer url={rtsp} controls playing />
      ) : (
        <p>Loading camera stream...</p>
      )}
    </div>
  );
};

export default MonitorVideo;