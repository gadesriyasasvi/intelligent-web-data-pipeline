
"""Exports cleaned rows and summary reports without automatic EDA packages."""
import csv
import html
import json
from pathlib import Path
from .analytics import build_summary
from .utils import write_json
from .config import PROCESSED_DIR, REPORT_DIR

CSV_FIELDS = [
    "job_id", "title", "company", "location", "description", "job_url", "posted_at",
    "salary_min", "salary_max", "salary_currency", "source", "skills",
    "first_seen_at", "last_seen_at"
]

def export_csv(jobs, path=None):
    path = Path(path or (PROCESSED_DIR / "jobs.csv"))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for job in jobs:
            row = dict(job)
            row["skills"] = ", ".join(job.get("skills", [])) if isinstance(job.get("skills"), list) else job.get("skills", "")
            writer.writerow(row)
    return path

def export_reports(jobs):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    summary = build_summary(jobs)
    write_json(REPORT_DIR / "latest_summary.json", summary)
    rows = []
    for job in jobs:
        skill_values = job.get("skills", [])
        if isinstance(skill_values, list):
            skills_text = ", ".join(skill_values)
        else:
            skills_text = str(skill_values or "")
        rows.append(
            "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                html.escape(str(job.get("title") or "")),
                html.escape(str(job.get("company") or "")),
                html.escape(str(job.get("location") or "")),
                html.escape(skills_text),
                html.escape(str(job.get("salary_currency") or "Undisclosed"))
            )
        )
    skills_html = "".join(
        f"<li>{html.escape(item['name'])}: {item['count']}</li>"
        for item in summary["top_skills"]
    )
    report_html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Pipeline Report</title>
<style>body{{font-family:Arial,sans-serif;max-width:1100px;margin:36px auto;padding:0 18px;color:#222}}
table{{border-collapse:collapse;width:100%}}th,td{{padding:9px;border:1px solid #ddd;text-align:left}}
th{{background:#f1f3f5}}.metrics{{display:flex;gap:20px;flex-wrap:wrap}}.metric{{background:#f1f3f5;padding:14px;border-radius:8px}}
</style></head><body><h1>Intelligent Web Data Pipeline Report</h1>
<div class="metrics"><div class="metric">Jobs: <b>{summary['total_jobs']}</b></div>
<div class="metric">Companies: <b>{summary['companies_count']}</b></div>
<div class="metric">Locations: <b>{summary['locations_count']}</b></div></div>
<h2>Most frequently listed skills</h2><ul>{skills_html}</ul>
<h2>Collected jobs</h2><table><thead><tr><th>Title</th><th>Company</th><th>Location</th><th>Skills</th><th>Salary currency</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<p><small>Statistics describe collected records only. They do not necessarily represent the entire job market.</small></p>
</body></html>"""
    report_path = REPORT_DIR / "latest_report.html"
    report_path.write_text(report_html, encoding="utf-8")
    return summary, report_path
