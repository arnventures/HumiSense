class Station:
    def __init__(self, station_id, name, humidity, temperature, coordinates):
        self.station_id = station_id
        self.name = name
        self.humidity = humidity
        self.temperature = temperature
        self.coordinates = coordinates

    def to_dict(self):
        """Convert the Station object to a dictionary for JSON responses."""
        return {
            "id": self.station_id,
            "name": self.name,
            "humidity": self.humidity,
            "temperature": self.temperature,
            "coordinates": self.coordinates,
        }
