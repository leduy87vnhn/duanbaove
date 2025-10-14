const express = require('express');
const app = express();
const { proxy, scriptUrl } = require('rtsp-relay')(app);

const cams = {
  cam1: 'rtsp://admin:Abcd121%40@113.185.6.120:8554/Streaming/Channels/101', 
};

app.ws('/api/stream/:id', (ws, req) => {
  const id = req.params.id;
  const url = cams[id];
  if (!url) return ws.close();
  proxy({ url, transport: 'tcp' })(ws, req);
});

app.get('/static/rtsp-relay.js', (req, res) => res.redirect(scriptUrl)); 
app.listen(9000, () => console.log('WebRTC RTSP relay on :9000'));
