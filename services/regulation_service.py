import math, time, threading, logging

class RegulationService(threading.Thread):
    """
    Liest kontinuierlich Sensor- und Stationsdaten und entscheidet,
    wann das Relais eingeschaltet oder ausgeschaltet werden soll.
    """

    def __init__(self, sensor, station_service, parameter_service, logging_service, relay_service):
        super().__init__()
        # Referenzen auf andere Services
        self.sensor = sensor
        self.station_service = station_service
        self.parameter_service = parameter_service
        self.logging_service = logging_service
        self.relay_service = relay_service

        # Thread-Stop-Signal
        self._stop_event = threading.Event()

        # Internes State-Management
        self.state = "idle"  # "idle", "pending_on", "relay_on", "Hand", "Aus", etc.
        self.pending_on_start = None
        self.pending_off_start = None
        self.relay_on_start = None

        # Letzter bekannter Status in Form eines Dictionaries
        self.status = {}

    def compute_absolute_humidity(self, rh, t):
        """
        Berechnet die absolute Feuchte (g/m^3) aus relativer Feuchte (rh, in %) und Temperatur (t, in °C).
        """
        a = 6.112
        b = 17.67
        c = 243.5
        svp = a * math.exp((b * t) / (c + t))
        vp = (rh / 100.0) * svp
        mw = 18.016
        rs = 8314.3
        ah = 1e5 * mw / rs * vp / (t + 273.15)
        return ah

    def get_api_station(self):
        """
        Liest aus den Parametern die 'api_station_id' und sucht
        in den abgerufenen Stationen den passenden Eintrag.
        """
        config = self.parameter_service.get_config()
        station_id = config.get("api_station_id", "ARO")
        stations = self.station_service.fetch_stations()
        for s in stations:
            if s.station_id == station_id:
                return s
        return None

    def run(self):
        """
        Haupt-Loop, der regelmaessig:
         - Lokalen Sensor ausliest
         - Externe Station (Temperatur/Feuchte) abfragt
         - Differenz bildet und anhand von Schwellwerten das Relais steuert.
         - In 'Auto'-Modus erfolgt die Steuerung automatisch;
           in 'Hand'/'Aus' wird der manuelle Zustand respektiert.
        """
        while not self._stop_event.is_set():
            regulation_params = self.parameter_service.get_config().get("regulation", {})
            on_threshold  = regulation_params.get("on_threshold", 2.0)
            off_threshold = regulation_params.get("off_threshold", 1.7)
            on_delay      = regulation_params.get("on_delay", 60)
            off_delay     = regulation_params.get("off_delay", 300)
            max_on_time   = regulation_params.get("max_on_time", 300)
            poll_interval = regulation_params.get("local_sensor_poll_interval", 1)
            test_mode     = regulation_params.get("test_mode", False)

            # Falls test_mode eingeschaltet ist, entfaellt die Einschaltverzoegerung
            if test_mode:
                on_delay = 0

            current_time = time.time()
            try:
                # Lokalen Sensorwert (innen) holen
                local_temp, local_rh = self.sensor.read_sensor()
            except Exception as e:
                # Falls Sensorfehler, Log-Eintrag und zyklisch weitermachen
                self.logging_service.log({"event": "local_sensor_error", "error": str(e)})
                time.sleep(poll_interval)
                continue

            # Absolute Feuchte innen
            inside_ah = self.compute_absolute_humidity(local_rh, local_temp)

            # API-Station (außen) abrufen
            api_station = self.get_api_station()
            if api_station and api_station.temperature is not None and api_station.humidity is not None:
                outside_ah = self.compute_absolute_humidity(api_station.humidity, api_station.temperature)
            else:
                outside_ah = None

            diff = inside_ah - outside_ah if outside_ah is not None else None

            # Status-Dictionary fuer Monitoring
            status = {
                "local_temperature": round(local_temp, 2),
                "local_humidity": round(local_rh, 2),
                "inside_absolute_humidity": round(inside_ah, 2),
                "api_station": api_station.station_id if api_station else None,
                "api_temperature": round(api_station.temperature, 2) if (api_station and api_station.temperature is not None) else None,
                "api_humidity": round(api_station.humidity, 2) if (api_station and api_station.humidity is not None) else None,
                "outside_absolute_humidity": round(outside_ah, 2) if outside_ah is not None else None,
                "difference": round(diff, 2) if diff is not None else None,
            }

            # Modus abfragen (Auto, Hand, Aus)
            relay_mode = self.parameter_service.get_config().get("relay_mode", "Auto")
            if relay_mode != "Auto":
                # Wenn nicht Auto, uebernehmen wir den manuellen Zustand
                self.state = relay_mode
            else:
                # Wenn von Manuell nach Auto gewechselt wurde, internen State resetten
                if self.state not in ["idle", "pending_on", "relay_on"]:
                    self.logging_service.log({
                        "event": "auto_mode_reset",
                        "message": f"Switching from manual ({self.state}) to Auto mode, resetting state to idle."
                    })
                    self.state = "idle"
                    self.pending_on_start = None
                    self.pending_off_start = None
                    self.relay_on_start = None

                # Zustandsautomat
                if self.state == "idle":
                    # Bedingung fuer Einschalten erfuellt?
                    if diff is not None and diff > on_threshold:
                        self.pending_on_start = current_time
                        self.state = "pending_on"
                        self.logging_service.log({
                            "event": "pending_on_started",
                            "message": f"Diff {round(diff,2)} > {on_threshold}"
                        })

                elif self.state == "pending_on":
                    # Einschaltbedingung entfaellt?
                    if diff is None or diff <= on_threshold:
                        self.state = "idle"
                        self.pending_on_start = None
                        self.logging_service.log({
                            "event": "pending_on_cancelled",
                            "message": "Condition no longer met"
                        })
                    # Zeit abgelaufen => Einschalten
                    elif current_time - self.pending_on_start >= on_delay:
                        self.relay_on_start = current_time
                        self.state = "relay_on"
                        self.pending_on_start = None
                        self.logging_service.log({
                            "event": "relay_turned_on",
                            "message": "Relay turned on"
                        })
                        self.relay_service.turn_on(delay=0, auto=True)

                elif self.state == "relay_on":
                    # Schutz: Abschalten nach max_on_time
                    if current_time - self.relay_on_start >= max_on_time:
                        self.logging_service.log({
                            "event": "max_on_time_exceeded",
                            "message": "Max on time exceeded, turning relay off"
                        })
                        self.state = "idle"
                        self.relay_on_start = None
                        self.pending_off_start = None
                        self.relay_service.turn_off(delay=0, auto=True)
                    else:
                        # Bedingung fuer Ausschalten?
                        if diff is not None and diff < off_threshold:
                            if self.pending_off_start is None:
                                self.pending_off_start = current_time
                                self.logging_service.log({
                                    "event": "pending_off_started",
                                    "message": f"Diff {round(diff,2)} < {off_threshold}"
                                })
                        else:
                            if self.pending_off_start is not None:
                                self.logging_service.log({
                                    "event": "pending_off_cancelled",
                                    "message": "Diff above off threshold"
                                })
                                self.pending_off_start = None

                        # Off-Delay erreicht => abschalten
                        if self.pending_off_start is not None and (current_time - self.pending_off_start >= off_delay):
                            self.logging_service.log({
                                "event": "relay_turned_off",
                                "message": "Relay turned off after off delay"
                            })
                            self.state = "idle"
                            self.relay_on_start = None
                            self.pending_off_start = None
                            self.relay_service.turn_off(delay=0, auto=True)

            # Letzten Status updaten
            status["regulation_state"] = self.state
            self.status = status
            self.logging_service.log({"event": "status_update", "status": self.status})

            # Kurze Wartezeit bis zur naechsten Runde
            time.sleep(poll_interval)

    def stop(self):
        """
        Signalisiert dem Thread, sich zu beenden.
        """
        self._stop_event.set()

    def get_status(self):
        """
        Liefert den zuletzt erfassten Status (Temperatur, Feuchte,
        Relay-Zustand usw.).
        """
        return self.status
