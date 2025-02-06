import time
import logging
import threading
import lgpio  # Raspberry Pi 5 GPIO-Steuerung

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class RelayService:
    """
    Klasse zur Steuerung eines Relais mit LED-Anzeige und verschiedenen Betriebsmodi:
      - Hand: Manuelle Steuerung (direktes Schalten)
      - Aus: Relais bleibt immer AUS
      - Auto: Automatische Steuerung durch den RegulationService
    """

    ON_DELAY = 2  # Standardverzögerung vor dem Einschalten
    OFF_DELAY = 2  # Standardverzögerung vor dem Ausschalten
    RELAY_PIN = 17  # Standard-Relais-Pin
    LED_PIN = 5     # Standard-LED-Pin

    def __init__(self):
        """
        Initialisiert das Relais und die LED über die GPIO-Pins.
        Standardmäßig ist der Modus auf "Auto" gesetzt.
        """
        self.relay_pin = RelayService.RELAY_PIN
        self.led_pin = RelayService.LED_PIN
        self.state = False         # False = Aus, True = Ein
        self.brand_alarm = False   # Notfall-Modus aktiv?
        self.mode = "Auto"         # Betriebsmodus: "Hand", "Aus" oder "Auto"
        self.current_thread = None  # Aktueller Delay-Thread

        # GPIOs initialisieren
        self.chip = lgpio.gpiochip_open(0)
        lgpio.gpio_claim_output(self.chip, self.relay_pin, 0)  # Relais startet AUS
        lgpio.gpio_claim_output(self.chip, self.led_pin, 0)      # LED startet AUS

    def _execute_after_delay(self, action, delay):
        """
        Führt eine Aktion (on/off) nach einer Verzögerung aus, sofern diese nicht unterbrochen wird.
        """
        time.sleep(delay)
        if action == "on" and not self.brand_alarm:
            self._turn_on()
        elif action == "off":
            self._turn_off()

    def _turn_on(self):
        """Schaltet das Relais und die LED sofort ein."""
        lgpio.gpio_write(self.chip, self.relay_pin, 1)
        lgpio.gpio_write(self.chip, self.led_pin, 1)  # LED an
        self.state = True
        logging.info("✅ Relais wurde eingeschaltet.")

    def _turn_off(self):
        """Schaltet das Relais und die LED sofort aus."""
        lgpio.gpio_write(self.chip, self.relay_pin, 0)
        lgpio.gpio_write(self.chip, self.led_pin, 0)  # LED aus
        self.state = False
        logging.info("✅ Relais wurde ausgeschaltet.")

    def turn_on(self, delay=None, auto=False):
        """
        Schaltet das Relais ein.
        Wenn auto==False, ist die manuelle Steuerung nur im Handmodus möglich.
        :param delay: (Optional) Verzögerung in Sekunden, ansonsten ON_DELAY
        :param auto: Wenn True, wird die Aktion auch in anderen Modi erlaubt (z. B. im Auto-Modus)
        :return: Statusmeldung als String
        """
        if not auto and self.mode != "Hand":
            return "⚠ Manuelle Steuerung ist nur im Handmodus möglich!"
        if self.brand_alarm:
            return "🚨 Notfall aktiv! Relais bleibt AUS!"
        if self.state:
            return "⚠ Relais ist bereits EIN!"

        delay = delay if delay is not None else self.ON_DELAY
        logging.info(f"⏳ Relais wird in {delay} Sekunden eingeschaltet...")

        if self.current_thread and self.current_thread.is_alive():
            self.current_thread = None

        self.current_thread = threading.Thread(target=self._execute_after_delay, args=("on", delay))
        self.current_thread.start()
        return f"✅ Einschaltung geplant (nach {delay} Sekunden)."

    def turn_off(self, delay=None, auto=False):
        """
        Schaltet das Relais aus.
        Wenn auto==False, ist die manuelle Steuerung nur im Handmodus möglich.
        :param delay: (Optional) Verzögerung in Sekunden, ansonsten OFF_DELAY
        :param auto: Wenn True, wird die Aktion auch in anderen Modi erlaubt (z. B. im Auto-Modus)
        :return: Statusmeldung als String
        """
        if not auto and self.mode != "Hand":
            return "⚠ Manuelle Steuerung ist nur im Handmodus möglich!"
        if not self.state:
            return "⚠ Relais ist bereits AUS!"

        delay = delay if delay is not None else self.OFF_DELAY
        logging.info(f"⏳ Relais wird in {delay} Sekunden ausgeschaltet...")

        if self.current_thread and self.current_thread.is_alive():
            self.current_thread = None

        self.current_thread = threading.Thread(target=self._execute_after_delay, args=("off", delay))
        self.current_thread.start()
        return f"✅ Ausschaltung geplant (nach {delay} Sekunden)."


    def force_off(self):
        """
        Schaltet das Relais sofort aus (Notfall, Brandkontakt).
        """
        self.brand_alarm = True  # Notfallmodus aktivieren
        if self.current_thread and self.current_thread.is_alive():
            self.current_thread = None
        self._turn_off()
        return "🚨 Notfall: Relais wurde SOFORT ausgeschaltet!"

    def set_mode(self, mode):
        """
        Setzt den Betriebsmodus des Relais.
        Mögliche Modi: "Hand", "Aus", "Auto"
        :param mode: Gewünschter Modus
        :return: Der gesetzte Modus
        """
        if mode not in ["Hand", "Aus", "Auto"]:
            raise ValueError("Ungültiger Modus")
        self.mode = mode
        logging.info(f"Modus auf {mode} gesetzt.")
        if mode == "Aus":
            # Im "Aus"-Modus soll das Relais stets ausgeschaltet sein
            if self.current_thread and self.current_thread.is_alive():
                self.current_thread = None
            self._turn_off()
        return self.mode

    def get_state(self):
        """
        Gibt den aktuellen Zustand und den Modus des Relais zurück.
        :return: Dict mit "state" (True/False) und "mode"
        """
        return {"state": self.state, "mode": self.mode}

    def cleanup(self):
        """
        Schließt die GPIO-Verbindung.
        """
        lgpio.gpiochip_close(self.chip)
        logging.info("GPIOs zurückgesetzt.")


if __name__ == "__main__":
    # Testmodus: Steuerung über die Konsole
    relay = RelayService()
    try:
        while True:
            print(f"\n🔹 Aktueller Zustand: {'EIN' if relay.get_state()['state'] else 'AUS'}; Modus: {relay.get_state()['mode']}")
            cmd = input("Befehl (on/off/force_off/set_mode/reset_fire/exit): ").strip().lower()
            if cmd == "on":
                delay = float(input("Verzögerung (Sekunden, 0 für sofort): "))
                print(relay.turn_on(delay))
            elif cmd == "off":
                delay = float(input("Verzögerung (Sekunden, 0 für sofort): "))
                print(relay.turn_off(delay))
            elif cmd == "force_off":
                print(relay.force_off())
            elif cmd == "set_mode":
                mode = input("Neuer Modus (Hand/Aus/Auto): ").strip()
                try:
                    print(relay.set_mode(mode))
                except Exception as e:
                    print(f"Fehler: {e}")
            elif cmd == "reset_fire":
                # Beispiel: Rücksetzen des Notfallmodus könnte hier implementiert werden
                relay.brand_alarm = False
                print("Notfallmodus zurückgesetzt.")
            elif cmd == "exit":
                break
            else:
                print("Ungültiger Befehl!")
    except KeyboardInterrupt:
        print("\nAbbruch durch Benutzer.")
    finally:
        relay.cleanup()
