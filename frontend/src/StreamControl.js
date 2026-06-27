import React, { useState } from 'react';

const API_BASE = 'http://172.10.0.2:8503/api/stream';

export default function StreamControl({ rtspUrl }) {
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [rtspTransport, setRtspTransport] = useState('tcp');

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
      setMessage(data.message || (data.success ? 'Thành công' : 'Lỗi'));
    } catch (err) {
      setMessage('Lỗi kết nối API');
    }
    setLoading(false);
  };

  const stopAndStart = async (endpoint, body = null) => {
    setLoading(true);
    setMessage('');
    try {
      // Dừng stream hiện tại trước
      await fetch(`${API_BASE}/stop`, { method: 'POST' });
      // Đợi 500ms để đảm bảo stream đã dừng hoàn toàn
      await new Promise(resolve => setTimeout(resolve, 500));
      // Khởi động stream mới
      const options = {
        method: 'POST',
        headers: body ? { 'Content-Type': 'application/json' } : undefined,
        body: body ? JSON.stringify(body) : undefined
      };
      const res = await fetch(`${API_BASE}/${endpoint}`, options);
      const data = await res.json();
      setMessage(data.message || (data.success ? 'Thành công' : 'Lỗi'));
    } catch (err) {
      setMessage('Lỗi kết nối API');
    }
    setLoading(false);
  };

  const handleStartRTSP = () => {
    const body = {
      rtspTransport,
      ...(rtspUrl && rtspUrl.trim() ? { rtspUrl: rtspUrl.trim() } : {})
    };
    stopAndStart('start', body);
  };

  return (
    <div style={{ maxWidth: 400, margin: '40px auto', padding: 24, border: '1px solid #ccc', borderRadius: 8 }}>
      <h2>Stream Control</h2>
      <div style={{ margin: '12px 8px', textAlign: 'left' }}>
        <div style={{ fontWeight: 600, marginBottom: 6 }}>RTSP input transport</div>
        <label style={{ marginRight: 16 }}>
          <input
            type="radio"
            name="rtspTransport"
            value="tcp"
            checked={rtspTransport === 'tcp'}
            onChange={(e) => setRtspTransport(e.target.value)}
          />
          TCP
        </label>
        <label>
          <input
            type="radio"
            name="rtspTransport"
            value="udp"
            checked={rtspTransport === 'udp'}
            onChange={(e) => setRtspTransport(e.target.value)}
          />
          UDP
        </label>
      </div>
      <button onClick={handleStartRTSP} disabled={loading} style={{ margin: 8 }}>Start RTSP Stream</button>
      <button onClick={() => stopAndStart('start-fallback')} disabled={loading} style={{ margin: 8 }}>Start Fallback Stream</button>
      <button onClick={() => callApi('stop-fallback')} disabled={loading} style={{ margin: 8 }}>Stop Fallback Stream</button>
      <button onClick={() => callApi('stop')} disabled={loading} style={{ margin: 8 }}>Stop Any Stream</button>
      <div style={{ marginTop: 16, color: '#333' }}>{message}</div>
    </div>
  );
}
