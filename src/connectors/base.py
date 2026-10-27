
"""Shared connector contract. Connectors return source records and raw payloads."""
from abc import ABC, abstractmethod

class BaseConnector(ABC):
    name = "base"

    @abstractmethod
    def fetch(self):
        """Return (records: list[dict], raw_payload: object)."""
        raise NotImplementedError
