
"""Optional Streamlit dashboard. Reads SQLite; it does not collect web data."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
from src.storage import JobStore
from src.config import DB_PATH
from src.analytics import build_summary

st.set_page_config(page_title="Web Data Pipeline", layout="wide")
st.title("Intelligent Web Data Pipeline")
st.caption("Analytics over the latest stored job records. This page does not trigger scraping.")

if not DB_PATH.exists():
    st.warning("No database found yet. Run `python -m src.main demo` in a terminal first.")
    st.stop()

store = JobStore(DB_PATH)
try:
    jobs = store.fetch_all_jobs()
    runs = store.fetch_run_history(10)
finally:
    store.close()

summary = build_summary(jobs)
col1, col2, col3, col4 = st.columns(4)
col1.metric("Collected jobs", summary["total_jobs"])
col2.metric("Companies", summary["companies_count"])
col3.metric("Locations", summary["locations_count"])
col4.metric("Jobs with comparable salary", summary["jobs_with_salary"])

query = st.text_input("Search title, company, location, description, or skill")
location_options = sorted({job.get("location") or "Unknown" for job in jobs})
selected_locations = st.multiselect("Filter by location", location_options, default=location_options)

filtered = []
for job in jobs:
    haystack = " ".join([
        str(job.get("title") or ""), str(job.get("company") or ""),
        str(job.get("location") or ""), str(job.get("description") or ""),
        " ".join(job.get("skills", []))
    ]).lower()
    if query.lower() in haystack and (job.get("location") or "Unknown") in selected_locations:
        filtered.append(job)

st.subheader("Most listed skills")
skills = summary["top_skills"]
if skills:
    skill_chart_data = pd.DataFrame({
        "Skill": [item["name"] for item in skills],
        "Job listings": [item["count"] for item in skills]
    })
    st.bar_chart(skill_chart_data, x="Skill", y="Job listings")
else:
    st.info("No skills found yet.")

st.subheader("Collected jobs")
display_rows = []
for job in filtered:
    display_rows.append({
        "Title": job.get("title"), "Company": job.get("company"),
        "Location": job.get("location"), "Skills": ", ".join(job.get("skills", [])),
        "Salary min": job.get("salary_min"), "Salary max": job.get("salary_max"),
        "Currency": job.get("salary_currency"), "URL": job.get("job_url")
    })
st.dataframe(display_rows, use_container_width=True, hide_index=True)

st.download_button(
    "Download filtered jobs as CSV",
    data=("Title,Company,Location,Skills,URL\n" + "\n".join(
        '"' + str(row["Title"] or "").replace('"', '""') + '","' +
        str(row["Company"] or "").replace('"', '""') + '","' +
        str(row["Location"] or "").replace('"', '""') + '","' +
        str(row["Skills"] or "").replace('"', '""') + '","' +
        str(row["URL"] or "").replace('"', '""') + '"'
        for row in display_rows
    )).encode("utf-8"),
    file_name="filtered_jobs.csv",
    mime="text/csv"
)

st.subheader("Recent pipeline runs")
if runs:
    st.dataframe([{
        "Run": row["run_id"], "Started": row["started_at"], "Finished": row["finished_at"],
        "Status": row["status"], "Fetched": row["records_fetched"],
        "Inserted": row["jobs_inserted"], "Updated": row["jobs_updated"],
        "Errors": row["error_summary"]
    } for row in runs], use_container_width=True, hide_index=True)
