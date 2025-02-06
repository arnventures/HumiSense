import requests
import time
import logging
from models.station import Station
from models.log_entry import LogEntry

class StationService:
    """
    Service zur Verwaltung von Wetterstationen. Lädt Temperatur- und Feuchtigkeitswerte
    von der Swiss Meteo API und speichert die letzten Daten im Cache.
    """

    def __init__(self, logging_service, config):
        """
        Initialisiert den StationService.
        
        :param logging_service: Service für Logging-Funktionalität.
        :param config: Konfigurationsobjekt mit API-URLs und Cache-Settings.
        """
        self.logging_service = logging_service
        self.config = config
        self.cached_stations = []
        self.last_fetch_time = 0

    def fetch_stations(self):
        """
        Ruft Wetterstationsdaten von der API ab, sofern der Cache abgelaufen ist.
        Andernfalls werden die gecachten Stationen zurückgegeben.
        
        :return: Liste der Station-Objekte.
        """
        current_time = time.time()
        if self.cached_stations and (current_time - self.last_fetch_time < self.config.CACHE_EXPIRATION_SECONDS):
            logging.info("Cache gültig – gebe gecachte Stationen zurück.")
            return self.cached_stations

        logging.info("Abrufen der Stationsdaten von der API...")
        humidity_data = self._fetch_data(self.config.HUMIDITY_URL)
        temperature_data = self._fetch_data(self.config.TEMPERATURE_URL)

        if not humidity_data or not temperature_data:
            logging.warning("Fehler beim Abrufen der API-Daten. Verwende vorhandenen Cache.")
            return self.cached_stations

        self.cached_stations = self._combine_data(humidity_data, temperature_data)
        self.last_fetch_time = current_time

        self._log_aggregate_data()

        return self.cached_stations

    def _fetch_data(self, url):
        """
        Ruft JSON-Daten von der angegebenen URL ab.
        
        :param url: Die URL, von der die Daten geladen werden.
        :return: Liste der Features (Daten) oder None im Fehlerfall.
        """
        try:
            logging.info(f"Rufe Daten von {url} ab...")
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            logging.debug(f"Antwort von {url}: {response.text[:200]}")
            return data.get("features", [])
        except requests.exceptions.RequestException as e:
            logging.error(f"Fehler beim Abrufen von {url}: {e}")
            return None

    def _combine_data(self, humidity_data, temperature_data):
        """
        Kombiniert Feuchtigkeits- und Temperaturdaten zu Station-Objekten.
        
        :param humidity_data: Liste der Feuchtigkeitsdaten.
        :param temperature_data: Liste der Temperaturdaten.
        :return: Liste von Station-Objekten.
        """
        combined = []
        for humidity_station in humidity_data:
            station_id = humidity_station.get("id")
            matching_temp = next((t for t in temperature_data if t.get("id") == station_id), None)
            if not matching_temp:
                logging.info(f"Keine Temperaturdaten für Station {station_id} gefunden. Station wird übersprungen.")
                continue

            try:
                station = Station(
                    station_id=station_id,
                    name=humidity_station["properties"].get("station_name", "Unbekannt"),
                    humidity=humidity_station["properties"].get("value"),
                    temperature=matching_temp["properties"].get("value"),
                    coordinates=humidity_station["geometry"].get("coordinates")
                )
                combined.append(station)
            except Exception as e:
                logging.error(f"Fehler beim Erstellen des Station-Objekts für {station_id}: {e}")

        logging.info(f"{len(combined)} Stationen erfolgreich kombiniert.")
        return combined

    def _log_aggregate_data(self):
        """
        Erstellt einen Log-Eintrag mit der Gesamtzahl der geladenen Stationen.
        """
        try:
            log_entry = LogEntry(
                category="weather",
                data={
                    "total_stations": len(self.cached_stations),
                    "timestamp": time.time()
                }
            )
            self.logging_service.log(log_entry)
        except Exception as e:
            logging.error(f"Fehler beim Logging der aggregierten Wetterdaten: {e}")
