import React, { useState } from 'react';

const API_BASE = 'http://172.10.0.2:8503/api/stream';

export default function StreamControl() {
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const callApi = async (endpoint) => {
    setLoading(true);
    setMessage('');
    try {
      const res = await fetch(`${API_BASE}/${endpoint}`, { method: 'POST' });
      const data = await res.json();
      setMessage(data.message || (data.success ? 'Thành công' : 'Lỗi'));
    } catch (err) {
      setMessage('Lỗi kết nối API');
    }
    setLoading(false);
  };

  return (
    <div style={{ maxWidth: 400, margin: '40px auto', padding: 24, border: '1px solid #ccc', borderRadius: 8 }}>
      <h2>Stream Control</h2>
      <button onClick={() => callApi('start')} disabled={loading} style={{ margin: 8 }}>Start RTSP Stream</button>
      <button onClick={() => callApi('start-fallback')} disabled={loading} style={{ margin: 8 }}>Start Fallback Stream</button>
      <button onClick={() => callApi('stop-fallback')} disabled={loading} style={{ margin: 8 }}>Stop Fallback Stream</button>
      <button onClick={() => callApi('stop')} disabled={loading} style={{ margin: 8 }}>Stop Any Stream</button>
      <div style={{ marginTop: 16, color: '#333' }}>{message}</div>
    </div>
  );
}
