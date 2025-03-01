import pytest
import time
from unittest.mock import MagicMock
from services.regulation_service import RegulationService

@pytest.fixture
def mock_sensor():
    sensor = MagicMock()
    # Standardwerte für 'read_sensor()'
    sensor.read_sensor.return_value = (20.0, 50.0)  # 20°C, 50% rF
    return sensor

@pytest.fixture
def mock_station_service():
    station_service = MagicMock()
    # Standard: Station liefert 10°C, 80% rF
    mock_station = MagicMock()
    mock_station.station_id = "ARO"
    mock_station.temperature = 10.0
    mock_station.humidity = 80.0
    station_service.fetch_stations.return_value = [mock_station]
    return station_service

@pytest.fixture
def mock_parameter_service():
    parameter_service = MagicMock()
    # Standard-Regulation-Parameter
    parameter_service.get_config.return_value = {
        "api_station_id": "ARO",
        "regulation": {
            "on_threshold": 2.0,
            "off_threshold": 1.7,
            "on_delay": 0,
            "off_delay": 0,
            "max_on_time": 5,
            "local_sensor_poll_interval": 0.1,
            "test_mode": True  # Damit Verzögerungen entfallen, falls gewünscht
        },
        "relay_mode": "Auto"
    }
    return parameter_service

@pytest.fixture
def mock_logging_service():
    return MagicMock()

@pytest.fixture
def mock_relay_service():
    relay_service = MagicMock()
    relay_service.turn_on.return_value = "Relay turning on"
    relay_service.turn_off.return_value = "Relay turning off"
    return relay_service

@pytest.fixture
def regulation_service_instance(mock_sensor, mock_station_service, mock_parameter_service, 
                                mock_logging_service, mock_relay_service):
    service = RegulationService(
        sensor=mock_sensor,
        station_service=mock_station_service,
        parameter_service=mock_parameter_service,
        logging_service=mock_logging_service,
        relay_service=mock_relay_service
    )
    yield service
    service.stop()
    service.join(timeout=1)

def test_regulation_starts_and_stops(regulation_service_instance):
    """
    Testet, ob sich der Thread problemlos starten und stoppen lässt.
    """
    regulation_service_instance.start()
    time.sleep(0.3)
    regulation_service_instance.stop()
    regulation_service_instance.join(timeout=1)
    assert not regulation_service_instance.is_alive(), "Service-Thread sollte beendet sein"

def test_auto_mode_relay_on_off(regulation_service_instance, mock_sensor, mock_station_service, 
                                mock_parameter_service, mock_logging_service, mock_relay_service):
    """
    Testet, ob im Auto-Modus das Relais eingeschaltet wird,
    wenn die Differenz der absoluten Feuchte über on_threshold liegt.
    """
    regulation_service_instance.start()
    time.sleep(0.5)
    # Zunächst sollte das Relais noch nicht eingeschaltet sein
    assert not mock_relay_service.turn_on.called, "Relay sollte anfangs nicht eingeschaltet sein"

    # Sensor- und Stationsdaten so manipulieren, dass der Unterschied deutlich über on_threshold liegt:
    # z.B. innen: 30°C, 80% (hohe absolute Feuchte)
    # aussen: 10°C, 50% (niedrige absolute Feuchte)
    mock_sensor.read_sensor.return_value = (30.0, 80.0)
    station = mock_station_service.fetch_stations.return_value[0]
    station.temperature = 10.0
    station.humidity = 50.0
    time.sleep(0.5)
    
    # Nun sollte der pending_on-Zustand abgelaufen sein und turn_on wird aufgerufen:
    assert mock_relay_service.turn_on.called, "Relay sollte in Auto-Modus eingeschaltet werden"

    # Kurz warten und dann den Service stoppen
    time.sleep(1.0)
    regulation_service_instance.stop()
    regulation_service_instance.join(timeout=1)

    # Prüfen, ob Log-Einträge geschrieben wurden
    assert mock_logging_service.log.called, "Es sollten Logeinträge geschrieben worden sein"

def test_manual_mode_block_auto(regulation_service_instance, mock_parameter_service, mock_relay_service):
    """
    Testet, dass im 'Hand'-Modus keine automatische Regelung erfolgt.
    """
    # Vor Start 'Hand'-Modus einstellen
    config_mock = mock_parameter_service.get_config.return_value
    config_mock["relay_mode"] = "Hand"

    regulation_service_instance.start()
    time.sleep(0.5)
    regulation_service_instance.stop()
    regulation_service_instance.join(timeout=1)

    # RelayService sollte nicht automatisch getriggert werden
    assert not mock_relay_service.turn_on.called, "Im Hand-Modus darf kein automatisches Einschalten geschehen"
