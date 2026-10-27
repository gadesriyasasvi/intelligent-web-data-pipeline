
"""SQLite persistence. SQL statements are explicit and schema is visible."""
import json
import sqlite3
from pathlib import Path
from .utils import utc_now

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_key TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT,
    description TEXT,
    job_url TEXT,
    posted_at TEXT,
    salary_min INTEGER,
    salary_max INTEGER,
    salary_currency TEXT,
    source TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS job_skills (
    job_id INTEGER NOT NULL,
    skill TEXT NOT NULL,
    PRIMARY KEY (job_id, skill),
    FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS job_observations (
    observation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    observed_at TEXT NOT NULL,
    salary_min INTEGER,
    salary_max INTEGER,
    salary_currency TEXT,
    source TEXT,
    FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS raw_records (
    raw_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    source TEXT NOT NULL,
    record_count INTEGER NOT NULL,
    payload_path TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    sources_attempted INTEGER DEFAULT 0,
    sources_succeeded INTEGER DEFAULT 0,
    records_fetched INTEGER DEFAULT 0,
    records_valid INTEGER DEFAULT 0,
    records_rejected INTEGER DEFAULT 0,
    duplicates_found INTEGER DEFAULT 0,
    jobs_inserted INTEGER DEFAULT 0,
    jobs_updated INTEGER DEFAULT 0,
    error_summary TEXT
);
"""

class JobStore:
    def __init__(self, db_path):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(SCHEMA)
        self.connection.commit()

    def close(self):
        self.connection.close()

    def start_run(self, sources_attempted):
        cursor = self.connection.execute(
            "INSERT INTO pipeline_runs (started_at, status, sources_attempted) VALUES (?, ?, ?)",
            (utc_now(), "running", sources_attempted)
        )
        self.connection.commit()
        return cursor.lastrowid

    def add_raw_record(self, run_id, source, record_count, payload_path):
        self.connection.execute(
            "INSERT INTO raw_records (run_id, source, record_count, payload_path) VALUES (?, ?, ?, ?)",
            (run_id, source, record_count, str(payload_path))
        )
        self.connection.commit()

    def save_jobs(self, jobs, run_id):
        inserted = 0
        updated = 0
        observed_at = utc_now()
        try:
            with self.connection:
                for job in jobs:
                    existing = self.connection.execute(
                        "SELECT job_id FROM jobs WHERE canonical_key = ?",
                        (job["canonical_key"],)
                    ).fetchone()
                    if existing:
                        job_id = existing["job_id"]
                        self.connection.execute("""
                            UPDATE jobs SET title=?, company=?, location=?, description=?,
                                job_url=?, posted_at=?, salary_min=?, salary_max=?,
                                salary_currency=?, source=?, last_seen_at=?
                            WHERE job_id=?
                        """, (
                            job["title"], job["company"], job["location"], job["description"],
                            job["job_url"], job["posted_at"], job["salary_min"], job["salary_max"],
                            job["salary_currency"], job["source"], observed_at, job_id
                        ))
                        updated += 1
                    else:
                        cursor = self.connection.execute("""
                            INSERT INTO jobs (
                                canonical_key, title, company, location, description, job_url,
                                posted_at, salary_min, salary_max, salary_currency, source,
                                first_seen_at, last_seen_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            job["canonical_key"], job["title"], job["company"], job["location"],
                            job["description"], job["job_url"], job["posted_at"],
                            job["salary_min"], job["salary_max"], job["salary_currency"],
                            job["source"], observed_at, observed_at
                        ))
                        job_id = cursor.lastrowid
                        inserted += 1
                    self.connection.execute("DELETE FROM job_skills WHERE job_id = ?", (job_id,))
                    for skill in job.get("skills", []):
                        self.connection.execute(
                            "INSERT OR IGNORE INTO job_skills (job_id, skill) VALUES (?, ?)",
                            (job_id, skill)
                        )
                    self.connection.execute("""
                        INSERT INTO job_observations
                        (job_id, observed_at, salary_min, salary_max, salary_currency, source)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        job_id, observed_at, job["salary_min"], job["salary_max"],
                        job["salary_currency"], job["source"]
                    ))
            return inserted, updated
        except sqlite3.Error:
            raise

    def finish_run(self, run_id, status, metrics, error_summary=""):
        with self.connection:
            self.connection.execute("""
                UPDATE pipeline_runs SET finished_at=?, status=?, sources_succeeded=?,
                    records_fetched=?, records_valid=?, records_rejected=?, duplicates_found=?,
                    jobs_inserted=?, jobs_updated=?, error_summary=?
                WHERE run_id=?
            """, (
                utc_now(), status, metrics.get("sources_succeeded", 0),
                metrics.get("records_fetched", 0), metrics.get("records_valid", 0),
                metrics.get("records_rejected", 0), metrics.get("duplicates_found", 0),
                metrics.get("jobs_inserted", 0), metrics.get("jobs_updated", 0),
                error_summary, run_id
            ))

    def fetch_all_jobs(self):
        rows = self.connection.execute("""
            SELECT job_id, canonical_key, title, company, location, description, job_url,
                   posted_at, salary_min, salary_max, salary_currency, source,
                   first_seen_at, last_seen_at
            FROM jobs ORDER BY last_seen_at DESC, title
        """).fetchall()
        jobs = []
        for row in rows:
            item = dict(row)
            skill_rows = self.connection.execute(
                "SELECT skill FROM job_skills WHERE job_id=? ORDER BY skill",
                (item["job_id"],)
            ).fetchall()
            item["skills"] = [skill["skill"] for skill in skill_rows]
            jobs.append(item)
        return jobs

    def fetch_run_history(self, limit=20):
        rows = self.connection.execute(
            "SELECT * FROM pipeline_runs ORDER BY run_id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]

    def count_jobs(self):
        row = self.connection.execute("SELECT COUNT(*) AS count FROM jobs").fetchone()
        return row["count"]
