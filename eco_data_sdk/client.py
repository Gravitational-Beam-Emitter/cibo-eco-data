"""
Eco Data HTTP Client — thin wrapper around the REST API.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests


class EcoDataClient:
    """Synchronous HTTP client for the Eco Data API."""

    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()

    def _get(self, path: str, params: Optional[dict] = None) -> Any:
        resp = self._session.get(
            f"{self.base_url}{path}",
            params=params,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, params: Optional[dict] = None, json: Optional[dict] = None) -> Any:
        resp = self._session.post(
            f"{self.base_url}{path}",
            params=params,
            json=json,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    # ── Indicators ─────────────────────────────────────────

    def list_indicators(self, source: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all indicators. Filter by source (us, cn, global_, hk, jp, euro, uk, de, au, ca, ch, bond, futures, shipping, banks, alt, llm, defi, energy, ai, ai_co)."""
        params = {}
        if source:
            params["source"] = source
        return self._get("/api/v1/indicators", params)

    def get_indicator(self, indicator_id: int) -> Dict[str, Any]:
        """Get metadata for a single indicator."""
        return self._get(f"/api/v1/indicators/{indicator_id}")

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search indicators by keyword (name, description, tags, or source)."""
        return self._get("/api/v1/indicators/search", {"q": query})

    def list_tags(self) -> List[Dict[str, Any]]:
        """List all tags with indicator counts. Use to browse data by topic."""
        return self._get("/api/v1/tags")

    def query_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """List indicators matching a specific tag (e.g. '通胀', 'AI算力', '数据中心')."""
        return self._get("/api/v1/indicators", {"tag": tag})

    # ── Data ───────────────────────────────────────────────

    def query_data(
        self,
        indicator_id: int,
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: int = 1000,
    ) -> Dict[str, Any]:
        """Query time-series observations. Returns {indicator, count, data}."""
        params: Dict[str, Any] = {"limit": limit}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        return self._get(f"/api/v1/data/{indicator_id}", params)

    def latest(self, indicator_id: int) -> Dict[str, Any]:
        """Get the most recent observation."""
        return self._get(f"/api/v1/data/{indicator_id}/latest")

    # ── Actions ─────────────────────────────────────────────

    def fetch(self, source: Optional[str] = None) -> Dict[str, Any]:
        """Trigger a data refresh from upstream sources."""
        params = {}
        if source:
            params["source"] = source
        return self._post("/api/v1/fetch", params)

    def health(self) -> Dict[str, Any]:
        """Service health check."""
        return self._get("/api/v1/health")

    # ── Categories ─────────────────────────────────────────

    def list_categories(self) -> Dict[str, Any]:
        """List the three data categories with source counts."""
        return self._get("/api/v1/categories")

    # ── Risk Ratings ────────────────────────────────────────

    def list_risk_indicators(self, source: Optional[str] = None) -> List[Dict[str, Any]]:
        """List country risk indicators (AML ratings, sanctions, CPI)."""
        params = {}
        if source:
            params["source"] = source
        return self._get("/api/v1/risk/indicators", params)

    def get_risk_indicator(self, indicator_id: int) -> Dict[str, Any]:
        """Get metadata for a single risk indicator."""
        return self._get(f"/api/v1/risk/indicators/{indicator_id}")

    def query_risk_data(
        self,
        indicator_id: int,
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: int = 1000,
    ) -> Dict[str, Any]:
        """Query time-series data for a risk indicator."""
        params: Dict[str, Any] = {"limit": limit}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        return self._get(f"/api/v1/risk/data/{indicator_id}", params)

    def risk_latest(self, indicator_id: int) -> Dict[str, Any]:
        """Get the most recent observation for a risk indicator."""
        return self._get(f"/api/v1/risk/data/{indicator_id}/latest")

    def risk_fetch(self) -> Dict[str, Any]:
        """Refresh all country risk data sources."""
        return self._post("/api/v1/risk/fetch")

    # ── Name Screening ──────────────────────────────────────

    def screen_name(self, query: str, include_news: bool = False) -> Dict[str, Any]:
        """Comprehensive name screening — sanctions, PEP, negative news."""
        return self._post("/api/v1/name-screening/search", json={
            "query": query,
            "include_news": include_news,
        })

    def screen_name_batch(self, queries: List[str], include_news: bool = False) -> Dict[str, Any]:
        """Batch name screening — screen multiple names at once."""
        return self._post("/api/v1/name-screening/batch", json={
            "queries": queries,
            "include_news": include_news,
        })

    def name_screening_stats(self) -> Dict[str, Any]:
        """Get name screening database statistics."""
        return self._get("/api/v1/name-screening/stats")

    def close(self) -> None:
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
