export const getRTSPLink = (req, res) => {
  res.json({
    rtsp: 'rtsp://admin:Abcd121@113.185.6.120:554/Streaming/Channels/101',
    hls_internal: 'http://172.10.0.2:8503/hls/stream.m3u8',
    hls_public: 'http://103.116.104.4:8503/hls/stream.m3u8'
  });
};