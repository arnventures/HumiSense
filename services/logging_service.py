#!/usr/bin/env python3
import json
import time
import threading

class LoggingService:
    def __init__(self, log_file="log.json"):
        self.log_file = log_file
        self.lock = threading.Lock()

    def log(self, entry: dict):
        # Zeitstempel hinzufügen und Eintrag zeilenweise in die Logdatei schreiben
        entry["timestamp"] = time.time()
        with self.lock:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
