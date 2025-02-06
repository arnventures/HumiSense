import json
from datetime import datetime

class LogEntry:
    def __init__(self, category, data):
        self.category = category
        self.data = data
        self.timestamp = datetime.now().isoformat()  # ISO 8601 format

    def to_dict(self):
        """Convert the log entry to a dictionary."""
        return {
            "timestamp": self.timestamp,
            "category": self.category,
            "data": self.data,
        }

    def to_json(self):
        """Convert the log entry to a JSON string."""
        return json.dumps(self.to_dict())
