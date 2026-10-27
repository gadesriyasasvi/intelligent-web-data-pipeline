
"""Basic analytics implemented with explicit loops and arithmetic."""
from collections import Counter

def build_summary(jobs):
    total = len(jobs)
    skill_counts = Counter()
    location_counts = Counter()
    company_counts = Counter()
    salary_values = []
    missing_salary = 0
    for job in jobs:
        for skill in job.get("skills", []):
            skill_counts[skill] += 1
        location = job.get("location") or "Unknown"
        company = job.get("company") or "Unknown"
        location_counts[location] += 1
        company_counts[company] += 1
        low, high = job.get("salary_min"), job.get("salary_max")
        if low is not None and high is not None and job.get("salary_currency"):
            salary_values.append((low + high) / 2)
        else:
            missing_salary += 1
    salary_mean = None
    if salary_values:
        total_salary = 0
        for value in salary_values:
            total_salary += value
        salary_mean = round(total_salary / len(salary_values), 2)
    return {
        "total_jobs": total,
        "companies_count": len(company_counts),
        "locations_count": len(location_counts),
        "jobs_with_salary": len(salary_values),
        "jobs_missing_comparable_salary": missing_salary,
        "mean_salary_midpoint": salary_mean,
        "top_skills": [{"name": name, "count": count} for name, count in skill_counts.most_common(15)],
        "jobs_by_location": [{"name": name, "count": count} for name, count in location_counts.most_common()],
        "top_companies": [{"name": name, "count": count} for name, count in company_counts.most_common(15)]
    }

def manual_mean(numbers):
    if not numbers:
        return None
    total = 0
    for number in numbers:
        total += number
    return total / len(numbers)
