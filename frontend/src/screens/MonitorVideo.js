import React, { useEffect, useState } from 'react';
import axios from 'axios';
import ReactPlayer from 'react-player';

const MonitorVideo = () => {
  const [rtsp, setRtsp] = useState('');

  useEffect(() => {
    axios.get('http://localhost:8503/api/monitor/video')
      .then(res => setRtsp(res.data.rtsp))
      .catch(err => console.error(err));
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