import time
import logging
import threading
import gpiod
from gpiod.line import Direction, Value

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class RelayService:
    """
    Class to control a relay with LED indicator and various operating modes:
      - Hand: Manual control
      - Aus: Relay always off
      - Auto: Automatic control via RegulationService
    """
    ON_DELAY = 1
    OFF_DELAY = 1
    RELAY_PIN = 22
    LED_PIN = 5

    def __init__(self):
        """
        Initializes the relay and LED using GPIO pins from gpiochip0.
        Default mode is set to "Auto".
        """
        self.relay_pin = self.RELAY_PIN
        self.led_pin = self.LED_PIN
        self.state = False         # False = Off, True = On
        self.brand_alarm = False   # Emergency mode active?
        self.mode = "Auto"         # Operating mode: "Hand", "Aus" or "Auto"
        self.current_thread = None  # Current delay thread

        # Request the two required lines (relay and LED) from gpiochip0
        try:
            self.lines = gpiod.request_lines(
                "/dev/gpiochip0",
                consumer="relay_service",
                config={
                    self.RELAY_PIN: gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.INACTIVE),
                    self.LED_PIN: gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.INACTIVE),
                },
            )
            logger.info("Successfully requested GPIO lines on /dev/gpiochip0")
        except Exception as e:
            logger.error("Failed to request GPIO lines from /dev/gpiochip0: %s", str(e))
            self.lines = None

    def _execute_after_delay(self, action, delay):
        """Executes the on/off action after a delay."""
        if self.lines is None:
            logger.warning("GPIO lines not available. Cannot execute action: %s", action)
            return
        logger.info("Starting delay of %d seconds for action: %s", delay, action)
        time.sleep(delay)
        logger.info("Delay finished, executing action: %s", action)
        if action == "on" and not self.brand_alarm:
            self._turn_on()
        elif action == "off":
            self._turn_off()

    def _turn_on(self):
        """Turns on the relay and LED immediately."""
        if self.lines:
            logger.info("Turning relay ON at GPIO %d", self.relay_pin)
            self.lines.set_value(self.relay_pin, Value.ACTIVE)
            logger.info("Turning LED ON at GPIO %d", self.led_pin)
            self.lines.set_value(self.LED_PIN, Value.ACTIVE)
            self.state = True
            logger.info("Relay turned on, state: %s", self.state)
        else:
            logger.warning("GPIO lines not configured. Cannot turn on relay.")

    def _turn_off(self):
        """Turns off the relay and LED immediately."""
        if self.lines:
            logger.info("Turning relay OFF at GPIO %d", self.relay_pin)
            self.lines.set_value(self.relay_pin, Value.INACTIVE)
            logger.info("Turning LED OFF at GPIO %d", self.led_pin)
            self.lines.set_value(self.LED_PIN, Value.INACTIVE)
            self.state = False
            logger.info("Relay turned off, state: %s", self.state)
        else:
            logger.warning("GPIO lines not configured. Cannot turn off relay.")

    def turn_on(self, delay=None, auto=False):
        """
        Turns on the relay.
        Manual control is only allowed in "Hand" mode unless auto==True.
        :param delay: Optional delay in seconds (default is ON_DELAY).
        :param auto: If True, the action is allowed in any mode (e.g., in Auto mode).
        :return: Status message.
        """
        if self.lines is None:
            logger.warning("GPIO lines not available. Cannot turn on relay.")
            return "GPIO not available!"
        logger.info("turn_on called with delay=%s, auto=%s", delay, auto)
        if not auto and self.mode != "Hand":
            logger.warning("Manual control blocked: Not in Hand mode")
            return "Manual control is only allowed in Hand mode!"
        if self.brand_alarm:
            logger.warning("Emergency active: Relay remains off")
            return "Emergency active! Relay remains off!"
        if self.state:
            logger.info("Relay is already on")
            return "Relay is already on!"
        delay = delay if delay is not None else self.ON_DELAY
        logger.info("Relay will turn on in %d seconds...", delay)
        if self.current_thread and self.current_thread.is_alive():
            self.current_thread = None
        self.current_thread = threading.Thread(target=self._execute_after_delay, args=("on", delay))
        self.current_thread.start()
        return f"Relay scheduled to turn on in {delay} seconds."

    def turn_off(self, delay=None, auto=False):
        """
        Turns off the relay.
        Manual control is only allowed in "Hand" mode unless auto==True.
        :param delay: Optional delay in seconds (default is OFF_DELAY).
        :param auto: If True, the action is allowed in any mode.
        :return: Status message.
        """
        if self.lines is None:
            logger.warning("GPIO lines not available. Cannot turn off relay.")
            return "GPIO not available!"
        logger.info("turn_off called with delay=%s, auto=%s", delay, auto)
        if not auto and self.mode != "Hand":
            logger.warning("Manual control blocked: Not in Hand mode")
            return "Manual control is only allowed in Hand mode!"
        if not self.state:
            logger.info("Relay is already off")
            return "Relay is already off!"
        delay = delay if delay is not None else self.OFF_DELAY
        logger.info("Relay will turn off in %d seconds...", delay)
        if self.current_thread and self.current_thread.is_alive():
            self.current_thread = None
        self.current_thread = threading.Thread(target=self._execute_after_delay, args=("off", delay))
        self.current_thread.start()
        return f"Relay scheduled to turn off in {delay} seconds."

    def force_off(self):
        """
        Immediately turns off the relay (emergency).
        """
        if self.lines is None:
            logger.warning("GPIO lines not available. Cannot force off relay.")
            return "GPIO not available!"
        logger.info("Forcing relay off due to emergency")
        self.brand_alarm = True
        if self.current_thread and self.current_thread.is_alive():
            self.current_thread = None
        self._turn_off()
        return "Emergency: Relay turned off immediately!"

    def set_mode(self, mode):
        """
        Sets the operating mode of the relay.
        Allowed modes: "Hand", "Aus", "Auto".
        :param mode: Desired mode.
        :return: The set mode.
        """
        if mode not in ["Hand", "Aus", "Auto"]:
            raise ValueError("Invalid mode")
        self.mode = mode
        logger.info(f"Mode set to {mode}.")
        if mode == "Aus":
            if self.current_thread and self.current_thread.is_alive():
                self.current_thread = None
            self._turn_off()
        return self.mode

    def get_state(self):
        """
        Returns the current state and mode of the relay.
        :return: Dictionary with "state" (True/False) and "mode".
        """
        return {"state": self.state, "mode": self.mode}

    def cleanup(self):
        """
        Releases the GPIO lines.
        """
        if self.lines is not None:
            logger.info("Releasing GPIO lines...")
            self.lines.release()
            self.lines = None
            logger.info("GPIO lines released.")

# No __del__ method needed; use cleanup() to release resources.

if __name__ == "__main__":
    # Test mode: control via console
    relay = RelayService()
    try:
        while True:
            print(f"\nCurrent state: {'ON' if relay.get_state()['state'] else 'OFF'}; Mode: {relay.get_state()['mode']}")
            cmd = input("Command (on/off/force_off/set_mode/reset_fire/exit): ").strip().lower()
            if cmd == "on":
                delay = float(input("Delay in seconds (0 for immediate): "))
                print(relay.turn_on(delay))
            elif cmd == "off":
                delay = float(input("Delay in seconds (0 for immediate): "))
                print(relay.turn_off(delay))
            elif cmd == "force_off":
                print(relay.force_off())
            elif cmd == "set_mode":
                mode = input("New mode (Hand/Aus/Auto): ").strip()
                try:
                    print(relay.set_mode(mode))
                except Exception as e:
                    print(f"Error: {e}")
            elif cmd == "reset_fire":
                relay.brand_alarm = False
                print("Emergency mode reset.")
            elif cmd == "exit":
                break
            else:
                print("Invalid command!")
    except KeyboardInterrupt:
        print("\nUser aborted.")
    finally:
        relay.cleanup()
