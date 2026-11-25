import time
from config import CFG

class PiPower5Reader:
    """Read SunFounder PiPower 5 over I2C if available.

    If smbus2 is not installed, I2C is disabled, or the HAT is not present,
    returns a dict with available=False so the web can show N/A safely.
    """
    def __init__(self):
        self.last = {"available": False, "error": "not read yet"}
        self.last_ts = 0.0
        self._bus = None
        self._init_error = ""
        try:
            from smbus2 import SMBus
            self._SMBus = SMBus
        except Exception as e:
            self._SMBus = None
            self._init_error = f"smbus2 not installed: {e}"

    def _open(self):
        if self._bus is not None:
            return self._bus
        if not CFG.pipower_enabled:
            raise RuntimeError("PiPower disabled in config")
        if self._SMBus is None:
            raise RuntimeError(self._init_error)
        self._bus = self._SMBus(CFG.pipower_i2c_bus)
        return self._bus

    @staticmethod
    def _u16(buf, i):
        # PiPower docs expose u16 registers. Most Pi SMBus devices use little endian here.
        le = buf[i] | (buf[i+1] << 8)
        be = (buf[i] << 8) | buf[i+1]
        # choose the more plausible value for millivolt/milliamp ranges
        if le > 65000 and be < 20000:
            return be
        return le

    @staticmethod
    def _i16(buf, i):
        v = PiPower5Reader._u16(buf, i)
        return v - 65536 if v & 0x8000 else v

    def read(self):
        now = time.time()
        if now - self.last_ts < 1.0:
            return self.last
        self.last_ts = now
        try:
            bus = self._open()
            data = bus.read_i2c_block_data(CFG.pipower_i2c_addr, 0, 20)
            self.last = {
                "available": True,
                "input_voltage_v": self._u16(data, 0) / 1000.0,
                "input_current_a": self._u16(data, 2) / 1000.0,
                "output_voltage_v": self._u16(data, 4) / 1000.0,
                "output_current_a": self._u16(data, 6) / 1000.0,
                "battery_voltage_v": self._u16(data, 8) / 1000.0,
                "battery_current_a": self._i16(data, 10) / 1000.0,
                "battery_percent": int(data[12]),
                "capacity_mah": self._u16(data, 13),
                "power_source": int(data[15]),
                "usb_connected": int(data[16]),
                "charging": int(data[18]),
                "error": "",
            }
        except Exception as e:
            self.last = {"available": False, "error": str(e)}
        return self.last

PIPOWER5 = PiPower5Reader()
