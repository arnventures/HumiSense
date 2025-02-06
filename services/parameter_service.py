#!/usr/bin/env python3
import json
import os
import threading

class ParameterService:
    def __init__(self, filepath="config.json"):
        self.filepath = filepath
        self.lock = threading.Lock()
        self.config = self.load_config()

    def load_config(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, "r") as f:
                return json.load(f)
        else:
            # Standardkonfiguration, falls keine Datei existiert
            default_config = {
                "api_station_id": "ARO",  # Standard: Außensensor von Station Arosa
                "regulation": {
                    "on_threshold": 2.0,              # Unterschied > 2 g/m³ → einschalten
                    "off_threshold": 1.7,             # Unterschied < 1.7 g/m³ → ausschalten
                    "on_delay": 60,                   # Einschaltverzögerung (in s)
                    "off_delay": 300,                 # Ausschaltverzögerung (in s)
                    "max_on_time": 300,               # Maximale Einschaltzeit (in s)
                    "local_sensor_poll_interval": 1,  # Abfrageintervall lokaler Sensor (in s)
                    "api_poll_interval": 600          # API-Polling-Intervall (in s, optional)
                },
                "logging": {
                    "log_file": "log.json"
                }
            }
            with open(self.filepath, "w") as f:
                json.dump(default_config, f, indent=4)
            return default_config

    def get_config(self):
        with self.lock:
            return self.config.copy()

    def update_config(self, new_config):
        with self.lock:
            self.config.update(new_config)
            with open(self.filepath, "w") as f:
                json.dump(self.config, f, indent=4)
