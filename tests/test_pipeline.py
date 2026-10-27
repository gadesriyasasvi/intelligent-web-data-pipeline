
import tempfile
import unittest
from pathlib import Path
from src.pipeline import run_pipeline

class PipelineTests(unittest.TestCase):
    def test_demo_pipeline_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "test.db"
            result = run_pipeline("demo", db_path=db)
            self.assertIn(result["status"], ("success", "partial"))
            self.assertGreaterEqual(result["summary"]["total_jobs"], 1)
            self.assertTrue(Path(result["report_path"]).exists())

if __name__ == "__main__":
    unittest.main()
