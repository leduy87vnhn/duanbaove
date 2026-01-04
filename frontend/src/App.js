import VideoPlayer from './VideoPlayer';
import StreamControl from './StreamControl';
import React from 'react';
import MonitorVideo from './screens/MonitorVideo';

function App() {
  return (
    <div className="App">
      <StreamControl />
      <MonitorVideo />
      <VideoPlayer />
    </div>
  );
}

export default App;