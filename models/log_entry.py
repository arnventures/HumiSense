# models/station.py
class Station:
    def __init__(self, station_id, name, humidity, temperature, coordinates):
        self.station_id = station_id
        self.name = name
        self.humidity = humidity
        self.temperature = temperature
        self.coordinates = coordinates
