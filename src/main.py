
"""Command-line entry point."""
import argparse
import json
from .config import configure_logging
from .pipeline import run_pipeline, regenerate_reports
from .scheduler import run_schedule

def main():
    parser = argparse.ArgumentParser(description="Intelligent Web Data Pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo_parser = subparsers.add_parser("demo", help="Run offline JSON + HTML fixture pipeline")
    demo_parser.add_argument("--limit", type=int, default=30)

    live_parser = subparsers.add_parser("live", help="Fetch live jobs from the configured public API")
    live_parser.add_argument("--limit", type=int, default=30)

    subparsers.add_parser("report", help="Regenerate reports from the existing database")

    schedule_parser = subparsers.add_parser("schedule", help="Run pipeline repeatedly")
    schedule_parser.add_argument("--mode", choices=["demo", "live"], default="demo")
    schedule_parser.add_argument("--interval-minutes", type=int, default=1440)
    schedule_parser.add_argument("--limit", type=int, default=30)

    args = parser.parse_args()
    configure_logging()

    if args.command in ("demo", "live"):
        mode = args.command
        result = run_pipeline(mode=mode, limit=args.limit)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        return

    if args.command == "report":
        result = regenerate_reports()
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        return

    if args.command == "schedule":
        run_schedule(args.mode, args.interval_minutes, args.limit)

if __name__ == "__main__":
    main()
