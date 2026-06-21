"""
kr_stock configuration — Korean stock market (KOSPI/KOSDAQ/KONEX).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# DART API (optional — filings disabled without it)
DART_API_KEY = os.getenv("DART_API_KEY", "")

# LLM API keys (reused from cn_stock's .env entries)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")

# DuckDB
DB_PATH = str(Path(__file__).resolve().parent / "kr_stock.duckdb")
