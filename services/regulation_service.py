#!/usr/bin/env python3
import math
import time
import threading

class RegulationService(threading.Thread):
    def __init__(self, sensor, station_service, relay_service, parameter_service, logging_service):
        super().__init__()
        self.sensor = sensor
        self.station_service = station_service
        self.relay_service = relay_service
        self.parameter_service = parameter_service
        self.logging_service = logging_service
        self._stop_event = threading.Event()
        self.state = "idle"  # Mögliche Zustände: idle, pending_on, relay_on
        self.pending_on_start = None
        self.pending_off_start = None
        self.relay_on_start = None
        self.status = {}  # Aktueller Status, abrufbar über die REST-API

    def compute_absolute_humidity(self, rh, t):
        # Berechnung der absoluten Feuchtigkeit (g/m³) mittels Magnus-Formel
        a = 6.112
        b = 17.67
        c = 243.5
        svp = a * math.exp((b * t) / (c + t))
        vp_val = (rh / 100.0) * svp
        mw = 18.016  # Molekulargewicht (kg/kmol)
        rs = 8314.3  # Universelle Gaskonstante
        ah = 1e5 * mw / rs * vp_val / (t + 273.15)
        return ah

    def get_api_sensor_data(self):
        # Wählt die API-Station anhand der Konfiguration aus
        config = self.parameter_service.get_config()
        station_id = config.get("api_station_id", "ARO")
        stations = self.station_service.fetch_stations()
        for station in stations:
            if station.station_id == station_id:
                return station
        return None

    def get_local_sensor_data(self):
        try:
            temperature, humidity = self.sensor.read_sensor()
            return temperature, humidity
        except Exception as e:
            self.logging_service.log({"event": "local_sensor_error", "error": str(e)})
            return None

    def run(self):
        while not self._stop_event.is_set():
            params = self.parameter_service.get_config().get("regulation", {})
            on_threshold = params.get("on_threshold", 2.0)
            off_threshold = params.get("off_threshold", 1.7)
            on_delay = params.get("on_delay", 60)
            off_delay = params.get("off_delay", 300)
            max_on_time = params.get("max_on_time", 300)
            local_poll_interval = params.get("local_sensor_poll_interval", 1)

            # Falls der RelayService nicht im Auto-Modus ist, automatische Regelung überspringen
            if self.relay_service.get_state().get("mode") != "Auto":
                time.sleep(local_poll_interval)
                continue

            # Lokaler Sensor (innen)
            local_data = self.get_local_sensor_data()
            if local_data is None:
                time.sleep(local_poll_interval)
                continue
            local_temp, local_rh = local_data
            inside_ah = self.compute_absolute_humidity(local_rh, local_temp)

            # Außensensor (API)
            api_station = self.get_api_sensor_data()
            if api_station and api_station.temperature is not None and api_station.humidity is not None:
                outside_ah = self.compute_absolute_humidity(api_station.humidity, api_station.temperature)
            else:
                outside_ah = None

            # Differenz berechnen
            diff = inside_ah - outside_ah if outside_ah is not None else None

            # Status zusammenstellen und Werte auf 2 Dezimalstellen runden
            self.status = {
                "local_temperature": round(local_temp, 2),
                "local_humidity": round(local_rh, 2),
                "inside_absolute_humidity": round(inside_ah, 2),
                "api_station": api_station.station_id if api_station else None,
                "api_temperature": round(api_station.temperature, 2) if (api_station and api_station.temperature is not None) else None,
                "api_humidity": round(api_station.humidity, 2) if (api_station and api_station.humidity is not None) else None,
                "outside_absolute_humidity": round(outside_ah, 2) if outside_ah is not None else None,
                "difference": round(diff, 2) if diff is not None else None,
                "regulation_state": self.state
            }

            current_time = time.time()
            # Zustandsautomat zur Regelung
            if self.state == "idle":
                if diff is not None and diff > on_threshold:
                    self.pending_on_start = current_time
                    self.state = "pending_on"
                    self.logging_service.log({
                        "event": "pending_on_started",
                        "message": f"Diff {round(diff,2)} > {on_threshold}, On-Timer gestartet."
                    })
            elif self.state == "pending_on":
                if diff is None or diff <= on_threshold:
                    self.state = "idle"
                    self.pending_on_start = None
                    self.logging_service.log({
                        "event": "pending_on_cancelled",
                        "message": "Bedingung während On-Delay nicht mehr erfüllt."
                    })
                elif current_time - self.pending_on_start >= on_delay:
                    self.relay_service.turn_on(delay=0, auto=True)
                    self.relay_on_start = current_time
                    self.state = "relay_on"
                    self.pending_on_start = None
                    self.logging_service.log({
                        "event": "relay_turned_on",
                        "message": "Relais nach On-Delay eingeschaltet."
                    })
            elif self.state == "relay_on":
                if current_time - self.relay_on_start >= max_on_time:
                    self.relay_service.turn_off(delay=0, auto=True)
                    self.logging_service.log({
                        "event": "max_on_time_exceeded",
                        "message": "Maximale Einschaltzeit überschritten → Relais ausgeschaltet."
                    })
                    self.state = "idle"
                    self.relay_on_start = None
                    self.pending_off_start = None
                else:
                    if diff is not None and diff < off_threshold:
                        if self.pending_off_start is None:
                            self.pending_off_start = current_time
                            self.logging_service.log({
                                "event": "pending_off_started",
                                "message": f"Diff {round(diff,2)} < {off_threshold}, Off-Timer gestartet."
                            })
                    else:
                        if self.pending_off_start is not None:
                            self.logging_service.log({
                                "event": "pending_off_cancelled",
                                "message": "Diff wieder über Off-Schwelle, Off-Timer abgebrochen."
                            })
                            self.pending_off_start = None
                    if self.pending_off_start is not None and (current_time - self.pending_off_start >= off_delay):
                        self.relay_service.turn_off(delay=0, auto=True)
                        self.logging_service.log({
                            "event": "relay_turned_off",
                            "message": "Relais nach Off-Delay ausgeschaltet."
                        })
                        self.state = "idle"
                        self.relay_on_start = None
                        self.pending_off_start = None

            # Status loggen
            self.logging_service.log({
                "event": "status_update",
                "status": self.status
            })

            time.sleep(local_poll_interval)

    def stop(self):
        self._stop_event.set()

    def get_status(self):
        return self.status
