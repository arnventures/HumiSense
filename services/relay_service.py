import time
import logging
import threading
import gpiod

# Configure logging
logging.basicConfig(level=logging.INFO)

class RelayService:
    # Standard delays in seconds for turning on/off
    ON_DELAY = 1
    OFF_DELAY = 1

    # GPIO Pins (Relay / LED)
    RELAY_PIN = 22
    LED_PIN = 5

    def __init__(self):
        # Standard states
        self.relay_pin = RelayService.RELAY_PIN
        self.led_pin = RelayService.LED_PIN
        self.state = False  # False = Off, True = On
        self.brand_alarm = False  # Emergency state (fire alarm)
        self.mode = "Auto"  # "Hand", "Aus", or "Auto"
        self.current_thread = None

        # Open the GPIO chip (on Raspberry Pi 5, user-facing GPIOs are on gpiochip0 after kernel update)
        logging.info("Opening GPIO chip...")
        self.chip = gpiod.Chip("gpiochip0")
        logging.info("GPIO chip opened successfully.")

        # Configure the relay and LED pins as outputs
        logging.info("Configuring GPIO %d as output for relay...", self.relay_pin)
        self.relay_line = self.chip.get_line(self.relay_pin)
        self.relay_line.request(consumer="relay_service", type=gpiod.LINE_REQ_DIR_OUT, default_val=0)
        logging.info("Configuring GPIO %d as output for LED...", self.led_pin)
        self.led_line = self.chip.get_line(self.led_pin)
        self.led_line.request(consumer="relay_service", type=gpiod.LINE_REQ_DIR_OUT, default_val=0)
        logging.info("GPIO pins configured successfully.")

    def _execute_after_delay(self, action, delay):
        """Executes the on/off action after a delay."""
        logging.info("Starting delay of %d seconds for action: %s", delay, action)
        time.sleep(delay)
        logging.info("Delay finished, executing action: %s", action)
        if action == "on" and not self.brand_alarm:
            self._turn_on()
        elif action == "off":
            self._turn_off()

    def _turn_on(self):
        """Internal method to turn on immediately."""
        logging.info("Turning relay ON at GPIO %d", self.relay_pin)
        self.relay_line.set_value(1)
        logging.info("Turning LED ON at GPIO %d", self.led_pin)
        self.led_line.set_value(1)
        self.state = True
        logging.info("Relay turned on, state: %s", self.state)

    def _turn_off(self):
        """Internal method to turn off immediately."""
        logging.info("Turning relay OFF at GPIO %d", self.relay_pin)
        self.relay_line.set_value(0)
        logging.info("Turning LED OFF at GPIO %d", self.led_pin)
        self.led_line.set_value(0)
        self.state = False
        logging.info("Relay turned off, state: %s", self.state)

    def turn_on(self, delay=None, auto=False):
        """
        Timed turn-on.
        delay: Time in seconds. If None, ON_DELAY is used.
        auto: Flag indicating if the action is initiated from 'Auto' mode.
        """
        logging.info("turn_on called with delay=%s, auto=%s", delay, auto)
        if not auto and self.mode != "Hand":
            logging.warning("Manual control blocked: Not in Hand mode")
            return "Manual control is only allowed in Hand mode!"
        if self.brand_alarm:
            logging.warning("Emergency active: Relay remains off")
            return "Emergency active! Relay remains off!"
        if self.state:
            logging.info("Relay is already on")
            return "Relay is already on!"
        delay = delay if delay is not None else self.ON_DELAY
        logging.info("Relay will turn on in %d seconds...", delay)
        if self.current_thread and self.current_thread.is_alive():
            self.current_thread = None
        self.current_thread = threading.Thread(target=self._execute_after_delay, args=("on", delay))
        self.current_thread.start()
        return f"Relay scheduled to turn on in {delay} seconds."

    def turn_off(self, delay=None, auto=False):
        """
        Timed turn-off.
        delay: Time in seconds. If None, OFF_DELAY is used.
        auto: Flag indicating if the action is initiated from 'Auto' mode.
        """
        logging.info("turn_off called with delay=%s, auto=%s", delay, auto)
        if not auto and self.mode != "Hand":
            logging.warning("Manual control blocked: Not in Hand mode")
            return "Manual control is only allowed in Hand mode!"
        if not self.state:
            logging.info("Relay is already off")
            return "Relay is already off!"
        delay = delay if delay is not None else self.OFF_DELAY
        logging.info("Relay will turn off in %d seconds...", delay)
        if self.current_thread and self.current_thread.is_alive():
            self.current_thread = None
        self.current_thread = threading.Thread(target=self._execute_after_delay, args=("off", delay))
        self.current_thread.start()
        return f"Relay scheduled to turn off in {delay} seconds."

    def force_off(self):
        """Immediate turn-off (emergency)."""
        logging.info("Forcing relay off due to emergency")
        self.brand_alarm = True
        if self.current_thread and self.current_thread.is_alive():
            self.current_thread = None
        self._turn_off()
        return "Emergency: Relay turned off immediately!"

    def set_mode(self, mode):
        """Sets the operating mode ('Hand', 'Aus', 'Auto')."""
        logging.info("Setting mode to %s", mode)
        if mode not in ["Hand", "Aus", "Auto"]:
            raise ValueError("Invalid mode")
        self.mode = mode
        if mode == "Aus":
            if self.current_thread and self.current_thread.is_alive():
                self.current_thread = None
            self._turn_off()
        return self.mode

    def get_state(self):
        """
        Returns the current state of the relay and the current mode.
        state: True/False
        mode: "Hand", "Aus", "Auto"
        """
        return {"state": self.state, "mode": self.mode}

    def cleanup(self):
        """Closes the GPIO chip and releases resources."""
        logging.info("Cleaning up GPIO...")
        self.relay_line.release()
        self.led_line.release()
        self.chip.close()
        logging.info("GPIO cleaned up.")