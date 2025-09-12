# GPS_web_app/mock_rpi/GPIO.py
import logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s][%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

class GPIO:
    BCM = 'BCM'
    OUT = 'OUT'
    HIGH = 1
    LOW = 0

    @staticmethod
    def setmode(mode):
        logger.info(f"[MOCK GPIO] setmode({mode})")

    @staticmethod
    def setwarnings(flag):
        logger.info(f"[MOCK GPIO] setwarnings({flag})")

    @staticmethod
    def setup(pin, mode):
        logger.info(f"[MOCK GPIO] setup(pin={pin}, mode={mode})")

    @staticmethod
    def output(pin, value):
        val_str = "HIGH" if value else "LOW"
        logger.info(f"[MOCK GPIO] output(pin={pin}, value={val_str})")

    @staticmethod
    def cleanup():
        logger.info("[MOCK GPIO] cleanup()")
