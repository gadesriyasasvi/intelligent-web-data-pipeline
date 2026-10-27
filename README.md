
# Intelligent Web Data Pipeline

A standalone, rule-based web data pipeline. It collects records from API-like JSON and HTML sources, preserves raw inputs, validates and standardizes records, deduplicates jobs, stores records in SQLite, creates CSV/JSON/HTML reports, and offers an optional dashboard and scheduler.

**No AI models, LLM APIs, embeddings, or AI services are used.** The important processing logic (cleaning, validation, deduplication, skill matching, and basic statistics) is implemented explicitly in Python. Libraries are used only for HTTP transport, HTML parsing, dashboard rendering, and test execution.

## Requirements

- Python 3.10+
- Internet access only for optional live collection
- Windows, macOS, or Linux

## Quick start (works offline)

Open a terminal in this project folder.

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m src.main demo
```

If PowerShell blocks activation, run the commands without activation using `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` and `.\.venv\Scripts\python.exe -m src.main demo`.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m src.main demo
```

The demo uses bundled JSON and HTML fixtures, so it does not depend on a website being available.

## Output files

After a successful run, inspect:

- `data/pipeline.db` — SQLite database
- `data/raw/` — timestamped copies of source payloads
- `data/processed/jobs.csv` — cleaned job records
- `output/reports/latest_summary.json` — machine-readable summary
- `output/reports/latest_report.html` — readable HTML report
- `logs/pipeline.log` — execution log

Run `python -m src.main report` to regenerate exports from the database without fetching new data.

## Optional live collection

The live connector uses the Remotive public jobs API. Network availability, API policies, returned fields, and access conditions can change; a live run can fail without affecting your stored data. Review the provider's current terms before use.

```bash
python -m src.main live --limit 30
```

The API connector uses timeouts and bounded retries. No API key is needed for this example. Live collection is separate from the offline demo.

To enable a second live HTML source, edit `config/sources.json`: set `html_example.enabled` to `true`, enter a permitted page URL, and update the CSS selectors to match that page. The live pipeline will then run the API connector and configured HTML connector independently.

### HTML connector

`src/connectors/html_connector.py` contains a configurable CSS-selector-based HTML connector. The included demo exercises it using a local HTML fixture. To scrape a live page, configure its URL and selectors in `config/sources.json`, and ensure the site permits your intended automated access. Do not bypass logins, CAPTCHAs, access controls, or rate limits.

## Dashboard

After running the demo once:

```bash
streamlit run src/dashboard.py
```

The dashboard reads the SQLite database and displays counts, skill frequencies, locations, and a job table. It does not scrape sites when the page opens.

## Scheduled execution

Run the pipeline every 24 hours (the scheduler runs until stopped with Ctrl+C):

```bash
python -m src.main schedule --mode demo --interval-minutes 1440
```

For live collection:

```bash
python -m src.main schedule --mode live --interval-minutes 1440
```

This is intentionally a basic in-process scheduler, not a distributed workflow orchestrator. The process must remain running. For a dependable daily production schedule, use your operating system's scheduler after you understand this implementation.

## Tests

```bash
python -m unittest discover -s tests -v
```

Tests use local fixtures and temporary databases; they do not require internet access.

## Project structure

```text
intelligent-web-data-pipeline/
├── config/
│   └── sources.json
├── data/
│   ├── demo/
│   │   ├── api_jobs.json
│   │   └── jobs_page.html
│   ├── raw/
│   └── processed/
├── logs/
├── output/reports/
├── src/
│   ├── connectors/
│   │   ├── base.py
│   │   ├── demo_connector.py
│   │   ├── html_connector.py
│   │   └── remotive_api.py
│   ├── analytics.py
│   ├── config.py
│   ├── dashboard.py
│   ├── main.py
│   ├── pipeline.py
│   ├── processing.py
│   ├── reporting.py
│   ├── scheduler.py
│   ├── storage.py
│   └── utils.py
└── tests/
    ├── test_pipeline.py
    ├── test_processing.py
    └── test_storage.py
```

## Data flow

1. Read data from a JSON fixture/API or a permitted HTML page.
2. Save the original payload under `data/raw/`.
3. Convert each source record to a common job schema.
4. Validate and clean values using explicit Python logic.
5. Extract skills with a small, editable dictionary (not an ML model).
6. Deduplicate using normalized title/company/location keys and source IDs.
7. Upsert jobs into SQLite and record pipeline-run metadata.
8. Calculate summary statistics and export CSV, JSON, and HTML reports.
9. Optionally view results in Streamlit or repeat the run on a schedule.

## Notes and limitations

- This is a learning project, not a complete commercial job-market data product.
- Salary fields can be missing or expressed in incompatible units. The pipeline does not invent missing values.
- The built-in skill matcher uses literal dictionary matching. It is transparent but cannot understand synonyms or context as a language model would.
- The pipeline records when a listing was observed. A listing missing from one API response is **not** automatically marked closed.
- Raw data is saved for traceability. Review provider terms before storing or redistributing third-party data.
