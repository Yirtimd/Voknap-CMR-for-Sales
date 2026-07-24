import argparse
import time

from app.core.database import SessionLocal
from app.modules.connectors.jobs import IntegrationJobService


def process_once() -> int:
    with SessionLocal() as db:
        return IntegrationJobService(db).process_available()


def main() -> None:
    parser = argparse.ArgumentParser(description="Process integration background jobs")
    parser.add_argument("--once", action="store_true", help="Process one batch and exit")
    parser.add_argument("--interval", type=float, default=2.0, help="Polling interval in seconds")
    args = parser.parse_args()
    while True:
        processed = process_once()
        if args.once:
            print(f"Processed integration jobs: {processed}")
            return
        if processed == 0:
            time.sleep(max(args.interval, 0.2))


if __name__ == "__main__":
    main()
