# services/log_reader_service.py
import json, os
from dateutil import parser as dateparser
from file_read_backwards import FileReadBackwards

class LogReaderService:
    def __init__(self, parameter_service):
        self.parameter_service = parameter_service

    def get_filtered_logs(self, start_param=None, end_param=None, event_filter=None, limit=100):
        config = self.parameter_service.get_config()
        log_file = config.get("logging", {}).get("log_file", "log.json")

        start_time = None
        end_time = None
        try:
            if start_param:
                start_time = dateparser.isoparse(start_param).timestamp()
            if end_param:
                end_time = dateparser.isoparse(end_param).timestamp()
        except Exception as e:
            raise ValueError("Invalid date format") from e

        filtered_logs = []
        try:
            with FileReadBackwards(log_file, encoding="utf-8") as frb:
                for line in frb:
                    try:
                        entry = json.loads(line)
                    except Exception:
                        continue
                    ts = entry.get("timestamp")
                    if ts is None:
                        continue
                    if start_time and ts < start_time:
                        continue
                    if end_time and ts > end_time:
                        continue
                    if event_filter and entry.get("event") != event_filter:
                        continue
                    filtered_logs.append(entry)
                    if len(filtered_logs) >= limit:
                        break
        except Exception as e:
            raise Exception("Error reading log file") from e

        filtered_logs.reverse()
        return filtered_logs
