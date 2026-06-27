import React, { useState } from 'react';

const API_BASE = 'http://172.10.0.2:8503/api/stream';

export default function StreamControl({ rtspUrl }) {
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [rtspTransport, setRtspTransport] = useState('tcp');
  const [bufferSeconds, setBufferSeconds] = useState(20);

  const bufferOptions = Array.from({ length: 20 }, (_, index) => {
    const seconds = (index + 1) * 2;
    return {
      seconds,
      hlsListSize: index + 1
    };
  });

  const callApi = async (endpoint, body = null) => {
    setLoading(true);
    setMessage('');
    try {
      const options = {
        method: 'POST',
        headers: body ? { 'Content-Type': 'application/json' } : undefined,
        body: body ? JSON.stringify(body) : undefined
      };
      const res = await fetch(`${API_BASE}/${endpoint}`, options);
      const data = await res.json();
      setMessage(data.message || (data.success ? 'Thanh cong' : 'Loi'));
    } catch (err) {
      setMessage('Loi ket noi API');
    }
    setLoading(false);
  };

  const stopAndStart = async (endpoint, body = null) => {
    setLoading(true);
    setMessage('');
    try {
      await fetch(`${API_BASE}/stop`, { method: 'POST' });
      await new Promise(resolve => setTimeout(resolve, 500));

      const options = {
        method: 'POST',
        headers: body ? { 'Content-Type': 'application/json' } : undefined,
        body: body ? JSON.stringify(body) : undefined
      };
      const res = await fetch(`${API_BASE}/${endpoint}`, options);
      const data = await res.json();
      setMessage(data.message || (data.success ? 'Thanh cong' : 'Loi'));
    } catch (err) {
      setMessage('Loi ket noi API');
    }
    setLoading(false);
  };

  const handleStartRTSP = () => {
    const body = {
      rtspTransport,
      hlsListSize: bufferSeconds / 2,
      ...(rtspUrl && rtspUrl.trim() ? { rtspUrl: rtspUrl.trim() } : {})
    };
    stopAndStart('start', body);
  };

  return (
    <div className="stream-control-card">
      <div className="control-header">
        <div>
          <p className="monitor-eyebrow">Stream operation</p>
          <h2>Stream Control</h2>
        </div>
        <div className="stream-settings">
          <div className="setting-group">
            <label>RTSP input</label>
            <div className="transport-toggle" aria-label="RTSP input transport">
              <button
                type="button"
                className={rtspTransport === 'tcp' ? 'active' : ''}
                onClick={() => setRtspTransport('tcp')}
              >
                TCP
              </button>
              <button
                type="button"
                className={rtspTransport === 'udp' ? 'active' : ''}
                onClick={() => setRtspTransport('udp')}
              >
                UDP
              </button>
            </div>
          </div>
          <div className="setting-group">
            <label>Buffer HLS</label>
            <select
              value={bufferSeconds}
              onChange={(e) => setBufferSeconds(Number(e.target.value))}
            >
              {bufferOptions.map(option => (
                <option key={option.hlsListSize} value={option.seconds}>
                  {option.seconds}s - list size {option.hlsListSize}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="control-actions">
        <button className="btn-action btn-primary" onClick={handleStartRTSP} disabled={loading}>
          Start RTSP Stream
        </button>
        <button className="btn-action btn-secondary" onClick={() => stopAndStart('start-fallback')} disabled={loading}>
          Start Fallback
        </button>
        <button className="btn-action btn-warning" onClick={() => callApi('stop-fallback')} disabled={loading}>
          Stop Fallback
        </button>
        <button className="btn-action btn-danger" onClick={() => callApi('stop')} disabled={loading}>
          Stop Stream
        </button>
      </div>

      {message && <div className="control-message">{message}</div>}
    </div>
  );
}
