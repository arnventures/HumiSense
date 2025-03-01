import requests, time, logging
from models.station import Station

class StationService:
    def __init__(self, logging_service, config):
        # Zum Loggen von Ereignissen wird ein externer LoggingService uebergeben
        self.logging_service = logging_service
        # config enthaelt wichtige Einstellungen (URLs, Cache-Dauer etc.)
        self.config = config
        self.cached_stations = []
        self.last_fetch_time = 0

    def fetch_stations(self):
        """
        Liefert die Liste aller Stationen.
        Greift nur dann auf die APIs zu, wenn der Cache abgelaufen ist.
        """
        current_time = time.time()
        # Wenn Cache noch gueltig, einfach zwischengespeicherte Stationen zurueckgeben
        if self.cached_stations and (current_time - self.last_fetch_time < self.config.CACHE_EXPIRATION_SECONDS):
            return self.cached_stations

        # Frische Daten von zwei APIs holen (Luftfeuchte / Temperatur)
        humidity_data = self._fetch_data(self.config.HUMIDITY_URL)
        temperature_data = self._fetch_data(self.config.TEMPERATURE_URL)
        if not humidity_data or not temperature_data:
            # Falls ein API-Fehler auftritt, gib vorhandene Cachdaten zurueck (kann leer sein)
            return self.cached_stations

        # Daten kombinieren und im Cache ablegen
        self.cached_stations = self._combine_data(humidity_data, temperature_data)
        self.last_fetch_time = current_time

        # Logge zusammenfassende Informationen (Anzahl Stationen)
        self._log_aggregate_data()
        return self.cached_stations

    def _fetch_data(self, url):
        """
        Hilfsfunktion zum Abruf von JSON-Daten via HTTP.
        """
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()  # Loest bei Fehlercodes eine Exception aus
            data = response.json()
            return data.get("features", [])
        except Exception as e:
            logging.error(f"Error fetching data from {url}: {e}")
            return None

    def _combine_data(self, humidity_data, temperature_data):
        """
        Kombiniert Luftfeuchte- und Temperaturdaten anhand der Stations-ID.
        Erzeugt ein Station-Objekt pro ID (sofern beide Datensaetze vorhanden sind).
        """
        combined = []
        for h in humidity_data:
            station_id = h.get("id")
            # passender Eintrag in temperature_data
            matching_temp = next((t for t in temperature_data if t.get("id") == station_id), None)
            if not matching_temp:
                continue
            try:
                station = Station(
                    station_id=station_id,
                    name=h["properties"].get("station_name", "Unknown"),
                    humidity=h["properties"].get("value"),
                    temperature=matching_temp["properties"].get("value"),
                    coordinates=h["geometry"].get("coordinates")
                )
                combined.append(station)
            except Exception as e:
                logging.error(f"Error combining data for station {station_id}: {e}")
        return combined

    def _log_aggregate_data(self):
        """
        Erzeugt einen Log-Eintrag mit der Gesamtanzahl abgerufener Stationen.
        """
        entry = {
            "category": "weather",
            "data": {"total_stations": len(self.cached_stations)}
        }
        self.logging_service.log(entry)
