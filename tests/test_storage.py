
import tempfile
import unittest
from pathlib import Path
from src.storage import JobStore
from src.processing import prepare_records, deduplicate_records

class StorageTests(unittest.TestCase):
    def test_insert_then_update(self):
        with tempfile.TemporaryDirectory() as directory:
            store = JobStore(Path(directory) / "test.db")
            jobs, rejected = prepare_records([{
                "id": "1", "title": "Python Developer", "company_name": "Acme",
                "location": "Remote - India", "description": "Python SQL",
                "url": "https://example.invalid/job/1"
            }], "test")
            jobs, _ = deduplicate_records(jobs)
            first = store.save_jobs(jobs, 1)
            second = store.save_jobs(jobs, 2)
            self.assertEqual(first[0], 1)
            self.assertEqual(second[0], 0)
            self.assertEqual(second[1], 1)
            self.assertEqual(store.count_jobs(), 1)
            self.assertEqual(len(store.fetch_all_jobs()), 1)
            store.close()

if __name__ == "__main__":
    unittest.main()
