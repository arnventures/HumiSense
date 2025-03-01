import pytest
from flask import Flask
from routes.api import api_bp

@pytest.fixture
def api_client():
    # Minimale Flask-App für Tests
    app = Flask(__name__)
    # Konfiguration in app.config simulieren
    app.config["PARAMETER_SERVICE"] = ...
    app.config["REGULATION_SERVICE"] = ...
    app.config["RELAY_SERVICE"] = ...
    # usw. => Mocks/Spies für Tests
    app.register_blueprint(api_bp, url_prefix="/api")
    client = app.test_client()
    yield client

def test_get_status_no_regulation_service(api_client):
    # Entfernt den Service-Eintrag, damit es zu einem Error kommt
    del api_client.application.config["REGULATION_SERVICE"]
    response = api_client.get("/api/status")
    assert response.status_code == 500
    assert b"Required service not available" in response.data

def test_get_config(api_client):
    # Angenommen, wir hätten einen Mock/Stub in PARAMETER_SERVICE
    response = api_client.get("/api/config")
    assert response.status_code == 200
    # Hier kann man Details checken, z. B. ob JSON-Felder vorhanden sind
