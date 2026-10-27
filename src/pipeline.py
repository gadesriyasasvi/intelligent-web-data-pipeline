
"""Coordinates connector execution, raw capture, transformation, storage, and reporting."""
import logging
import json
from datetime import datetime
from pathlib import Path
from .config import RAW_DIR, DB_PATH, ensure_directories
from .connectors.demo_connector import DemoJSONConnector, DemoHTMLConnector
from .connectors.remotive_api import RemotiveAPIConnector
from .connectors.html_connector import HTMLPageConnector
from .processing import prepare_records, deduplicate_records
from .storage import JobStore
from .reporting import export_csv, export_reports
from .utils import write_json

logger = logging.getLogger(__name__)

def make_connectors(mode="demo", limit=30):
    if mode == "demo":
        return [DemoJSONConnector(), DemoHTMLConnector()]
    if mode == "live":
        connectors = [RemotiveAPIConnector(limit=limit)]
        config_path = Path(__file__).resolve().parents[1] / "config" / "sources.json"
        with config_path.open("r", encoding="utf-8") as file:
            settings = json.load(file)
        html_settings = settings.get("html_example", {})
        if html_settings.get("enabled") and html_settings.get("url"):
            connectors.append(HTMLPageConnector(
                name="configured_html",
                url=html_settings["url"],
                selectors=html_settings.get("selectors", {})
            ))
        return connectors
    raise ValueError("mode must be 'demo' or 'live'")

def run_pipeline(mode="demo", limit=30, db_path=None):
    ensure_directories()
    connectors = make_connectors(mode, limit)
    store = JobStore(db_path or DB_PATH)
    run_id = store.start_run(len(connectors))
    metrics = {
        "sources_succeeded": 0, "records_fetched": 0, "records_valid": 0,
        "records_rejected": 0, "duplicates_found": 0, "jobs_inserted": 0, "jobs_updated": 0
    }
    all_cleaned = []
    errors = []
    try:
        for connector in connectors:
            try:
                records, payload = connector.fetch()
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                raw_path = RAW_DIR / f"run_{run_id}_{connector.name}_{stamp}.json"
                write_json(raw_path, payload)
                store.add_raw_record(run_id, connector.name, len(records), raw_path)
                cleaned, rejected = prepare_records(records, connector.name)
                metrics["sources_succeeded"] += 1
                metrics["records_fetched"] += len(records)
                metrics["records_valid"] += len(cleaned)
                metrics["records_rejected"] += len(rejected)
                all_cleaned.extend(cleaned)
                if rejected:
                    logger.warning("%s: rejected %d records", connector.name, len(rejected))
                logger.info("%s: fetched=%d valid=%d rejected=%d",
                            connector.name, len(records), len(cleaned), len(rejected))
                if rejected:
                    reject_path = RAW_DIR / f"run_{run_id}_{connector.name}_rejected.json"
                    write_json(reject_path, rejected)
            except Exception as error:
                errors.append(f"{connector.name}: {error}")
                logger.exception("Source %s failed", connector.name)
        unique_jobs, duplicate_count = deduplicate_records(all_cleaned)
        metrics["duplicates_found"] = duplicate_count
        inserted, updated = store.save_jobs(unique_jobs, run_id)
        metrics["jobs_inserted"] = inserted
        metrics["jobs_updated"] = updated
        status = "success" if not errors else ("partial" if metrics["sources_succeeded"] else "failed")
        store.finish_run(run_id, status, metrics, "; ".join(errors))
        jobs = store.fetch_all_jobs()
        export_csv(jobs)
        summary, report_path = export_reports(jobs)
        logger.info("Run %s completed: status=%s jobs=%d inserted=%d updated=%d",
                    run_id, status, len(jobs), inserted, updated)
        return {
            "run_id": run_id, "status": status, "metrics": metrics,
            "summary": summary, "report_path": str(report_path),
            "csv_path": str(Path(__file__).resolve().parents[1] / "data" / "processed" / "jobs.csv"),
            "errors": errors
        }
    except Exception as error:
        store.finish_run(run_id, "failed", metrics, str(error))
        raise
    finally:
        store.close()

def regenerate_reports(db_path=None):
    store = JobStore(db_path or DB_PATH)
    try:
        jobs = store.fetch_all_jobs()
        csv_path = export_csv(jobs)
        summary, report_path = export_reports(jobs)
        return {"jobs": len(jobs), "csv_path": str(csv_path), "report_path": str(report_path), "summary": summary}
    finally:
        store.close()
