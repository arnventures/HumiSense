import time
import logging
import threading
import lgpio
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RelayService:
    ON_DELAY = 1
    OFF_DELAY = 1
    RELAY_PIN = 22
    LED_PIN = 5

    def __init__(self):
        self.relay_pin = self.RELAY_PIN
        self.led_pin = self.LED_PIN
        self.state = False
        self.brand_alarm = False
        self.mode = "Auto"
        self.current_thread = None
        self.chip = None

        # List available GPIO devices for debugging
        gpio_devices = [f for f in os.listdir("/dev") if f.startswith("gpiochip")]
        logger.info(f"Available GPIO devices: {gpio_devices}")

        # Open the GPIO chip (chip 0 corresponds to /dev/gpiochip0)
        try:
            self.chip = lgpio.gpiochip_open(0)  # Open chip 0
            logger.info("Successfully opened GPIO chip 0")
        except Exception as e:
            logger.error(f"Failed to open GPIO chip: {str(e)}")
            self.chip = None

        if self.chip is None:
            logger.error("GPIO chip could not be opened. RelayService will run without GPIO access.")
        else:
            try:
                # Claim relay and LED pins as outputs with initial value 0 (LOW)
                lgpio.gpio_claim_output(self.chip, self.relay_pin, 0)
                lgpio.gpio_claim_output(self.chip, self.led_pin, 0)
                logger.info("GPIO pins configured successfully.")
            except Exception as e:
                logger.error(f"Failed to claim GPIO pins: {str(e)}")
                lgpio.gpiochip_close(self.chip)
                self.chip = None

    def _execute_after_delay(self, action, delay):
        """Executes the on/off action after a delay."""
        if self.chip is None:
            logger.warning("GPIO not available. Cannot execute action: %s", action)
            return
        logger.info("Starting delay of %d seconds for action: %s", delay, action)
        time.sleep(delay)
        logger.info("Delay finished, executing action: %s", action)
        if action == "on" and not self.brand_alarm:
            self._turn_on()
        elif action == "off":
            self._turn_off()

    def _turn_on(self):
        """Internal method to turn on immediately."""
        if self.chip is not None:
            logger.info("Turning relay ON at GPIO %d", self.relay_pin)
            lgpio.gpio_write(self.chip, self.relay_pin, 1)
            logger.info("Turning LED ON at GPIO %d", self.led_pin)
            lgpio.gpio_write(self.chip, self.led_pin, 1)
            self.state = True
            logger.info("Relay turned on, state: %s", self.state)
        else:
            logger.warning("GPIO not available. Cannot turn on relay.")

    def _turn_off(self):
        """Internal method to turn off immediately."""
        if self.chip is not None:
            logger.info("Turning relay OFF at GPIO %d", self.relay_pin)
            lgpio.gpio_write(self.chip, self.relay_pin, 0)
            logger.info("Turning LED OFF at GPIO %d", self.led_pin)
            lgpio.gpio_write(self.chip, self.led_pin, 0)
            self.state = False
            logger.info("Relay turned off, state: %s", self.state)
        else:
            logger.warning("GPIO not available. Cannot turn off relay.")

    def turn_on(self, delay=None, auto=False):
        """
        Timed turn-on.
        delay: Time in seconds. If None, ON_DELAY is used.
        auto: Flag indicating if the action is initiated from 'Auto' mode.
        """
        if self.chip is None:
            logger.warning("GPIO not available. Cannot turn on relay.")
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
        Timed turn-off.
        delay: Time in seconds. If None, OFF_DELAY is used.
        auto: Flag indicating if the action is initiated from 'Auto' mode.
        """
        if self.chip is None:
            logger.warning("GPIO not available. Cannot turn off relay.")
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
        """Immediate turn-off (emergency)."""
        if self.chip is None:
            logger.warning("GPIO not available. Cannot force off relay.")
            return "GPIO not available!"
        logger.info("Forcing relay off due to emergency")
        self.brand_alarm = True
        if self.current_thread and self.current_thread.is_alive():
            self.current_thread = None
        self._turn_off()
        return "Emergency: Relay turned off immediately!"

    def set_mode(self, mode):
        """Sets the operating mode ('Hand', 'Aus', 'Auto')."""
        if mode not in ["Hand", "Aus", "Auto"]:
            raise ValueError("Invalid mode")
        self.mode = mode
        logger.info(f"Mode set to {mode}.")
        if mode == "Aus" and self.chip is not None:
            if self.current_thread and self.current_thread.is_alive():
                self.current_thread = None
            self._turn_off()
        # Restore LED behavior: turn on LED in Hand mode
        if mode == "Hand" and self.chip is not None:
            logger.info("Turning on LED for Hand mode...")
            lgpio.gpio_write(self.chip, self.led_pin, 1)
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
        if self.chip is not None:
            logger.info("Releasing GPIO lines...")
            lgpio.gpiochip_close(self.chip)
            logger.info("GPIO lines released.")