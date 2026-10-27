
"""Configurable CSS-selector HTML connector for pages you are permitted to access."""
import time
import requests
from bs4 import BeautifulSoup
from .base import BaseConnector

class HTMLPageConnector(BaseConnector):
    def __init__(self, name, url, selectors, timeout=15, retries=1):
        self.name = name
        self.url = url
        self.selectors = selectors
        self.timeout = timeout
        self.retries = max(0, retries)

    def fetch(self):
        if not self.url:
            raise ValueError("HTML connector URL is empty")
        last_error = None
        for attempt in range(self.retries + 1):
            try:
                response = requests.get(
                    self.url, timeout=self.timeout,
                    headers={"User-Agent": "IntelligentWebDataPipeline/1.0 (educational project)"}
                )
                response.raise_for_status()
                html = response.text
                return self.parse_html(html), {"url": self.url, "html": html}
            except requests.RequestException as error:
                last_error = error
                if attempt < self.retries:
                    time.sleep(2 ** attempt)
        raise RuntimeError(f"HTML fetch failed: {last_error}")

    def parse_html(self, html):
        soup = BeautifulSoup(html, "html.parser")
        records = []
        selectors = self.selectors
        for item in soup.select(selectors.get("container", "")):
            record = {}
            field_selectors = {
                "title": "title", "company_name": "company",
                "candidate_required_location": "location",
                "description": "description", "url": "url"
            }
            for output_key, selector_key in field_selectors.items():
                selector = selectors.get(selector_key, "")
                node = item.select_one(selector) if selector else None
                if output_key == "url":
                    record[output_key] = node.get("href", "") if node else ""
                else:
                    record[output_key] = node.get_text(" ", strip=True) if node else ""
            id_attribute = selectors.get("job_id_attribute", "data-job-id")
            record["id"] = item.get(id_attribute, "")
            record["publication_date"] = ""
            record["salary"] = ""
            records.append(record)
        return records
