
import unittest
from src.processing import clean_text, parse_salary, extract_skills, prepare_records, deduplicate_records

class ProcessingTests(unittest.TestCase):
    def test_clean_text(self):
        self.assertEqual(clean_text("  Python   SQL "), "Python SQL")

    def test_parse_lpa(self):
        low, high, currency = parse_salary("₹ 10 LPA")
        self.assertEqual((low, high, currency), (1000000, 1000000, "INR"))

    def test_missing_salary(self):
        self.assertEqual(parse_salary(""), (None, None, ""))

    def test_skill_extraction(self):
        self.assertEqual(extract_skills("Use Python and SQL daily."), ["python", "sql"])

    def test_prepare_and_deduplicate(self):
        records = [
            {"id": "1", "title": "Data Engineer", "company_name": "Acme",
             "candidate_required_location": "Bengaluru", "description": "Python SQL"},
            {"id": "2", "title": " Data Engineer ", "company_name": "Acme",
             "candidate_required_location": "Bangalore", "description": "Python Docker"}
        ]
        cleaned, rejected = prepare_records(records, "test")
        unique, duplicates = deduplicate_records(cleaned)
        self.assertEqual(len(rejected), 0)
        self.assertEqual(len(unique), 1)
        self.assertEqual(duplicates, 1)
        self.assertIn("docker", unique[0]["skills"])

if __name__ == "__main__":
    unittest.main()
