import json, os, threading

class ParameterService:
    def __init__(self, filepath):
        # Pfad zur Konfigurationsdatei (z. B. "config.json")
        self.filepath = filepath
        # Lock für Thread-Sicherheit
        self.lock = threading.Lock()
        # Beim Erzeugen wird die Konfiguration sofort geladen (oder neu erstellt)
        self.config = self.load_config()

    def load_config(self):
        """
        Lädt eine vorhandene JSON-Datei.
        Falls sie nicht existiert, wird eine Datei mit Standardwerten angelegt.
        """
        if os.path.exists(self.filepath):
            # Datei bereits vorhanden? Dann JSON einlesen
            with open(self.filepath, "r") as f:
                return json.load(f)
        else:
            # Erstelle eine neue Standardkonfiguration
            default_config = {
                "api_station_id": "ARO",
                "regulation": {
                    "on_threshold": 2.0,
                    "off_threshold": 1.7,
                    "on_delay": 60,
                    "off_delay": 300,
                    "max_on_time": 300,
                    "local_sensor_poll_interval": 1,
                    "api_poll_interval": 600
                },
                "logging": {
                    "log_file": "log.json"
                },
                "relay_mode": "Auto"
            }
            # Neue Konfiguration in Datei speichern
            with open(self.filepath, "w") as f:
                json.dump(default_config, f, indent=4)
            return default_config

    def get_config(self):
        """
        Gibt eine Kopie der aktuellen Konfiguration zurück.
        Mit Lock, um Thread-Konflikte beim Lesen zu vermeiden.
        """
        with self.lock:
            return self.config.copy()

    def update_config(self, new_config):
        """
        Aktualisiert bestimmte Werte der Konfiguration und schreibt sie in die Datei.
        """
        with self.lock:
            self.config.update(new_config)
            with open(self.filepath, "w") as f:
                json.dump(self.config, f, indent=4)
