
"""Offline connectors using bundled fixtures, so the project works without internet."""
import json
from pathlib import Path
from bs4 import BeautifulSoup
from .base import BaseConnector

PROJECT_ROOT = Path(__file__).resolve().parents[2]

class DemoJSONConnector(BaseConnector):
    name = "demo_json"

    def fetch(self):
        path = PROJECT_ROOT / "data" / "demo" / "api_jobs.json"
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        records = payload.get("jobs", [])
        if not isinstance(records, list):
            raise ValueError("Demo JSON field 'jobs' must be a list")
        return records, payload

class DemoHTMLConnector(BaseConnector):
    name = "demo_html"

    def fetch(self):
        path = PROJECT_ROOT / "data" / "demo" / "jobs_page.html"
        html = path.read_text(encoding="utf-8")
        soup = BeautifulSoup(html, "html.parser")
        records = []
        for item in soup.select(".job"):
            title_node = item.select_one(".title")
            company_node = item.select_one(".company")
            location_node = item.select_one(".location")
            description_node = item.select_one(".description")
            link_node = item.select_one("a")
            records.append({
                "id": item.get("data-job-id", ""),
                "title": title_node.get_text(" ", strip=True) if title_node else "",
                "company_name": company_node.get_text(" ", strip=True) if company_node else "",
                "candidate_required_location": location_node.get_text(" ", strip=True) if location_node else "",
                "description": description_node.get_text(" ", strip=True) if description_node else "",
                "url": link_node.get("href", "") if link_node else "",
                "publication_date": "",
                "salary": ""
            })
        return records, {"html_fixture": html, "records_extracted": len(records)}
