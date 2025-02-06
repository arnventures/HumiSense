#!/usr/bin/env python3
import os
from flask import Flask
from flask_cors import CORS

# Importiere unsere Services
from services.parameter_service import ParameterService
from services.logging_service import LoggingService
from services.regulation_service import RegulationService

# Externe Module (müssen in Deinem Projekt vorhanden sein)
from config import Config                 # Statische Konfiguration (z. B. API‑URLs)
from services.station_service import StationService  # Swiss Meteo API
from services.relay_service import RelayService        # Relais‑Steuerung
from services.local_sensor_service import SHT31Sensor          # Lokaler SHT31‑Sensor
from services.logging_service import LoggingService

app = Flask(__name__)
CORS(app)

# Blueprint importieren und registrieren
from routes.api_routes import api as api_routes
app.register_blueprint(api_routes)

# Globale Instanzen initialisieren
parameter_service = ParameterService("config.json")
config_data = parameter_service.get_config()
log_file = config_data.get("logging", {}).get("log_file", "log.json")
logging_service = LoggingService(log_file=log_file)

station_service = StationService(logging_service, Config)
relay_service = RelayService()
sensor = SHT31Sensor()

regulation_service = RegulationService(sensor, station_service, relay_service, parameter_service, logging_service)
regulation_service.daemon = True
regulation_service.start()

# Diese globalen Variablen werden auch im Blueprint verwendet:
import routes.api_routes as api_mod
api_mod.regulation_service = regulation_service
api_mod.parameter_service = parameter_service
api_mod.relay_service = relay_service

if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=3000, threaded=True)
    except KeyboardInterrupt:
        print("Abbruch durch Benutzer...")
    finally:
        if regulation_service:
            regulation_service.stop()
        if relay_service:
            relay_service.cleanup()
