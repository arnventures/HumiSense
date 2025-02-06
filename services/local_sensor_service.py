from abc import ABC, abstractmethod
import smbus2 as smbus
import time
import logging

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SensorInterface(ABC):
    """
    Abstrakte Schnittstelle für Sensoren, um verschiedene Sensoren einfach austauschbar zu machen.
    """
    
    @abstractmethod
    def read_sensor(self):
        """
        Liest Temperatur- und Feuchtigkeitswerte aus.
        Sollte von jeder konkreten Sensorklasse implementiert werden.
        """
        pass

class SHT31Sensor(SensorInterface):
    """
    Implementierung für den SHT31-Sensor, um Temperatur- und Feuchtigkeitswerte auszulesen.
    """
    
    SHT31_I2C_ADDR = 0x44  # Standard I2C-Adresse für SHT31

    def __init__(self, bus_id=1):
        """
        Initialisiert die Verbindung zum I2C-Bus.
        
        :param bus_id: Die ID des I2C-Busses (standardmäßig 1 auf Raspberry Pi)
        """
        self.bus = smbus.SMBus(bus_id)
    
    def read_sensor(self):
        """
        Liest Temperatur- und Feuchtigkeitswerte vom SHT31-Sensor.
        
        :return: (temperature in °C, humidity in %)
        :raises ValueError: Falls unrealistische Werte erkannt werden
        :raises RuntimeError: Falls das Auslesen fehlschlägt
        """
        try:
            logging.info("Starte Sensor-Messung")
            # Einzelmessung starten
            self.bus.write_i2c_block_data(self.SHT31_I2C_ADDR, 0x24, [0x00])
            time.sleep(0.015)  # Wartezeit für die Messung

            # 6 Bytes von Sensor lesen
            data = self.bus.read_i2c_block_data(self.SHT31_I2C_ADDR, 0x00, 6)

            # Rohdaten verarbeiten
            raw_temp = (data[0] << 8) | data[1]
            raw_hum = (data[3] << 8) | data[4]

            # Umrechnung in physikalische Werte
            temperature = -45 + (175 * (raw_temp / 65535.0))
            humidity = 100 * (raw_hum / 65535.0)

            logging.info(f"Gelesene Werte: Temperatur={temperature:.2f}°C, Luftfeuchtigkeit={humidity:.2f}%")

            # Werte validieren
            if not (-40 <= temperature <= 125):
                logging.error(f"Unrealistische Temperatur erkannt: {temperature}°C")
                raise ValueError(f"Unrealistische Temperatur erkannt: {temperature}°C")
            if not (0 <= humidity <= 100):
                logging.error(f"Unrealistische Luftfeuchtigkeit erkannt: {humidity}%")
                raise ValueError(f"Unrealistische Luftfeuchtigkeit erkannt: {humidity}%")
            
            return temperature, humidity
        
        except Exception as e:
            logging.exception("Fehler beim Auslesen der Sensordaten")
            raise RuntimeError(f"Fehler beim Auslesen der Sensordaten: {e}")

if __name__ == "__main__":
    sensor = SHT31Sensor()
    try:
        temperature, humidity = sensor.read_sensor()
        print(f"Temperatur: {temperature:.2f}°C, Luftfeuchtigkeit: {humidity:.2f}%")
    except RuntimeError as e:
        print(f"Fehler: {e}")
