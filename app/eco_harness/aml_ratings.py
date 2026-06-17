"""
AML/CFT Country Risk Ratings Harness — three data sources.

Sources:
  FATF    — grey list / black list (Wikipedia)
  INCSR   — US State Dept "Major Money Laundering Countries" (state.gov)
  Basel   — Basel AML Index composite + domain scores (Nuxt SSR payload)

Each method returns pd.DataFrame with columns: date, value, notes
"""

from __future__ import annotations

import json
import re
from datetime import date
from typing import Optional

import pandas as pd
import requests


class AMLRatingsHarness:
    """Anti-money laundering country risk ratings from FATF, INCSR, and Basel."""

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36 "
                "EcoData/1.0"
            ),
        })

    # ── FATF ──────────────────────────────────────────────────

    def _fetch_fatf_table(self, list_type: str) -> pd.DataFrame:
        """
        Parse FATF grey/black list from Wikipedia.
        Both lists use the same HTML structure: heading > paragraph with date > <ol> with countries.
        list_type: 'grey' or 'black'
        """
        url = "https://en.wikipedia.org/wiki/Financial_Action_Task_Force_blacklist"
        resp = self._session.get(url, timeout=15)
        resp.raise_for_status()
        html = resp.text
        today = str(date.today())

        heading_id = "Current_FATF_grey_list" if list_type == "grey" else "Current_FATF_blacklist"
        label_cn = "灰名单" if list_type == "grey" else "黑名单(Call for Action)"
        extra_note = "" if list_type == "grey" else "·需采取反制措施"

        # Find heading
        heading_match = re.search(
            f'<h3[^>]*id="{heading_id}"[^>]*>.*?</h3>',
            html
        )
        if not heading_match:
            return pd.DataFrame()

        after_heading = html[heading_match.end():]

        # Find the first <ol> after heading
        ol_match = re.search(r'<ol>(.*?)</ol>', after_heading[:20000], re.DOTALL)
        if not ol_match:
            return pd.DataFrame()

        ol_html = ol_match.group(1)
        countries = re.findall(r'<li[^>]*>.*?<a[^>]*title="([^"]*)"[^>]*>', ol_html, re.DOTALL)

        # Extract date from paragraph: "As of 13 February 2026, the following ..."
        date_match = re.search(
            r'As of (\d{1,2}\s+\w+\s+\d{4})',
            after_heading[:5000]
        )
        list_date = today
        if date_match:
            try:
                list_date = pd.to_datetime(date_match.group(1), dayfirst=False).strftime("%Y-%m-%d")
            except Exception:
                pass

        records = []
        for c in countries:
            c = c.strip()
            if c and c not in ("Flag", "Wikipedia", "Edit"):
                records.append({
                    "country": c,
                    "date": list_date,
                    "value": 1,
                    "notes": f"FATF{label_cn}·列入日期{list_date}·{c}{extra_note}",
                    "list": list_type,
                })
        return pd.DataFrame(records)

    def fatf_grey_list(self) -> pd.DataFrame:
        """FATF grey list (Jurisdictions under Increased Monitoring)."""
        df = self._fetch_fatf_table("grey")
        if df.empty:
            return df
        df["value"] = 1
        return df[["date", "value", "notes", "country", "list"]]

    def fatf_black_list(self) -> pd.DataFrame:
        """FATF black list (High-Risk Jurisdictions)."""
        df = self._fetch_fatf_table("black")
        if df.empty:
            return df
        df["value"] = 1
        return df[["date", "value", "notes", "country", "list"]]

    def fatf_grey_list_count(self) -> pd.DataFrame:
        """Count of countries on FATF grey list over time."""
        df = self._fetch_fatf_table("grey")
        if df.empty:
            return df
        today = str(date.today())
        return pd.DataFrame([{
            "date": today,
            "value": len(df),
            "notes": f"FATF灰名单·{len(df)}国·" + "、".join(df["country"].head(5).tolist()) + ("等" if len(df) > 5 else ""),
        }])

    def fatf_black_list_count(self) -> pd.DataFrame:
        """Count of countries on FATF black list over time."""
        df = self._fetch_fatf_table("black")
        if df.empty:
            return df
        today = str(date.today())
        return pd.DataFrame([{
            "date": today,
            "value": len(df),
            "notes": f"FATF黑名单·{len(df)}国·" + "、".join(df["country"].tolist()),
        }])

    # ── INCSR ─────────────────────────────────────────────────

    def incsr_major_ml_countries(self) -> pd.DataFrame:
        """
        US State Department INCSR Vol.II — Major Money Laundering Countries.
        Downloads the official PDF from state.gov and parses the 4-column bullet list
        using pdfplumber word-level extraction with column-aware grouping.
        """
        import io
        from collections import defaultdict

        try:
            import pdfplumber
        except ImportError:
            return pd.DataFrame()

        # First get the landing page to find the Volume II PDF link
        landing_url = "https://www.state.gov/2025-international-narcotics-control-strategy-report"
        pdf_url = None
        try:
            resp = self._session.get(landing_url, timeout=15)
            resp.raise_for_status()
            m = re.search(
                r'href="([^"]*volume-?2[^"]*\.pdf)"',
                resp.text, re.IGNORECASE
            )
            if m:
                pdf_url = m.group(1)
                if pdf_url.startswith("/"):
                    pdf_url = "https://www.state.gov" + pdf_url
        except Exception:
            pass

        if not pdf_url:
            pdf_url = (
                "https://www.state.gov/wp-content/uploads/2025/03/"
                "2025-International-Narcotics-Control-Strategy-Volume-2-Accessible.pdf"
            )

        try:
            resp = self._session.get(pdf_url, timeout=30)
            resp.raise_for_status()
        except Exception:
            return pd.DataFrame()

        try:
            pdf = pdfplumber.open(io.BytesIO(resp.content))

            # Collect all words from pages 14-15 (0-indexed 13-14)
            all_words = []
            for i in [13, 14]:
                page = pdf.pages[i]
                words = page.extract_words()
                all_words.extend(words)

            # Find the section start: "Major Money Laundering Jurisdictions in 2024:"
            start_idx = None
            for i, w in enumerate(all_words):
                if w["text"] == "Major":
                    snippet = " ".join(x["text"] for x in all_words[i:i + 6])
                    if "Major Money Laundering Jurisdictions" in snippet:
                        start_idx = i + 5  # skip past "2024:"
                        break

            if start_idx is None:
                return pd.DataFrame()

            # Collect words from the bullet list area
            bullet_words = all_words[start_idx:]

            # 4-column layout boundaries based on x0 word positions
            col_ranges = [(0, 170), (170, 300), (300, 430), (430, 600)]

            # Group words by column
            cols: dict[int, list] = defaultdict(list)
            for w in bullet_words:
                x0 = w["x0"]
                for ci, (lo, hi) in enumerate(col_ranges):
                    if lo <= x0 < hi:
                        cols[ci].append(w)
                        break

            # Within each column, group words into rows (~25pt spacing)
            countries_raw = []
            for ci in range(4):
                col_words = sorted(cols[ci], key=lambda w: w["top"])
                rows: dict[float, list] = defaultdict(list)
                for w in col_words:
                    if w["text"] == "\u2022" or w["text"] == "•":
                        continue
                    # Find or create row group (< 12pt difference = same row)
                    placed = False
                    for rtop in rows:
                        if abs(w["top"] - rtop) < 12:
                            rows[rtop].append(w)
                            placed = True
                            break
                    if not placed:
                        rows[w["top"]].append(w)

                # Extract country name per row
                for rtop in sorted(rows.keys()):
                    words_in_row = sorted(rows[rtop], key=lambda w: w["x0"])
                    name = " ".join(w["text"] for w in words_in_row).strip()
                    if name:
                        countries_raw.append(name)

            # Post-process: filter non-countries, merge broken names
            today = str(date.today())
            records = []
            skip = {
                "the", "and", "for", "with", "this", "that", "each", "all", "both",
                "volume", "report", "state", "department", "international",
                "narcotics", "control", "strategy", "major", "money",
                "laundering", "countries", "primary", "concern", "section",
                "chapter", "appendix", "table", "figure", "note", "source",
                "introduction", "overview", "summary", "conclusion",
                "legislative", "basis", "methodology", "page", "overview",
            }
            # Tokens that indicate a continuation from the previous line
            continuation_tokens = {"and", "the", "Islands", "Republic", "Bissau",
                                   "Barbuda", "Verde", "Nevis", "Tobago", "States",
                                   "Kingdom", "Emirates", "Arab", "Kong", "Salvador",
                                   "Rico", "Maarten", "Grenadines", "Lucia", "Kitts",
                                   "Vincent"}

            i = 0
            while i < len(countries_raw):
                name = countries_raw[i].strip().rstrip(".").rstrip(",")
                # Fix hyphen breaks: "Guinea-" → next line "Bissau" → "Guinea-Bissau"
                if name.endswith("-"):
                    if i + 1 < len(countries_raw):
                        next_name = countries_raw[i + 1].strip()
                        name = name.rstrip("-") + "-" + next_name
                        i += 1

                # Merge continuation lines — may span 2+ rows
                # e.g., "Antigua and" + "Barbuda" or "Saint Vincent" + "and the" + "Grenadines"
                while i + 1 < len(countries_raw):
                    next_name = countries_raw[i + 1].strip().rstrip(".")
                    next_first = next_name.split()[0] if next_name.split() else ""
                    if next_first in continuation_tokens:
                        name = name + " " + next_name
                        i += 1
                    else:
                        break

                # Skip non-country headers/footers
                first_word = name.split()[0].lower() if name.split() else ""
                if (first_word in skip
                        or name.lower() in skip
                        or re.match(r'^\d{4}\s*:?\s*$', name)
                        or re.match(r'^\d{4}\s+INCSR', name)
                        or re.match(r'^\d+\s*\|\s*', name)
                        or re.match(r'^Page\s+\d+', name)
                        or "Volume" in name
                        or "Page " in name
                        or "for the INCSR" in name
                        or "Legislative Basis" in name
                        or len(name.split()) > 8):
                    i += 1
                    continue

                if len(name) < 4:
                    i += 1
                    continue

                records.append({
                    "date": today,
                    "value": 1,
                    "notes": f"2025 INCSR Vol.II·列为洗钱主要关注国·{name}",
                    "country": name,
                })
                i += 1

            return pd.DataFrame(records)
        except Exception:
            return pd.DataFrame()

    def incsr_listed_count(self) -> pd.DataFrame:
        """Count of countries on INCSR Major Money Laundering list."""
        df = self.incsr_major_ml_countries()
        today = str(date.today())
        if df.empty:
            return pd.DataFrame([{
                "date": today,
                "value": 0,
                "notes": "INCSR数据暂时不可用",
            }])
        return pd.DataFrame([{
            "date": today,
            "value": len(df),
            "notes": f"INCSR主要洗钱关注国·{len(df)}国·" + "、".join(df["country"].head(10).tolist()) + ("等" if len(df) > 10 else ""),
        }])

    # ── Basel AML Index ──────────────────────────────────────

    def basel_country_scores(self) -> pd.DataFrame:
        """
        Basel AML Index — extract country scores from Nuxt SSR payload.
        Parses the embedded JSON from the ranking page (no auth required).
        Returns DataFrame with country, iso2, iso3, aml_score, rank, region, income.
        """
        url = "https://index.baselgovernance.org/ranking"
        resp = self._session.get(url, timeout=20)
        resp.raise_for_status()
        html = resp.text

        # Extract Nuxt SSR JSON payload
        m = re.search(
            r'<script[^>]*type="application/json"[^>]*>(.*?)</script>',
            html, re.DOTALL
        )
        if not m:
            return pd.DataFrame()

        payload = json.loads(m.group(1))

        # Resolve payload references: integer values in dicts are array indices
        resolved = {}

        def resolve(idx: int):
            if idx in resolved:
                return resolved[idx]
            if idx < 0 or idx >= len(payload):
                return None
            val = payload[idx]
            if isinstance(val, list) and len(val) == 2 and isinstance(val[0], str) \
               and val[0] in ("ShallowReactive", "ShallowRef", "ShallowReadonly"):
                result = resolve(val[1])
                resolved[idx] = result
                return result
            if isinstance(val, dict):
                result = {}
                for k, v in val.items():
                    if isinstance(v, int) and k != "rank" and k != "id":
                        result[k] = resolve(v)
                    else:
                        result[k] = v
                resolved[idx] = result
                return result
            resolved[idx] = val
            return val

        # Find scores array
        scores_indices = None
        for v in payload:
            if isinstance(v, dict) and "scores" in v and isinstance(v.get("scores"), int):
                scores_indices = resolve(v["scores"])
                break

        if not scores_indices or not isinstance(scores_indices, list):
            return pd.DataFrame()

        records = []
        for idx in scores_indices:
            score = resolve(idx)
            if not isinstance(score, dict):
                continue
            country = score.get("country", "")
            if not country:
                continue
            records.append({
                "country": str(country),
                "iso2": str(score.get("iso2", "")),
                "iso3": str(score.get("iso3", "")),
                "aml_score": float(score.get("aml", 0)),
                "rank": int(score.get("rank", 0)),
                "region": str(score.get("region", "")),
                "income": str(score.get("income", "")),
            })

        df = pd.DataFrame(records)
        if df.empty:
            return df

        # Add date and notes
        today = str(date.today())
        df["date"] = today
        df["value"] = df["aml_score"]

        # Determine edition year from payload metadata
        edition_year = "2025"
        for v in payload:
            if isinstance(v, str) and re.match(r"Public Edition \d{4}", v):
                edition_year = re.search(r"(\d{4})", v).group(1)
                break

        df["notes"] = df.apply(
            lambda r: (
                f"Basel AML Index {edition_year}·177国排名第{r['rank']}·"
                f"综合分{r['aml_score']:.2f}/10·"
                f"地区:{r['region']}·收入水平:{r['income']}"
            ),
            axis=1,
        )

        return df[["date", "value", "notes", "country", "iso2", "iso3", "rank", "region", "income"]]

    def basel_top_risks(self, n: int = 10) -> pd.DataFrame:
        """Top N highest-risk countries by Basel AML Index."""
        df = self.basel_country_scores()
        if df.empty:
            return df
        df = df.nlargest(n, "value")
        return df

    def basel_lowest_risks(self, n: int = 10) -> pd.DataFrame:
        """Top N lowest-risk countries by Basel AML Index."""
        df = self.basel_country_scores()
        if df.empty:
            return df
        df = df.nsmallest(n, "value")
        return df

    # ── Per-country lookups (used by pipeline for individual indicators) ──

    def fatf_country_status(self, country: str, list_type: str = "grey") -> pd.DataFrame:
        """
        Get FATF list status for a specific country.
        Returns a single-row DataFrame (or empty if not on the list).
        """
        if list_type == "grey":
            df = self.fatf_grey_list()
        else:
            df = self.fatf_black_list()
        if df.empty:
            return df
        return df[df["country"] == country].copy()

    def incsr_country_status(self, country: str) -> pd.DataFrame:
        """
        Get INCSR Major Money Laundering status for a specific country.
        Returns a single-row DataFrame (or empty if not listed).
        """
        df = self.incsr_major_ml_countries()
        if df.empty:
            return df
        return df[df["country"] == country].copy()

    def basel_country_score(self, country: str) -> pd.DataFrame:
        """
        Get Basel AML Index score for a specific country.
        Returns a single-row DataFrame with full score details (or empty if not found).
        """
        df = self.basel_country_scores()
        if df.empty:
            return df
        result = df[df["country"] == country]
        if result.empty:
            # Try partial match
            result = df[df["country"].str.contains(country, case=False, na=False)]
        return result.head(1).copy()
