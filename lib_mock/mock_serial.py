import random
import logging

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s][%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

class Serial:
    def __init__(self, port, baudrate, timeout=None):
        logger.info(f"Initialized on port {port} at {baudrate} baud")
        self._buffer = b""
        self.timeout = timeout

    def flushInput(self):
        logger.info("flushInput called")
        self._buffer = b""

    def reset_input_buffer(self):
        logger.info("reset_input_buffer called")
        self._buffer = b""

    def write(self, data):
        logger.info(f"write: {data}")
        if b"AT+CGPS=1,1" in data:
            self._buffer = b"OK\r\n"
        elif b"AT+CGPSINFO" in data:
            # --- Đặt gốc quanh Hà Nội ---
            lat_goc = 21.028511
            lon_goc = 105.804817
            # Mỗi lần random dịch chuyển rất nhỏ: (-0.0005 đến +0.0005)
            lat = lat_goc + random.uniform(-0.0005, 0.0005)
            lon = lon_goc + random.uniform(-0.0005, 0.0005)

            # Convert sang định dạng xxYY.YYY (deg, minute)
            lat_deg = int(lat)
            lat_min = (lat - lat_deg) * 60
            lat_str = f"{lat_deg:02d}{lat_min:06.3f}"

            lon_deg = int(lon)
            lon_min = (lon - lon_deg) * 60
            lon_str = f"{lon_deg:03d}{lon_min:06.3f}"

            rest = "110925,172254.0,0.5,0.0"  # tốc độ thấp, giống xe di chuyển chậm
            self._buffer = bytes(f"+CGPSINFO: {lat_str},N,{lon_str},E,{rest}\r\n", "ascii")
        return len(data)


    def inWaiting(self):
        return len(self._buffer)

    @property
    def in_waiting(self):
        return len(self._buffer)

    def read(self, n=1):
        data = self._buffer[:n]
        self._buffer = self._buffer[n:]
        return data

    def readline(self):
        if b"\n" in self._buffer:
            index = self._buffer.index(b"\n") + 1
            line = self._buffer[:index]
            self._buffer = self._buffer[index:]
            return line
        else:
            line = self._buffer
            self._buffer = b""
            return line

    def close(self):
        logger.info("[MOCK Serial] close() called")
