"""Sync activities from Strava into the local SQLite database.

Usage:
    python3 src/sync.py            # incremental sync (since last watermark)
    python3 src/sync.py --limit 10 # only the 10 most recent activities
    python3 src/sync.py --full     # full historical backfill
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone

from src.config import DB_PATH
from src.db import connect
from src.ingest import insert_activity
from src.strava_client import RateLimitError, StravaClient


def _watermark(conn) -> int | None:
    row = conn.execute(
        "SELECT last_activity_at FROM sync_state WHERE source = 'strava'"
    ).fetchone()
    if not row or not row["last_activity_at"]:
        return None
    dt = datetime.fromisoformat(row["last_activity_at"].replace("Z", "+00:00"))
    return int(dt.timestamp())


def _set_watermark(conn, iso: str) -> None:
    conn.execute(
        """
        INSERT INTO sync_state (source, last_synced_utc, last_activity_at)
        VALUES ('strava', ?, ?)
        ON CONFLICT(source) DO UPDATE SET
            last_synced_utc = excluded.last_synced_utc,
            last_activity_at = MAX(sync_state.last_activity_at, excluded.last_activity_at)
        """,
        (datetime.now(timezone.utc).isoformat(), iso),
    )
    conn.commit()


def run(limit: int | None = None, full: bool = False) -> int:
    client = StravaClient()
    conn = connect(DB_PATH)

    after = None if (full or limit) else _watermark(conn)

    print("Fetching activity list...")
    activities = client.list_activities(after=after, per_page=30, max_pages=200)
    activities.sort(key=lambda a: a.get("start_date", ""))  # oldest first
    if limit:
        activities = activities[-limit:]
    print(f"  {len(activities)} activities to process")

    inserted = skipped = errored = 0
    for i, summary in enumerate(activities, 1):
        aid = summary.get("id")
        name = (summary.get("name") or "")[:40]
        date = (summary.get("start_date_local") or "")[:10]
        prefix = f"[{i}/{len(activities)}] {date} {name:40s}"
        try:
            # Cheap dedupe before spending API calls
            existing = conn.execute(
                "SELECT 1 FROM rides WHERE strava_id = ?", (aid,)
            ).fetchone()
            if existing:
                print(f"{prefix}  skip (already in db)")
                skipped += 1
                continue

            detail = client.activity_detail(aid)
            streams = {}
            try:
                streams = client.streams(aid)
            except Exception as e:
                print(f"{prefix}  streams unavailable ({e})")

            ride_id = insert_activity(conn, summary, detail, streams)
            sample_count = conn.execute(
                "SELECT COUNT(*) c FROM ride_samples WHERE ride_id = ?", (ride_id,)
            ).fetchone()["c"]
            print(f"{prefix}  inserted ride_id={ride_id} samples={sample_count}")
            inserted += 1

            _set_watermark(conn, summary.get("start_date") or "")

        except RateLimitError as e:
            print(f"\nRate limited. Sleeping {e.retry_after}s...")
            time.sleep(e.retry_after + 5)
        except Exception as e:
            print(f"{prefix}  ERROR: {e}")
            errored += 1

    print(f"\nDone. inserted={inserted} skipped={skipped} errored={errored}")
    conn.close()
    return 0 if errored == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="Only sync the N most recent activities")
    ap.add_argument("--full", action="store_true", help="Full backfill (ignore watermark)")
    args = ap.parse_args()
    return run(limit=args.limit, full=args.full)


if __name__ == "__main__":
    sys.exit(main())
