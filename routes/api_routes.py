#!/usr/bin/env python3
from flask import Blueprint, jsonify, request, render_template
import os, json
from dateutil import parser as dateparser  # pip install python-dateutil

api = Blueprint("api", __name__)

# Globale Dienst-Instanzen (werden im Hauptprogramm initialisiert)
regulation_service = None
parameter_service = None
relay_service = None
station_service = None

# --- Hilfsfunktionen ---
def get_log_file_path():
    # Hole den Logfile-Pfad aus der Konfiguration oder verwende "log.json"
    config = parameter_service.get_config() if parameter_service else {}
    logging_config = config.get("logging", {})
    return logging_config.get("log_file", "log.json")

def tail_lines(file_path, num_lines=100):
    """Liest die letzten num_lines Zeilen aus file_path."""
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r") as f:
        lines = f.readlines()
    return lines[-num_lines:]

# --- Bestehende Routen ---
@api.route("/")
def home():
    return render_template("home.html")

@api.route("/config")
def config():
    return render_template("config.html")

@api.route("/logs")
def logs_page():
    return render_template("logs.html")

@api.route("/api/status", methods=["GET"])
def get_status():
    if regulation_service:
        return jsonify(regulation_service.get_status())
    else:
        return jsonify({"error": "Regulation service nicht verfügbar"}), 500

@api.route("/api/config", methods=["GET"])
def get_config():
    if parameter_service:
        return jsonify(parameter_service.get_config())
    else:
        return jsonify({"error": "Parameter service nicht verfügbar"}), 500

@api.route("/api/config", methods=["POST"])
def update_config():
    new_config = request.get_json()
    if new_config is None:
        return jsonify({"error": "Ungültiges JSON"}), 400
    parameter_service.update_config(new_config)
    return jsonify({"message": "Konfiguration aktualisiert", "config": parameter_service.get_config()})

@api.route("/api/sensor", methods=["GET"])
def get_sensor():
    if regulation_service:
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
    else:
        return jsonify({"error": "Regulation service nicht verfügbar"}), 500

@api.route("/api/stations", methods=["GET"])
def get_stations():
    try:
        # Stelle sicher, dass station_service global verfügbar ist.
        stations = station_service.fetch_stations()
        # Erstelle eine Liste mit den gewünschten Informationen (z.B. ID und Station-Name)
        stations_list = [{"id": s.station_id, "station_name": s.name} for s in stations]
        return jsonify({"stations": stations_list})
    except Exception as e:
        return jsonify({"error": "Fehler beim Abrufen der Stationen", "details": str(e)}), 500




@api.route("/api/relay", methods=["GET"])
def get_relay_state():
    if relay_service:
        state = relay_service.get_state()
        return jsonify({"relay_state": state})
    else:
        return jsonify({"error": "Relay service nicht verfügbar"}), 500

@api.route("/api/relay/on", methods=["POST"])
def relay_on():
    data = request.get_json() or {}
    delay = data.get("delay", 0)
    message = relay_service.turn_on(delay=delay)
    return jsonify({"message": message, "relay_state": relay_service.get_state()})

@api.route("/api/relay/off", methods=["POST"])
def relay_off():
    data = request.get_json() or {}
    delay = data.get("delay", 0)
    message = relay_service.turn_off(delay=delay)
    return jsonify({"message": message, "relay_state": relay_service.get_state()})

@api.route("/api/relay/force_off", methods=["POST"])
def relay_force_off():
    message = relay_service.force_off()
    return jsonify({"message": message, "relay_state": relay_service.get_state()})

@api.route("/api/relay/mode", methods=["POST"])
def set_relay_mode():
    data = request.get_json() or {}
    mode = data.get("mode")
    if mode not in ["Hand", "Aus", "Auto"]:
        return jsonify({"error": "Ungültiger Modus"}), 400
    try:
        relay_service.set_mode(mode)
        return jsonify({"message": f"Modus auf {mode} gesetzt", "mode": mode})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Neuer Endpunkt zum Filtern der Logeinträge
@api.route("/api/logs", methods=["GET"])
def get_filtered_logs():
    # Erwarte optionale Query-Parameter: start, end, event, limit
    start_param = request.args.get("start", None)
    end_param = request.args.get("end", None)
    event_filter = request.args.get("event", None)
    try:
        limit = int(request.args.get("limit", 100))
    except ValueError:
        limit = 100

    start_time = None
    end_time = None
    try:
        if start_param:
            start_time = dateparser.isoparse(start_param).timestamp()
        if end_param:
            end_time = dateparser.isoparse(end_param).timestamp()
    except Exception as e:
        return jsonify({"error": "Ungültiges Datumsformat"}), 400

    log_file = get_log_file_path()
    filtered_logs = []
    try:
        # Nutze file_read_backwards, um zeilenweise (rückwärts) einzulesen
        from file_read_backwards import FileReadBackwards
        with FileReadBackwards(log_file, encoding="utf-8") as frb:
            for line in frb:
                try:
                    entry = json.loads(line)
                except:
                    continue
                ts = entry.get("timestamp")
                if ts is None:
                    continue
                # Filter: Zeitbereich
                if start_time and ts < start_time:
                    continue
                if end_time and ts > end_time:
                    continue
                # Filter: Event
                if event_filter and entry.get("event") != event_filter:
                    continue
                filtered_logs.append(entry)
                if len(filtered_logs) >= limit:
                    break
    except Exception as e:
        return jsonify({"error": "Fehler beim Lesen des Logfiles"}), 500

    filtered_logs.reverse()  # Umkehrung, da wir rückwärts gelesen haben
    return jsonify(filtered_logs), 200


@api.route("/api/dashboard", methods=["GET"])
def get_dashboard_data():
    """
    Dieser Endpunkt liefert ein Array von Datenpunkten (aus dem Logfile),
    wobei jeder Datenpunkt folgende Felder enthält:
      - timestamp
      - inside_absolute_humidity
      - outside_absolute_humidity
      - difference
    Optional kann der Query-Parameter 'limit' gesetzt werden (Standard: 100).
    """
    try:
        limit = int(request.args.get("limit", 100))
    except ValueError:
        limit = 100

    log_file = get_log_file_path()
    try:
        # Lies die letzten Zeilen aus dem Logfile
        lines = tail_lines(log_file, num_lines=limit * 2)
    except Exception as e:
        return jsonify({"error": "Logfile konnte nicht gelesen werden"}), 500

    dashboard_data = []
    # Verarbeite die Zeilen in umgekehrter Reihenfolge (neuste zuerst)
    for line in reversed(lines):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue  # Überspringe ungültige Zeilen
        if entry.get("event") == "status_update":
            status = entry.get("status", {})
            data_point = {
                "timestamp": entry.get("timestamp"),
                "inside_absolute_humidity": status.get("inside_absolute_humidity"),
                "outside_absolute_humidity": status.get("outside_absolute_humidity"),
                "difference": status.get("difference")
            }
            dashboard_data.append(data_point)
            if len(dashboard_data) >= limit:
                break

    dashboard_data.sort(key=lambda x: x["timestamp"])
    return jsonify(dashboard_data), 200