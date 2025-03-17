# dummy_lgpio.py
import logging

def gpiochip_open(chip):
    logging.info(f"dummy_lgpio: gpiochip_open({chip})")
    return chip

def gpio_claim_output(chip, pin, initial_value):
    logging.info(f"dummy_lgpio: gpio_claim_output(chip={chip}, pin={pin}, initial_value={initial_value})")

def gpio_write(chip, pin, value):
    logging.info(f"dummy_lgpio: gpio_write(chip={chip}, pin={pin}, value={value})")

def gpiochip_close(chip):
    logging.info(f"dummy_lgpio: gpiochip_close({chip})")
