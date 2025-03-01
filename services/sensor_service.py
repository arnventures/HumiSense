import time
import logging
import smbus2
from abc import ABC, abstractmethod

class SensorInterface(ABC):
    """
    Ein generisches Sensor-Interface mit einer Methode zum Auslesen
    von Messwerten. Ermöglicht eine einfache Austauschbarkeit oder Mocking.
    """
    @abstractmethod
    def read_sensor(self):
        pass

class SHT31Sensor(SensorInterface):
    """
    Spezialisiert auf das Auslesen der Temperatur und Luftfeuchtigkeit
    von einem SHT31-Sensor per I2C.
    """
    SHT31_I2C_ADDR = 0x44  # Standard-I2C-Adresse des SHT31

    def __init__(self, bus_id=1):
        # Erstellt ein SMBus-Objekt (I2C-Bus), Standard ist häufig Bus #1
        self.bus = smbus2.SMBus(bus_id)

    def read_sensor(self):
        """
        Liest Temperatur und relative Luftfeuchtigkeit vom SHT31-Sensor.
        Gibt ein Tupel (temperature, humidity) zurück.
        """
        try:
            # Sende den "Single shot measurement"-Befehl
            self.bus.write_i2c_block_data(self.SHT31_I2C_ADDR, 0x24, [0x00])
            time.sleep(0.015)  # Kurze Wartezeit, damit der Sensor messen kann

            # Lese 6 Bytes: [MSB Temp, LSB Temp, CRC Temp, MSB Feuchte, LSB Feuchte, CRC Feuchte]
            data = self.bus.read_i2c_block_data(self.SHT31_I2C_ADDR, 0x00, 6)

            # Rohwerte zusammensetzen
            raw_temp = (data[0] << 8) | data[1]
            raw_hum = (data[3] << 8) | data[4]

            # Umrechnung anhand Datenblatt
            temperature = -45 + (175 * (raw_temp / 65535.0))
            humidity = 100 * (raw_hum / 65535.0)

            # Plausibilitätsprüfung der Werte
            if not (-40 <= temperature <= 125):
                raise ValueError("Temperature out of range")
            if not (0 <= humidity <= 100):
                raise ValueError("Humidity out of range")

            return temperature, humidity

        except Exception as e:
            logging.error(f"Error reading sensor: {e}")
            # Verpackt jede Exception in eine RuntimeError
            raise RuntimeError(f"Error reading sensor: {e}")
