import StreamControl from './StreamControl';
import React, { useState } from 'react';
import MonitorVideo from './screens/MonitorVideo';

function App() {
  const [rtspUrl, setRtspUrl] = useState('');

  return (
    <div className="App">
      <StreamControl rtspUrl={rtspUrl} />
      <MonitorVideo onRtspUrlChange={setRtspUrl} />
    </div>
  );
}

export default App;
