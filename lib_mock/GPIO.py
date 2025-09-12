# GPS_web_app/mock_rpi/GPIO.py
class GPIO:
    BCM = 'BCM'
    OUT = 'OUT'
    HIGH = 1
    LOW = 0

    @staticmethod
    def setmode(mode):
        print(f"[MOCK GPIO] setmode({mode})")

    @staticmethod
    def setwarnings(flag):
        print(f"[MOCK GPIO] setwarnings({flag})")

    @staticmethod
    def setup(pin, mode):
        print(f"[MOCK GPIO] setup(pin={pin}, mode={mode})")

    @staticmethod
    def output(pin, value):
        print(f"[MOCK GPIO] output(pin={pin}, value={value})")

    @staticmethod
    def cleanup():
        print("[MOCK GPIO] cleanup()")


