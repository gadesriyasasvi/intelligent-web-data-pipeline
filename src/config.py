
"""Central paths and logging setup."""
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REPORT_DIR = ROOT / "output" / "reports"
LOG_DIR = ROOT / "logs"
DB_PATH = DATA_DIR / "pipeline.db"

def ensure_directories():
    for path in (RAW_DIR, PROCESSED_DIR, REPORT_DIR, LOG_DIR):
        path.mkdir(parents=True, exist_ok=True)

def configure_logging():
    ensure_directories()
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        file_handler = logging.FileHandler(LOG_DIR / "pipeline.log", encoding="utf-8")
        file_handler.setFormatter(formatter)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
