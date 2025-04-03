import time
import logging
import smbus2
from abc import ABC, abstractmethod

class SensorInterface(ABC):
    """
    A generic sensor interface with a method to read values.
    Enables easy replacement or mocking.
    """
    @abstractmethod
    def read_sensor(self):
        pass

class SHT31Sensor(SensorInterface):
    """
    Specialized sensor service for reading temperature and humidity
    from a SHT31 sensor via I2C.
    """
    SHT31_I2C_ADDR = 0x44  # Standard I2C address for SHT31

    def __init__(self, bus_id=1, indicator_service=None):
        """
        Initializes the sensor with the specified I2C bus.
        Optionally accepts an indicator_service to control the fault LED.
        """
        self.bus = smbus2.SMBus(bus_id)
        self.indicator_service = indicator_service

    def read_sensor(self):
        """
        Reads temperature and relative humidity from the SHT31 sensor.
        Returns a tuple (temperature, humidity).
        
        If the reading is successful and within plausible ranges, the fault LED is turned off.
        If any error occurs or the values are out of range, the fault LED is turned on and a
        RuntimeError is raised.
        """
        try:
            # Send the "single shot measurement" command.
            self.bus.write_i2c_block_data(self.SHT31_I2C_ADDR, 0x24, [0x00])
            time.sleep(0.015)  # Short wait for sensor measurement

            # Read 6 bytes: [MSB Temp, LSB Temp, CRC Temp, MSB Humidity, LSB Humidity, CRC Humidity]
            data = self.bus.read_i2c_block_data(self.SHT31_I2C_ADDR, 0x00, 6)

            # Assemble raw values
            raw_temp = (data[0] << 8) | data[1]
            raw_hum = (data[3] << 8) | data[4]

            # Convert raw values using the humidity formula
            temperature = -45 + (175 * (raw_temp / 65535.0))
            humidity = 100 * (raw_hum / 65535.0)

            # Plausibility check
            if not (-40 <= temperature <= 125):
                raise ValueError("Temperature out of range")
            if not (0 <= humidity <= 100):
                raise ValueError("Humidity out of range")

            # Reading successful: clear any fault LED if indicator_service is available.
            if self.indicator_service:
                self.indicator_service.set_fault_led(False)

            return temperature, humidity

        except Exception as e:
            logging.error(f"Error reading sensor: {e}")
            # On error, trigger the fault LED if available.
            if self.indicator_service:
                self.indicator_service.set_fault_led(True)
            raise RuntimeError(f"Error reading sensor: {e}")
