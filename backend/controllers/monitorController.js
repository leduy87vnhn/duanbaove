export const getRTSPLink = (req, res) => {
  res.json({
    rtsp: 'rtsp://10.0.50.6:8554/camera',
    hls_internal: 'http://172.10.0.2:8503/hls/stream.m3u8',
    hls_public: 'http://103.116.104.4:8503/hls/stream.m3u8'
  });
};