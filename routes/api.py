from flask import Blueprint, jsonify, request, current_app
from dateutil import parser as dateparser
import json, os

api_bp = Blueprint("api", __name__)

# ------------------- STATUS ENDPOINT -------------------
@api_bp.route("/status", methods=["GET"])
def get_status():
    """
    Liefert den aktuellen Status aus dem RegulationService. 
    Wenn die Steuerung im manuellen Modus ist (Hand/Aus), wird 
    der tatsächliche Relaiszustand abgefragt und zurückgegeben.
    """
    try:
        regulation_service = current_app.config.get("REGULATION_SERVICE")
        station_service = current_app.config.get("STATION_SERVICE")
        relay_service = current_app.config.get("RELAY_SERVICE")
        if regulation_service is None or relay_service is None:
            raise Exception("Required service not available")

        # Basisstatus aus der Regelungslogik
        status = regulation_service.get_status()

        # Bei manuellem Modus im status regeln wir das Feld "regulation_state" 
        # auf den echten Relaiszustand (relay_on/relay_off)
        if status.get("regulation_state") in ["Hand", "Aus", "relay_off", "relay_on"]:
            actual_state = relay_service.get_state()["state"]
            status["regulation_state"] = "relay_on" if actual_state else "relay_off"

        # Zusätzlicher Komfort: Namen der externen Station holen, falls möglich
        if status.get("api_station") and station_service:
            stations = station_service.fetch_stations()
            station_name = next((s.name for s in stations if s.station_id == status["api_station"]), None)
            status["api_station_name"] = station_name if station_name else status["api_station"]

        return jsonify(status)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------- CONFIG ENDPOINTS -------------------
@api_bp.route("/config", methods=["GET"])
def get_config():
    """
    GET /api/config liefert die aktuelle Konfiguration (z. B. Schwellwerte).
    """
    try:
        parameter_service = current_app.config.get("PARAMETER_SERVICE")
        if parameter_service is None:
            raise Exception("Parameter service not available")
        return jsonify(parameter_service.get_config())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route("/config", methods=["POST"])
def update_config():
    """
    POST /api/config aktualisiert die Konfiguration (im ParameterService).
    """
    try:
        parameter_service = current_app.config.get("PARAMETER_SERVICE")
        if parameter_service is None:
            raise Exception("Parameter service not available")
        new_config = request.get_json()
        if new_config is None:
            raise ValueError("Invalid JSON")
        parameter_service.update_config(new_config)
        return jsonify({"message": "Configuration updated", "config": parameter_service.get_config()})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ------------------- SENSOR ENDPOINT -------------------
