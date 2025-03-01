import pytest
import time
from unittest.mock import patch, MagicMock
from station_service import StationService

class MockConfig:
    CACHE_EXPIRATION_SECONDS = 60
    HUMIDITY_URL = "http://testserver/humidity"
    TEMPERATURE_URL = "http://testserver/temperature"

@pytest.fixture
def station_service_instance():
    # Einfacher Mock fuer LoggingService
    class MockLoggingService:
        def log(self, entry):
            pass

    return StationService(
        logging_service=MockLoggingService(),
        config=MockConfig
    )

@patch("station_service.requests.get")
def test_fetch_stations_cache(mock_get, station_service_instance):
    """
    Testet, ob der Cache greift, wenn bereits Daten vorhanden sind 
    und die Cache-Zeit noch nicht abgelaufen ist.
    """
    # Zuerst: Mock-Daten zurueckgeben (1. Abruf)
    mock_get.return_value = MagicMock(status_code=200, json=lambda: {"features": [{"id": "ABC", "properties": {"value": 55.0}}]})
    
    # Erster Aufruf: Fuehrt tatsaechlich einen Request aus
    stations_first = station_service_instance.fetch_stations()
    assert len(stations_first) == 0, "Fuer die Kombination brauchen wir Temperatur UND Feuchte"

    # Beim 2. Request stellen wir nochmal Mock-Daten bereit, aber ...
    # ... wenn die Cache-Pruefung greift, sollte die fetch_stations() gar nicht neu anfragen
    stations_second = station_service_instance.fetch_stations()

    # Pruefen, dass nur 2 Requests gesendet wurden (Feuchte + Temperatur) vom 1. Aufruf
    # Danach beim 2. Aufruf kein weiterer Request (wegen Cache)
    assert mock_get.call_count == 2, "Bei erneutem fetch_stations sollte der Cache greifen"

    # Zeit vergeht, um Cache ablaufen zu lassen
    time.sleep(1)
    # Mock-Daten fuer Temperatur, damit es diesmal eine Kombination gibt
    def side_effect(url, timeout=5):
        if "temperature" in url:
            return MagicMock(status_code=200, json=lambda: {"features": [{"id": "ABC", "properties": {"value": 22.5}}]})
        else:
            return MagicMock(status_code=200, json=lambda: {"features": [{"id": "ABC", "properties": {"value": 55.0}}]})
    mock_get.side_effect = side_effect

    # Manuell die last_fetch_time hacken, damit der Cache als abgelaufen gilt
    station_service_instance.last_fetch_time -= 999

    stations_third = station_service_instance.fetch_stations()
    assert len(stations_third) == 1, "Jetzt sollte ein kombinierter Datensatz fuer Station ABC vorhanden sein"
    assert stations_third[0].temperature == 22.5
    assert stations_third[0].humidity == 55.0
    # Jetzt wurden 2 weitere Requests fuer Feuchte und Temperatur abgesetzt
    assert mock_get.call_count == 4

@patch("station_service.requests.get")
def test_fetch_stations_error_handling(mock_get, station_service_instance):
    """
    Testet, ob StationService bei Fehlern im Request
    die aktuellen Cachdaten (falls vorhanden) beibehalt.
    """
    # Legen wir einen initialen 'gueltigen' Cache an
    def side_effect_first(url, timeout=5):
        if "humidity" in url:
            return MagicMock(status_code=200, json=lambda: {"features": [{"id": "XYZ", "properties": {"value": 50.0}}]})
        else:
            return MagicMock(status_code=200, json=lambda: {"features": [{"id": "XYZ", "properties": {"value": 20.0}}]})
    mock_get.side_effect = side_effect_first

    initial_stations = station_service_instance.fetch_stations()
    assert len(initial_stations) == 1

    # Nun Fehler simulieren (z.B. 404)
    def side_effect_error(url, timeout=5):
        response_mock = MagicMock()
        response_mock.raise_for_status.side_effect = Exception("404 Not Found")
        return response_mock

    mock_get.side_effect = side_effect_error

    # Neuer Fetch: API fehlgeschlagen, Service sollte None zurueckbekommen
    # ... und die alten Cachdaten liefern
    stations_after_error = station_service_instance.fetch_stations()
    assert len(stations_after_error) == 1, "Sollte immer noch 1 Station aus dem alten Cache sein"

@patch("station_service.requests.get")
def test_combine_data_no_match(mock_get, station_service_instance):
    """
    Testet den Fall, dass Temperatur- und Feuchte-Listen keine 
    uebereinstimmenden Station-IDs haben.
    """
    # Feuchte-Liste hat ID 'ABC', Temperatur-Liste ID 'XYZ'
    def side_effect(url, timeout=5):
        if "humidity" in url:
            return MagicMock(status_code=200, json=lambda: {"features": [{"id": "ABC", "properties": {"value": 60.0}}]})
        else:
            return MagicMock(status_code=200, json=lambda: {"features": [{"id": "XYZ", "properties": {"value": 15.0}}]})

    mock_get.side_effect = side_effect

    stations = station_service_instance.fetch_stations()
    # Keine einzige gemeinsame ID => Komplette Ergebnisliste leer
    assert len(stations) == 0
