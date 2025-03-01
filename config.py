class Config:
    HUMIDITY_URL = "https://data.geo.admin.ch/ch.meteoschweiz.messwerte-luftfeuchtigkeit-10min/ch.meteoschweiz.messwerte-luftfeuchtigkeit-10min_de.json"
    TEMPERATURE_URL = "https://data.geo.admin.ch/ch.meteoschweiz.messwerte-lufttemperatur-10min/ch.meteoschweiz.messwerte-lufttemperatur-10min_de.json"
    CACHE_EXPIRATION_SECONDS = 600  # Cache validity (10 minutes)
    INITIAL_LOG_FILE = "log.json"    # Used as the default on first start (factory reset)