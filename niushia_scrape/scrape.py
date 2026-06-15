#!/usr/bin/env python3
"""
Niushia.com daily scraper — fetches review data, archive dates, and news.

Usage:
    python3 scrape.py              # fetch latest trading day
    python3 scrape.py --all        # fetch all available dates
    python3 scrape.py --date 20260612  # fetch specific date
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

BASE = "https://www.niushia.com"
DATA_DIR = Path(__file__).resolve().parent / "data"
FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"


def fetch(path: str) -> dict | list:
    url = f"{BASE}{path}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def download_file(path: str, dest: Path) -> int:
    url = f"{BASE}{path}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    return len(resp.content)


def scrape_date(date: str) -> Path:
    """Download review data for one trading day."""
    dest = DATA_DIR / f"review_{date}.json"
    size = download_file(f"/api/review?date={date}", dest)
    print(f"  [{date}] {size:>6} bytes → {dest.name}")
    return dest


def scrape_all() -> None:
    """Download all available data."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    FRONTEND_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Frontend
    print("=== Frontend ===")
    size = download_file("/", FRONTEND_DIR / "index.html")
    print(f"  index.html: {size} bytes")

    # 2. Archive dates
    print("\n=== Archive dates ===")
    archive = fetch("/api/archive_dates")
    download_file("/api/archive_dates", DATA_DIR / "archive_dates.json")
    print(f"  Review dates: {archive.get('review', [])}")
    print(f"  Longhu dates: {archive.get('longhu', [])}")

    # 3. Review data
    print("\n=== Review data ===")
    for date in archive.get("review", []):
        scrape_date(date)

    # 4. News
    print("\n=== News ===")
    size = download_file("/api/news", DATA_DIR / "news.json")
    print(f"  news.json: {size} bytes")

    # Summary
    files = sorted(DATA_DIR.glob("*.json"))
    print(f"\nTotal: {len(files)} files in {DATA_DIR}")


def scrape_latest() -> None:
    """Fetch only the latest trading day."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    archive = fetch("/api/archive_dates")
    dates = archive.get("review", [])
    if not dates:
        print("No data available")
        return
    latest = max(dates)
    print(f"Latest: {latest}")
    scrape_date(latest)


if __name__ == "__main__":
    if "--all" in sys.argv:
        scrape_all()
    elif "--date" in sys.argv:
        idx = sys.argv.index("--date")
        date = sys.argv[idx + 1]
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        scrape_date(date)
    else:
        scrape_latest()
