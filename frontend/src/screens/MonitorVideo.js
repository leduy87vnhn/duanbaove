import React, { useEffect, useState } from 'react';
import axios from 'axios';
import ReactPlayer from 'react-player';

const MonitorVideo = ({ onRtspUrlChange }) => {
  const [hlsInternal, setHlsInternal] = useState('');
  const [hlsPublic, setHlsPublic] = useState('');
  const [rtspInput, setRtspInput] = useState('');
  const [copyMessage, setCopyMessage] = useState('');

  useEffect(() => {
    const apiUrl = process.env.REACT_APP_API_BASE_URL || 'http://103.116.104.4:8503';
    axios.get(`${apiUrl}/api/monitor/video`)
      .then(res => {
        const inputUrl = res.data.rtsp || '';
        setHlsInternal(res.data.hls_internal || '');
        setHlsPublic(res.data.hls_public || '');
        setRtspInput(inputUrl);
        if (onRtspUrlChange) {
          onRtspUrlChange(inputUrl);
        }
      })
      .catch(err => console.error('API error:', err));
  }, [onRtspUrlChange]);

  const handleRtspChange = (e) => {
    const newValue = e.target.value;
    setRtspInput(newValue);
    if (onRtspUrlChange) {
      onRtspUrlChange(newValue);
    }
  };

  const copyToClipboard = async (value, label) => {
    if (!value) return;

    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(value);
      } else {
        const textarea = document.createElement('textarea');
        textarea.value = value;
        textarea.style.position = 'fixed';
        textarea.style.left = '-9999px';
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
      }
      setCopyMessage(`Da copy ${label}`);
    } catch (err) {
      setCopyMessage(`Khong copy duoc ${label}`);
    }
  };

  const renderPlayer = (url, loadingText) => (
    <div className="player-frame">
      {url ? (
        <ReactPlayer url={url} controls playing width="100%" height="100%" />
      ) : (
        <p className="loading-text">{loadingText}</p>
      )}
    </div>
  );

  return (
    <div className="monitor-page">
      <div className="monitor-header">
        <div>
          <p className="monitor-eyebrow">Live camera</p>
          <h2>Camera Monitoring</h2>
        </div>
        <div className="monitor-status">Video out: HLS port 8503</div>
      </div>

      <div className="monitor-card monitor-links">
        <div className="field-group">
          <label>Video out cho VLC (server phat lai - public HLS)</label>
          <div className="copy-row">
            <input
              type="text"
              value={hlsPublic}
              readOnly
              onFocus={e => e.target.select()}
              placeholder="Dang tai link video out..."
            />
            <button type="button" className="btn-copy" onClick={() => copyToClipboard(hlsPublic, 'video out')}>
              Copy
            </button>
          </div>
        </div>

        <div className="field-group">
          <label>Nguon RTSP goc (input camera)</label>
          <input
            type="text"
            value={rtspInput}
            onChange={handleRtspChange}
            onFocus={e => e.target.select()}
            placeholder="Nhap RTSP URL..."
          />
        </div>

        {copyMessage && <div className="copy-message">{copyMessage}</div>}
      </div>

      <div className="video-preview-grid">
        <div className="monitor-card video-card">
          <div className="video-card-header">
            <div>
              <h3>Server stream noi bo</h3>
              <p>{hlsInternal || 'Dang tai link noi bo...'}</p>
            </div>
            <span>Internal HLS</span>
          </div>
          {renderPlayer(hlsInternal, 'Loading internal stream...')}
        </div>

        <div className="monitor-card video-card">
          <div className="video-card-header">
            <div>
              <h3>Server stream public</h3>
              <p>{hlsPublic || 'Dang tai link public...'}</p>
            </div>
            <span>VLC output</span>
          </div>
          {renderPlayer(hlsPublic, 'Loading public stream...')}
        </div>
      </div>
    </div>
  );
};

export default MonitorVideo;
