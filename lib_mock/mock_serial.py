# GPS_web_app/mock_rpi/_serial.py
class Serial:
    def __init__(self, port, baudrate):
        print(f"[MOCK Serial] Initialized on port {port} at {baudrate} baud")
        self._buffer = b""

    def flushInput(self):
        print("[MOCK Serial] flushInput called")
        self._buffer = b""

    def write(self, data):
        print(f"[MOCK Serial] write: {data}")
        # mock trả về 'OK' cho mọi lệnh AT
        if b"AT+CGPS=1,1" in data:
            self._buffer = b"OK\r\n"
        elif b"AT+CGPSINFO" in data:
            # Trả GPS mẫu
            self._buffer = b"+CGPSINFO: 2100.123456,N,10550.654321,E,110925,172254.0,42.7,0.0\r\n"

    def inWaiting(self):
        return len(self._buffer)

    def read(self, n):
        data = self._buffer[:n]
        self._buffer = self._buffer[n:]
        return data
