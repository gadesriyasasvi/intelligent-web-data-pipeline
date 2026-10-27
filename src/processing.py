
"""Transparent, rule-based record cleaning and transformation. No AI models."""
import re
from datetime import datetime

SKILL_DICTIONARY = [
    "python", "sql", "pandas", "numpy", "scikit-learn", "pytorch",
    "tensorflow", "docker", "kubernetes", "airflow", "apache spark",
    "javascript", "html", "css", "rest apis", "postgresql", "excel",
    "git", "aws", "azure", "machine learning", "data engineering"
]

def clean_text(value):
    if value is None:
        return ""
    text = str(value).replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def parse_date(value):
    value = clean_text(value)
    if not value:
        return ""
    # Accept common formats explicitly; leave unrecognized dates blank.
    formats = ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ",
               "%d-%m-%Y", "%d/%m/%Y")
    for date_format in formats:
        try:
            return datetime.strptime(value[:19], date_format).date().isoformat()
        except ValueError:
            continue
    return ""

def parse_salary(value):
    """Extract a conservative numeric range; preserve unknown salary as None."""
    text = clean_text(value).lower()
    if not text:
        return None, None, ""
    currency = "INR" if ("inr" in text or "₹" in text or "lpa" in text) else ""
    # A salary string like '₹ 10 LPA' is represented as 10,00,000 INR.
    lpa = re.search(r"(\d+(?:\.\d+)?)\s*lpa", text)
    if lpa:
        amount = int(float(lpa.group(1)) * 100000)
        return amount, amount, "INR"
    numbers = re.findall(r"\d[\d,]*(?:\.\d+)?", text)
    values = []
    for number in numbers[:2]:
        try:
            values.append(float(number.replace(",", "")))
        except ValueError:
            pass
    if not values:
        return None, None, currency
    # Avoid silently interpreting text with unsupported units as a salary.
    if len(values) >= 2:
        return int(min(values[0], values[1])), int(max(values[0], values[1])), currency
    return int(values[0]), int(values[0]), currency

def extract_skills(description):
    """Literal, case-insensitive dictionary matching; intentionally not NLP."""
    text = clean_text(description).lower()
    found = []
    for skill in SKILL_DICTIONARY:
        pattern = r"(?<![a-z0-9])" + re.escape(skill.lower()) + r"(?![a-z0-9])"
        if re.search(pattern, text):
            found.append(skill)
    return sorted(found)

def normalize_location(value):
    text = clean_text(value)
    lower = text.lower()
    if "bengaluru" in lower or "bangalore" in lower:
        return "Bengaluru, India"
    if "hyderabad" in lower:
        return "Hyderabad, India"
    if "pune" in lower:
        return "Pune, India"
    if "remote" in lower and "india" in lower:
        return "Remote, India"
    if lower == "india":
        return "India"
    return text

def normalize_job(record, source):
    """Map known API/HTML field names to a consistent schema."""
    title = clean_text(record.get("title") or record.get("job_title"))
    company = clean_text(record.get("company_name") or record.get("company"))
    location = normalize_location(
        record.get("candidate_required_location") or record.get("location")
    )
    description = clean_text(record.get("description") or record.get("summary"))
    url = clean_text(record.get("url") or record.get("job_url"))
    source_id = clean_text(record.get("id") or record.get("job_id") or record.get("source_job_id"))
    posted_at = parse_date(record.get("publication_date") or record.get("posted_at"))
    salary_min, salary_max, currency = parse_salary(record.get("salary") or record.get("salary_text"))
    # If API supplies explicit numeric salary values, use them when valid.
    explicit_min = record.get("salary_min")
    explicit_max = record.get("salary_max")
    if explicit_min not in (None, "") and explicit_max not in (None, ""):
        try:
            low, high = int(float(explicit_min)), int(float(explicit_max))
            if low >= 0 and high >= low:
                salary_min, salary_max = low, high
                currency = clean_text(record.get("currency")) or currency
        except (TypeError, ValueError):
            pass
    skills = extract_skills(description)
    normalized = {
        "source": clean_text(source),
        "source_job_id": source_id,
        "title": title,
        "company": company,
        "location": location,
        "description": description,
        "job_url": url,
        "posted_at": posted_at,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "salary_currency": currency,
        "skills": skills,
    }
    errors = validate_job(normalized)
    normalized["validation_errors"] = errors
    normalized["canonical_key"] = make_canonical_key(normalized)
    return normalized

def validate_job(job):
    errors = []
    for field in ("title", "company"):
        if not job.get(field):
            errors.append(f"missing_{field}")
    if job.get("salary_min") is not None and job.get("salary_max") is not None:
        if job["salary_min"] < 0 or job["salary_max"] < job["salary_min"]:
            errors.append("invalid_salary_range")
    return errors

def make_canonical_key(job):
    """Stable fallback identity across sources; URLs/IDs are still stored separately."""
    parts = [
        clean_text(job.get("title")).lower(),
        clean_text(job.get("company")).lower(),
        clean_text(job.get("location")).lower()
    ]
    return "|".join(parts)

def prepare_records(records, source):
    cleaned = []
    rejected = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            rejected.append({"index": index, "reason": "record_not_object"})
            continue
        job = normalize_job(record, source)
        if job["validation_errors"]:
            rejected.append({
                "index": index, "reason": ",".join(job["validation_errors"]),
                "record": record
            })
            continue
        cleaned.append(job)
    return cleaned, rejected

def deduplicate_records(records):
    """Keep the first occurrence of each canonical key; merge known skills and URL."""
    result = []
    positions = {}
    duplicate_count = 0
    for job in records:
        key = job["canonical_key"]
        if key not in positions:
            positions[key] = len(result)
            result.append(job.copy())
            continue
        duplicate_count += 1
        existing = result[positions[key]]
        merged_skills = set(existing.get("skills", []))
        for skill in job.get("skills", []):
            merged_skills.add(skill)
        existing["skills"] = sorted(merged_skills)
        if not existing.get("job_url") and job.get("job_url"):
            existing["job_url"] = job["job_url"]
        if not existing.get("description") and job.get("description"):
            existing["description"] = job["description"]
        # Keep provenance from all source copies.
        sources = set(existing.get("source", "").split(","))
        sources.update(job.get("source", "").split(","))
        existing["source"] = ",".join(sorted(s for s in sources if s))
    return result, duplicate_count
