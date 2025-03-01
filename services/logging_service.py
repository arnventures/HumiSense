import json, time, threading

class LoggingService:
    def __init__(self, log_file):
        # Pfad zur Logdatei, z. B. "log.json"
        self.log_file = log_file
        # Lock für Thread-Sicherheit
        self.lock = threading.Lock()

    def log(self, entry: dict):
        """
        Ergaenzt den Eintrag um einen Zeitstempel und schreibt ihn als JSON-Zeile ins Logfile.
        """
        entry["timestamp"] = time.time()
        # Mit Lock absichern, damit keine zwei Threads gleichzeitig schreiben
        with self.lock:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
