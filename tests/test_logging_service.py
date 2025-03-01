import pytest
import os
import json
import tempfile
import time
from services.logging_service import LoggingService

@pytest.fixture
def temp_log_file():
    """
    Erzeugt eine temporaere Logdatei.
    Wird nach dem Test wieder geloescht.
    """
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        log_filepath = tmp.name
    yield log_filepath
    if os.path.exists(log_filepath):
        os.remove(log_filepath)

def test_log_single_entry(temp_log_file):
    """
    Testet, ob ein einzelner Log-Eintrag korrekt geschrieben wird.
    """
    logger = LoggingService(temp_log_file)
    logger.log({"event": "test_event", "value": 123})

    with open(temp_log_file, "r") as f:
        lines = f.readlines()
    assert len(lines) == 1, "Sollte genau einen Eintrag haben"

    entry = json.loads(lines[0])
    assert entry["event"] == "test_event"
    assert entry["value"] == 123
    assert "timestamp" in entry

def test_log_multiple_entries(temp_log_file):
    """
    Testet das Anhängen mehrerer Eintraege.
    """
    logger = LoggingService(temp_log_file)
    for i in range(3):
        logger.log({"count": i})
    with open(temp_log_file, "r") as f:
        lines = f.readlines()
    assert len(lines) == 3, "Drei Eintraege erwartet"

def test_log_thread_safety(temp_log_file):
    """
    Grober Test, um parallele Schreibvorgaenge zu pruefen.
    """
    logger = LoggingService(temp_log_file)

    import threading

    def writer_thread(idx):
        logger.log({"thread": idx, "test": True})
        time.sleep(0.01)

    threads = []
    for i in range(10):
        t = threading.Thread(target=writer_thread, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Pruefen, ob alle Eintraege vorhanden sind
    with open(temp_log_file, "r") as f:
        lines = f.readlines()
    assert len(lines) == 10, "Alle 10 Threads sollten geschrieben haben"
