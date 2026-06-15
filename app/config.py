"""
Config module — loads .env from project root on first import.
Other modules can simply `from app.config import FRED_API_KEY` etc.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

FRED_API_KEY = os.environ.get("FRED_API_KEY", "")
EIA_API_KEY = os.environ.get("EIA_API_KEY", "")
DB_PATH = os.environ.get("ECO_DATA_DB", str(Path(__file__).resolve().parent.parent / "eco_data.duckdb"))
