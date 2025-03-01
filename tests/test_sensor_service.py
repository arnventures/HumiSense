import pytest
import time
from unittest.mock import MagicMock, patch
from services.sensor_service import SHT31Sensor, SensorInterface


def test_inheritance():
    """
    Testet, ob SHT31Sensor wirklich das SensorInterface implementiert.
    """
    sensor = SHT31Sensor(bus_id=1)
    assert isinstance(sensor, SensorInterface), "SHT31Sensor sollte ein SensorInterface sein"
    print("[✅] SHT31Sensor implementiert SensorInterface")


@patch('smbus2.SMBus')
def test_read_sensor_success(mock_smbus):
    """
    Testet erfolgreiches Auslesen durch Mocking der I2C-Daten.
    """
    mock_read_data = [0x6C, 0x00, 0x00, 0x3D, 0x00, 0x00]  # Beispielwerte
    mock_instance = mock_smbus.return_value
    mock_instance.read_i2c_block_data.return_value = mock_read_data

    sensor = SHT31Sensor(bus_id=1)
    temperature, humidity = sensor.read_sensor()

    assert -40 <= temperature <= 125, "Temperatur sollte in einem plausiblen Bereich liegen."
    assert 0 <= humidity <= 100, "Luftfeuchtigkeit sollte in % zwischen 0 und 100 liegen."
    print(f"[✅] Erfolgreiches Sensorlesen: Temp={temperature}°C, Hum={humidity}%")

    mock_instance.write_i2c_block_data.assert_called_once()


@patch('smbus2.SMBus')
def test_read_sensor_out_of_range_temp(mock_smbus):
    """
    Testet den Fall, dass die Temperaturwerte unplausibel sind.
    """
    mock_read_data = [0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00]  # Rohwert > 125°C
    mock_instance = mock_smbus.return_value
    mock_instance.read_i2c_block_data.return_value = mock_read_data

    sensor = SHT31Sensor(bus_id=1)

    with pytest.raises(RuntimeError) as exc_info:
        sensor.read_sensor()

    assert "Temperature out of range" in str(exc_info.value), "Sollte Temperatur-Fehler melden"
    print("[✅] Temperature out of range erkannt")


@patch('smbus2.SMBus')
def test_read_sensor_out_of_range_hum(mock_smbus):
    """
    Testet den Fall, dass die Feuchtewerte unplausibel sind.
    Falls der Code zuerst die Temperatur überprüft, kann auch dieser Fehler auftreten.
    """
    mock_read_data = [0x00, 0x00, 0x00, 0xFF, 0xFF, 0x00]  # Rohwert > 100% Feuchte
    mock_instance = mock_smbus.return_value
    mock_instance.read_i2c_block_data.return_value = mock_read_data

    sensor = SHT31Sensor(bus_id=1)

    with pytest.raises(RuntimeError) as exc_info:
        sensor.read_sensor()

    assert (
        "Temperature out of range" in str(exc_info.value)
        or "Humidity out of range" in str(exc_info.value)
    ), "Sollte Temperatur- oder Feuchte-Fehler melden"
    print("[✅] Feuchte- oder Temperaturfehler erkannt")


@patch('smbus2.SMBus')
def test_read_sensor_exception(mock_smbus):
    """
    Testet generelle Fehler (z.B. Bus nicht erreichbar),
    bei dem der Code einen RuntimeError mit passender Meldung werfen soll.
    """
    mock_instance = mock_smbus.return_value
    mock_instance.read_i2c_block_data.side_effect = IOError("I2C Bus Error")

    sensor = SHT31Sensor(bus_id=1)

    with pytest.raises(RuntimeError) as exc_info:
        sensor.read_sensor()

    assert "Error reading sensor" in str(exc_info.value), "Allgemeiner Fehler sollte geloggt werden"
    print("[✅] I2C Bus Error erkannt")

