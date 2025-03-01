import pytest
import os
import json
import tempfile
from services.parameter_service import ParameterService

@pytest.fixture
def temp_config_file():
    """
    Erstellt eine temporäre Datei, die beim Test als config.json dienen kann.
    Löscht diese nach dem Test wieder.
    """
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        filepath = tmp.name
    yield filepath
    # Aufräumen nach dem Test
    if os.path.exists(filepath):
        os.remove(filepath)

def test_load_config_new_file(temp_config_file):
    """
    Testet, dass eine neue Datei mit Standardwerten angelegt wird,
    wenn noch keine existiert.
    """
    service = ParameterService(temp_config_file)
    config = service.get_config()

    assert os.path.exists(temp_config_file), "Datei sollte neu angelegt werden"
    assert "regulation" in config, "Standardwerte sollten enthalten sein"
    assert config["relay_mode"] == "Auto"

def test_update_config(temp_config_file):
    """
    Testet, ob sich die Konfiguration korrekt aktualisieren lässt.
    """
    service = ParameterService(temp_config_file)

    # Alte Werte lesen
    old_config = service.get_config()
    assert old_config["regulation"]["on_threshold"] == 2.0

    # Neue Werte schreiben
    service.update_config({"regulation": {"on_threshold": 3.5}})
    updated_config = service.get_config()
    assert updated_config["regulation"]["on_threshold"] == 3.5

def test_thread_safety(temp_config_file):
    """
    Testet grob die Thread-Sicherheit, indem mehrere Updates parallel erfolgen.
    """
    service = ParameterService(temp_config_file)

    def updater(val):
        service.update_config({"test_value": val})

    import threading
    threads = []
    for i in range(5):
        t = threading.Thread(target=updater, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Prüfen, ob zuletzt geschriebener Wert tatsächlich ankommt
    config = service.get_config()
    # Der zuletzt ausgeführte Thread überschreibt test_value
    # Da die Reihenfolge nicht festgelegt ist, prüfen wir hier nur, 
    # dass der Key existiert (Test demonstriert Thread-Sicherheit)
    assert "test_value" in config

def test_load_existing_config(temp_config_file):
    """
    Testet, ob ein bereits bestehendes config.json korrekt eingelesen wird.
    """
    # Eine 'vorgefertigte' Datei anlegen
    mock_data = {"foo": "bar"}
    with open(temp_config_file, "w") as f:
        json.dump(mock_data, f)

    service = ParameterService(temp_config_file)
    config = service.get_config()
    assert config["foo"] == "bar", "Sollte vorhandene Werte korrekt laden"
