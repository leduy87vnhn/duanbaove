export const getRTSPLink = (req, res) => {
  res.json({ rtsp: 'http://18.141.204.161:8889/index.m3u8' });
};