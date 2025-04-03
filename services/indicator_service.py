import logging
import gpiod
from gpiod.line import Direction, Value

class IndicatorService:
    # Define the GPIO pins
    RUN_LED_PIN = 18    #green LED “system running”
    FAULT_LED_PIN = 23  # red LED  “fault condition”

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        try:
            self.lines = gpiod.request_lines(
                "/dev/gpiochip0",
                consumer="indicator_service",
                config={
                    # The run LED is turned on immediately to indicate system power/running.
                    self.RUN_LED_PIN: gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.ACTIVE),
                    # The fault LED starts off (inactive).
                    self.FAULT_LED_PIN: gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.INACTIVE),
                },
            )
            self.logger.info("IndicatorService: Successfully requested GPIO lines on /dev/gpiochip0")
        except Exception as e:
            self.logger.error("IndicatorService: Failed to request GPIO lines: %s", str(e))
            self.lines = None

    def set_run_led(self, on: bool):
        """
        Sets the run LED (green) on or off.
        When on, it indicates that the system is powered and running.
        """
        if self.lines:
            value = Value.ACTIVE if on else Value.INACTIVE
            self.lines.set_value(self.RUN_LED_PIN, value)
            self.logger.info("Run LED set to %s", "ON" if on else "OFF")
        else:
            self.logger.error("IndicatorService: GPIO lines not available for run LED")

    def set_fault_led(self, on: bool):
        """
        Sets the fault LED (red) on or off.
        When on, it indicates a fault condition (e.g. no internet connection).
        """
        if self.lines:
            value = Value.ACTIVE if on else Value.INACTIVE
            self.lines.set_value(self.FAULT_LED_PIN, value)
            self.logger.info("Fault LED set to %s", "ON" if on else "OFF")
        else:
            self.logger.error("IndicatorService: GPIO lines not available for fault LED")

    def cleanup(self):
        if self.lines:
            self.lines.release()
            self.logger.info("IndicatorService: GPIO lines released")
