
"""Live API connector with timeout and bounded retries."""
import time
import requests
from .base import BaseConnector

class RemotiveAPIConnector(BaseConnector):
    name = "remotive_api"

    def __init__(self, limit=30, timeout=15, retries=2):
        self.limit = max(1, min(int(limit), 100))
        self.timeout = timeout
        self.retries = max(0, retries)
        self.url = "https://remotive.com/api/remote-jobs"

    def fetch(self):
        params = {"limit": self.limit}
        headers = {"User-Agent": "IntelligentWebDataPipeline/1.0 (educational project)"}
        last_error = None
        for attempt in range(self.retries + 1):
            try:
                response = requests.get(
                    self.url, params=params, headers=headers, timeout=self.timeout
                )
                response.raise_for_status()
                payload = response.json()
                records = payload.get("jobs", [])
                if not isinstance(records, list):
                    raise ValueError("API response field 'jobs' is not a list")
                return records, payload
            except (requests.RequestException, ValueError) as error:
                last_error = error
                if attempt < self.retries:
                    time.sleep(2 ** attempt)
        raise RuntimeError(f"Could not fetch Remotive jobs after retries: {last_error}")