@api_bp.route("/sensor", methods=["GET"])
def get_sensor():
    """
    GET /api/sensor gibt Temperatur- und Feuchtewerte (innen/außen) sowie ihre Differenz zurück,
    basierend auf dem letzten Status des RegulationService.
    """
    try:
        regulation_service = current_app.config.get("REGULATION_SERVICE")
        if regulation_service is None:
            raise Exception("Regulation service not available")
        status = regulation_service.get_status()
        sensor_data = {
            "local_temperature": status.get("local_temperature"),
            "local_humidity": status.get("local_humidity"),
            "inside_absolute_humidity": status.get("inside_absolute_humidity"),
            "api_station": status.get("api_station"),
            "api_temperature": status.get("api_temperature"),
            "api_humidity": status.get("api_humidity"),
            "outside_absolute_humidity": status.get("outside_absolute_humidity"),
            "difference": status.get("difference")
        }
        return jsonify(sensor_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------- STATION ENDPOINT -------------------
@api_bp.route("/stations", methods=["GET"])
def get_stations():
    """
    GET /api/stations liefert eine einfache Übersicht aller abgerufenen Stationen 
    (ID und Name), basierend auf dem StationService-Cache.
    """
    try:
        station_service = current_app.config.get("STATION_SERVICE")
        if station_service is None:
            raise Exception("Station service not available")
        stations = station_service.fetch_stations()
        stations_list = [{"id": s.station_id, "station_name": s.name} for s in stations]
        return jsonify({"stations": stations_list})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------- LOGS ENDPOINTS -------------------
@api_bp.route("/logs", methods=["GET"])
def get_logs():
    """
    GET /api/logs?start=YYYY-MM-DDT...&end=...&event=...&limit=...
    Liest gefilterte Logs aus dem LogReaderService.
    """
    try:
        log_reader = current_app.config.get("LOG_READER_SERVICE")
        if log_reader is None:
            raise Exception("Log reader service not available")
        start_param = request.args.get("start")
        end_param = request.args.get("end")
        event_filter = request.args.get("event")
        limit = int(request.args.get("limit", 100))

        logs = log_reader.get_filtered_logs(start_param, end_param, event_filter, limit)
        return jsonify(logs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route("/dashboard", methods=["GET"])
def get_dashboard_data():
    """
    GET /api/dashboard - Sonder-Endpunkt für die Haupt-Ansicht,
    gibt nur die Logs mit event='status_update' zurück.
    """
    try:
        log_reader = current_app.config.get("LOG_READER_SERVICE")
        if log_reader is None:
            raise Exception("Log reader service not available")
        limit = int(request.args.get("limit", 100))
        logs = log_reader.get_filtered_logs(event_filter="status_update", limit=limit)
        logs.sort(key=lambda x: x.get("timestamp", 0))
        return jsonify(logs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------- RELAY ENDPOINTS -------------------
@api_bp.route("/relay", methods=["GET"])
def get_relay_state():
    """
    GET /api/relay liefert den aktuellen Zustand des Relays (an/aus, Modus).
    """
    try:
        relay_service = current_app.config.get("RELAY_SERVICE")
        if relay_service is None:
            raise Exception("Relay service not available")
        state = relay_service.get_state()
        return jsonify({"relay_state": state})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route("/relay/on", methods=["POST"])
def relay_on():
    """
    POST /api/relay/on schaltet das Relais ein (optional mit Delay),
    wenn der Modus dies erlaubt.
    """
    try:
        relay_service = current_app.config.get("RELAY_SERVICE")
        if relay_service is None:
            raise Exception("Relay service not available")
        data = request.get_json() or {}
        delay = data.get("delay", 0)
        auto_flag = data.get("auto", False)
        message = relay_service.turn_on(delay=delay, auto=auto_flag)
        return jsonify({"message": message, "relay_state": relay_service.get_state()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route("/relay/off", methods=["POST"])
def relay_off():
    """
    POST /api/relay/off schaltet das Relais aus (optional mit Delay).
    """
    try:
        relay_service = current_app.config.get("RELAY_SERVICE")
        if relay_service is None:
            raise Exception("Relay service not available")
        data = request.get_json() or {}
        delay = data.get("delay", 0)
        auto_flag = data.get("auto", False)
        message = relay_service.turn_off(delay=delay, auto=auto_flag)
        return jsonify({"message": message, "relay_state": relay_service.get_state()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route("/relay/force_off", methods=["POST"])
def relay_force_off():
    """
    POST /api/relay/force_off erzwingt ein sofortiges Ausschalten 
    (Notfall / Brandalarm).
    """
    try:
        relay_service = current_app.config.get("RELAY_SERVICE")
        if relay_service is None:
            raise Exception("Relay service not available")
        message = relay_service.force_off()
        return jsonify({"message": message, "relay_state": relay_service.get_state()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route("/relay/mode", methods=["POST"])
def set_relay_mode():
    """
    POST /api/relay/mode wechselt den Modus des Relays (Auto, Hand, Aus),
    speichert dies im ParameterService und schaltet ggf. sofort das Relais.
    """
    try:
        relay_service = current_app.config.get("RELAY_SERVICE")
        parameter_service = current_app.config.get("PARAMETER_SERVICE")
        if relay_service is None or parameter_service is None:
            raise Exception("Required service not available")
        data = request.get_json() or {}
        mode = data.get("mode")
        if mode not in ["Hand", "Aus", "Auto"]:
            raise ValueError("Invalid mode")

        # In der Config persistent aktualisieren:
        parameter_service.update_config({"relay_mode": mode})
        # Gleich im RelayService setzen:
        relay_service.set_mode(mode)
        # Sofortige Schaltaktion in Abhängigkeit vom Modus
        if mode == "Hand":
            relay_service.turn_on(delay=0, auto=True)
        elif mode == "Aus":
            relay_service.turn_off(delay=0, auto=True)

        return jsonify({"message": f"Mode set to {mode}", "mode": mode})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
