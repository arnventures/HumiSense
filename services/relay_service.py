import time, logging, threading, lgpio

class RelayService:
    # Standardverzögerungen in Sekunden beim Ein- und Ausschalten
    ON_DELAY = 2
    OFF_DELAY = 2

    # GPIO-Pins (Relais / LED)
    RELAY_PIN = 17
    LED_PIN = 5

    def __init__(self):
        # Standardzustände
        self.relay_pin = RelayService.RELAY_PIN
        self.led_pin = RelayService.LED_PIN
        self.state = False       # False = Aus, True = An
        self.brand_alarm = False # Notfallzustand (Brandalarm)
        self.mode = "Auto"       # "Hand", "Aus" oder "Auto"
        self.current_thread = None

        # GPIO-Chip öffnen und Pins als Ausgang belegen
        self.chip = lgpio.gpiochip_open(0)
        lgpio.gpio_claim_output(self.chip, self.relay_pin, 0)
        lgpio.gpio_claim_output(self.chip, self.led_pin, 0)

    def _execute_after_delay(self, action, delay):
        """Führt nach einer Verzögerung das Ein- oder Ausschalten aus."""
        time.sleep(delay)
        if action == "on" and not self.brand_alarm:
            self._turn_on()
        elif action == "off":
            self._turn_off()

    def _turn_on(self):
        """Interne Methode zum sofortigen Einschalten."""
        lgpio.gpio_write(self.chip, self.relay_pin, 1)
        lgpio.gpio_write(self.chip, self.led_pin, 1)
        self.state = True
        logging.info("Relay turned on.")

    def _turn_off(self):
        """Interne Methode zum sofortigen Ausschalten."""
        lgpio.gpio_write(self.chip, self.relay_pin, 0)
        lgpio.gpio_write(self.chip, self.led_pin, 0)
        self.state = False
        logging.info("Relay turned off.")

    def turn_on(self, delay=None, auto=False):
        """
        Zeitgesteuertes Einschalten.
        delay: Zeit in Sekunden. Falls None, wird ON_DELAY verwendet.
        auto: Flag, ob die Aktion aus dem 'Auto'-Modus initiiert wird.
        """
        # Wenn nicht Auto-Modus und der aktuelle Modus != "Hand", dann blockieren
        if not auto and self.mode != "Hand":
            return "Manual control is only allowed in Hand mode!"

        # Wenn ein Brandalarm aktiv ist, bleibt das Relais aus
        if self.brand_alarm:
            return "Emergency active! Relay remains off!"

        # Wenn das Relais bereits an ist, nichts tun
        if self.state:
            return "Relay is already on!"

        delay = delay if delay is not None else self.ON_DELAY
        logging.info(f"Relay will turn on in {delay} seconds...")

        # Falls schon ein alter Thread läuft, verwerfen
        if self.current_thread and self.current_thread.is_alive():
            self.current_thread = None

        # Neuer Thread, der nach Ablauf von 'delay' das Relais einschaltet
        self.current_thread = threading.Thread(target=self._execute_after_delay, args=("on", delay))
        self.current_thread.start()
        return f"Relay scheduled to turn on in {delay} seconds."

    def turn_off(self, delay=None, auto=False):
        """
        Zeitgesteuertes Ausschalten.
        delay: Zeit in Sekunden. Falls None, wird OFF_DELAY verwendet.
        auto: Flag, ob die Aktion aus dem 'Auto'-Modus initiiert wird.
        """
        if not auto and self.mode != "Hand":
            return "Manual control is only allowed in Hand mode!"

        if not self.state:
            return "Relay is already off!"

        delay = delay if delay is not None else self.OFF_DELAY
        logging.info(f"Relay will turn off in {delay} seconds...")

        if self.current_thread and self.current_thread.is_alive():
            self.current_thread = None

        self.current_thread = threading.Thread(target=self._execute_after_delay, args=("off", delay))
        self.current_thread.start()
        return f"Relay scheduled to turn off in {delay} seconds."

    def force_off(self):
        """Sofortiges Ausschalten (Brandalarm)."""
        self.brand_alarm = True
        if self.current_thread and self.current_thread.is_alive():
            self.current_thread = None
        self._turn_off()
        return "Emergency: Relay turned off immediately!"

    def set_mode(self, mode):
        """Setzt den Betriebsmodus ('Hand', 'Aus', 'Auto')."""
        if mode not in ["Hand", "Aus", "Auto"]:
            raise ValueError("Invalid mode")
        self.mode = mode
        logging.info(f"Mode set to {mode}.")

        # Bei Modus "Aus" sofort ausschalten und evtl. Thread stoppen
        if mode == "Aus":
            if self.current_thread and self.current_thread.is_alive():
                self.current_thread = None
            self._turn_off()
        return self.mode

    def get_state(self):
        """
        Liefert den aktuellen Zustand des Relais und den aktuellen Modus.
        state: True/False
        mode: "Hand", "Aus", "Auto"
        """
        return {"state": self.state, "mode": self.mode}

    def cleanup(self):
        """Schließt den GPIO-Chip und räumt Ressourcen auf."""
        lgpio.gpiochip_close(self.chip)
        logging.info("GPIO cleaned up.")
