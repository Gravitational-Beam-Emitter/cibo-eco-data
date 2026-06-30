"""
Smart monthly backfill runner — only backfills months with 0 data.
Ultra-light: uses fetch_items=False (1 HTTP req/day, no per-filing requests).
"""

import subprocess
import sys
import time

# Months to backfill (skip 2025-01 which already has data)
MONTHS = [
    (2025, m) for m in range(2, 13)
] + [
    (2026, m) for m in range(1, 7)
]

def run():
    for year, month in MONTHS:
        print(f"\n=== {year}-{month:02d} ===")
        result = subprocess.run(
            [
                sys.executable, "-m", "us_corp_actions.backfill",
                f"{year}-{month:02d}-01",
                f"{year}-{month:02d}-31",  # Clamped in backfill.py
            ],
            capture_output=False,
        )
        if result.returncode != 0:
            print(f"WARNING: {year}-{month:02d} failed with code {result.returncode}")
        print(f"Pausing 30s...")
        time.sleep(30)

    # June 2026: partial month
    print("\n=== 2026-06 ===")
    subprocess.run(
        [sys.executable, "-m", "us_corp_actions.backfill", "2026-06-01", "2026-06-29"],
        capture_output=False,
    )

    print("\n=== DONE ===")

if __name__ == "__main__":
    run()
