# app.py
from flask import Flask
from flask_cors import CORS
from routes.api import api_bp
from routes.views import views_bp
from services.parameter_service import ParameterService
from services.logging_service import LoggingService
from services.station_service import StationService
from services.regulation_service import RegulationService
from services.sensor_service import SHT31Sensor
from services.relay_service import RelayService
from services.log_reader_service import LogReaderService
from config import Config

app = Flask(__name__)
CORS(app)

# Initialize services using static defaults from Config.
parameter_service = ParameterService("config.json")
logging_service = LoggingService(Config.INITIAL_LOG_FILE)
station_service = StationService(logging_service, Config)
# Test lgpio with RelayService
print("Initializing RelayService to test lgpio...")
relay_service = RelayService()
print("RelayService initialized successfully! lgpio is working.")
sensor = SHT31Sensor()
regulation_service = RegulationService(sensor, station_service, parameter_service, logging_service, relay_service)
log_reader_service = LogReaderService(parameter_service)

# Start background services (e.g., regulation thread)
regulation_service.start()

# Dependency Injection: Store services in app.config for use in routes.
app.config["PARAMETER_SERVICE"] = parameter_service
app.config["LOGGING_SERVICE"] = logging_service
app.config["STATION_SERVICE"] = station_service
app.config["REGULATION_SERVICE"] = regulation_service
app.config["RELAY_SERVICE"] = relay_service
app.config["LOG_READER_SERVICE"] = log_reader_service

# Register blueprints:
# The views blueprint serves HTML templates at root URLs.
app.register_blueprint(views_bp);
# The API blueprint serves JSON endpoints under /api.
app.register_blueprint(api_bp, url_prefix="/api");

if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5000, threaded=True)
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        regulation_service.stop()
        relay_service.cleanup()
