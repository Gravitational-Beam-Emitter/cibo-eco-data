"""
Sanctions & Corruption Data Harness — OFAC SDN + TI CPI.

Sources:
  OFAC SDN — US Treasury Specially Designated Nationals (XML, daily updates)
  TI CPI   — Transparency International Corruption Perceptions Index (Wikipedia, annual)

Each method returns pd.DataFrame with columns: date, value, notes
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date
from io import BytesIO

import pandas as pd
import requests

OFAC_SDN_URL = "https://sanctionslistservice.ofac.treas.gov/api/publicationpreview/exports/sdn.xml"
OFAC_XML_NS = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/XML"


class SanctionsHarness:
    """OFAC sanctions + TI Corruption Perceptions Index data access."""

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

    # ── OFAC SDN ─────────────────────────────────────────────────

    def _fetch_sdn_xml(self) -> bytes:
        """Download the full SDN XML. Returns raw bytes or raises."""
        resp = self._session.get(OFAC_SDN_URL, timeout=60)
        resp.raise_for_status()
        return resp.content

    def ofac_sdn_list(self) -> pd.DataFrame:
        """
        Full OFAC SDN list — all sanctioned entities, individuals, vessels, aircraft.
        Returns DataFrame with: uid, name, sdn_type, programs, addresses, aliases.
        """
        try:
            xml_bytes = self._fetch_sdn_xml()
            tree = ET.parse(BytesIO(xml_bytes))
            root = tree.getroot()

            pub = root.find(f"{{{OFAC_XML_NS}}}publshInformation")
            pub_date = pub.find(f"{{{OFAC_XML_NS}}}Publish_Date").text if pub is not None else ""

            records = []
            for entry in root.findall(f"{{{OFAC_XML_NS}}}sdnEntry"):
                uid = entry.find(f"{{{OFAC_XML_NS}}}uid")
                last_name = entry.find(f"{{{OFAC_XML_NS}}}lastName")
                first_name = entry.find(f"{{{OFAC_XML_NS}}}firstName")
                sdn_type = entry.find(f"{{{OFAC_XML_NS}}}sdnType")
                title = entry.find(f"{{{OFAC_XML_NS}}}title")

                # Build full name
                name_parts = []
                if first_name is not None and first_name.text:
                    name_parts.append(first_name.text)
                if last_name is not None and last_name.text:
                    name_parts.append(last_name.text)
                if not name_parts and title is not None and title.text:
                    name_parts.append(title.text)
                name = " ".join(name_parts) if name_parts else "UNKNOWN"

                # Sanctions programs
                prog_list = entry.find(f"{{{OFAC_XML_NS}}}programList")
                programs = []
                if prog_list is not None:
                    for prog in prog_list.findall(f"{{{OFAC_XML_NS}}}program"):
                        if prog.text:
                            programs.append(prog.text)

                # Addresses
                addr_list = entry.find(f"{{{OFAC_XML_NS}}}addressList")
                addresses = []
                countries = set()
                if addr_list is not None:
                    for addr in addr_list.findall(f"{{{OFAC_XML_NS}}}address"):
                        parts = []
                        for tag in ("address1", "address2", "address3", "city",
                                     "stateOrProvince", "postalCode", "country"):
                            el = addr.find(f"{{{OFAC_XML_NS}}}{tag}")
                            if el is not None and el.text:
                                parts.append(el.text.strip())
                                if tag == "country":
                                    countries.add(el.text.strip())
                        if parts:
                            addresses.append(", ".join(parts))

                # Aliases (AKAs)
                aka_list = entry.find(f"{{{OFAC_XML_NS}}}akaList")
                aliases = []
                if aka_list is not None:
                    for aka in aka_list.findall(f"{{{OFAC_XML_NS}}}aka"):
                        aka_last = aka.find(f"{{{OFAC_XML_NS}}}lastName")
                        aka_first = aka.find(f"{{{OFAC_XML_NS}}}firstName")
                        aka_type = aka.find(f"{{{OFAC_XML_NS}}}type")
                        aka_parts = []
                        if aka_first is not None and aka_first.text:
                            aka_parts.append(aka_first.text)
                        if aka_last is not None and aka_last.text:
                            aka_parts.append(aka_last.text)
                        aka_name = " ".join(aka_parts)
                        aka_info = {"name": aka_name}
                        if aka_type is not None and aka_type.text:
                            aka_info["type"] = aka_type.text
                        aliases.append(aka_info)

                records.append({
                    "uid": int(uid.text) if uid is not None and uid.text else 0,
                    "name": name,
                    "sdn_type": sdn_type.text if sdn_type is not None else "Unknown",
                    "programs": ", ".join(programs),
                    "countries": ", ".join(sorted(countries)),
                    "addresses": " | ".join(addresses),
                    "aliases": ", ".join(a["name"] for a in aliases if a["name"]),
                })

            df = pd.DataFrame(records)
            df["date"] = pd.to_datetime(pub_date).strftime("%Y-%m-%d")
            df["value"] = 1
            df["notes"] = df.apply(
                lambda r: (
                    f"OFAC SDN·{r['sdn_type']}·{r['name']}·"
                    f"制裁计划:{r['programs'][:100]}·"
                    f"关联国家:{r['countries'][:80]}"
                ),
                axis=1,
            )
            return df[["date", "value", "notes", "name", "sdn_type", "programs",
                        "countries", "addresses", "aliases"]]

        except Exception:
            return pd.DataFrame()

    def ofac_sanctions_by_country(self) -> pd.DataFrame:
        """
        OFAC sanctions aggregated by country.
        Returns per-country counts of sanctioned entities, individuals, vessels, aircraft.
        """
        df = self.ofac_sdn_list()
        if df.empty:
            return df

        today = str(date.today())
        records = []

        # Explode countries (each entry may have multiple countries)
        country_entries: dict[str, dict] = {}
        for _, row in df.iterrows():
            countries_str = row.get("countries", "")
            if not countries_str or pd.isna(countries_str):
                continue
            for c in countries_str.split(", "):
                c = c.strip()
                if not c:
                    continue
                if c not in country_entries:
                    country_entries[c] = {
                        "entities": 0, "individuals": 0, "vessels": 0, "aircraft": 0,
                        "programs": set(),
                    }
                sdn_type = str(row.get("sdn_type", "")).lower()
                if sdn_type == "entity":
                    country_entries[c]["entities"] += 1
                elif sdn_type == "individual":
                    country_entries[c]["individuals"] += 1
                elif sdn_type == "vessel":
                    country_entries[c]["vessels"] += 1
                elif sdn_type == "aircraft":
                    country_entries[c]["aircraft"] += 1

                for prog in str(row.get("programs", "")).split(", "):
                    if prog.strip():
                        country_entries[c]["programs"].add(prog.strip())

        for country, stats in country_entries.items():
            total = stats["entities"] + stats["individuals"] + stats["vessels"] + stats["aircraft"]
            records.append({
                "date": today,
                "value": total,
                "notes": (
                    f"OFAC制裁·{country}·"
                    f"实体{stats['entities']}·个人{stats['individuals']}·"
                    f"船舶{stats['vessels']}·飞行器{stats['aircraft']}·"
                    f"制裁计划:{','.join(sorted(stats['programs'])[:5])}"
                ),
                "country": country,
                "entities": stats["entities"],
                "individuals": stats["individuals"],
                "vessels": stats["vessels"],
                "aircraft": stats["aircraft"],
            })

        return pd.DataFrame(records)

    def ofac_country_sanctions(self, country: str) -> pd.DataFrame:
        """Get sanctions summary for a specific country."""
        df = self.ofac_sanctions_by_country()
        if df.empty:
            return df
        return df[df["country"] == country].copy()

    def ofac_total_counts(self) -> pd.DataFrame:
        """Aggregate OFAC SDN counts: total entities, individuals, vessels, aircraft."""
        df = self.ofac_sdn_list()
        if df.empty:
            return df

        today = str(date.today())
        type_counts = df["sdn_type"].value_counts().to_dict()
        total = len(df)
        program_count = len(set(
            p for progs in df["programs"].dropna() for p in str(progs).split(", ") if p
        ))

        return pd.DataFrame([{
            "date": today,
            "value": total,
            "notes": (
                f"OFAC SDN制裁总计·{total}条·"
                f"实体{type_counts.get('Entity', 0)}·"
                f"个人{type_counts.get('Individual', 0)}·"
                f"船舶{type_counts.get('Vessel', 0)}·"
                f"飞行器{type_counts.get('Aircraft', 0)}·"
                f"制裁计划{program_count}个"
            ),
        }])

    # ── TI CPI ────────────────────────────────────────────────────

    def cpi_scores(self) -> pd.DataFrame:
        """
        Transparency International Corruption Perceptions Index.
        Parses the latest year's country table from Wikipedia.
        Returns DataFrame with: country, rank, score (0-100), rank_change.
        """
        url = "https://en.wikipedia.org/wiki/Corruption_Perceptions_Index"
        try:
            resp = self._session.get(url, timeout=15)
            resp.raise_for_status()
            html = resp.text
        except Exception:
            return pd.DataFrame()

        # Find the country data table (largest wikitable with >100 rows)
        all_tables = re.findall(r'<table[^>]*>(.*?)</table>', html, re.DOTALL)
        country_table = None
        for table in all_tables:
            rows = re.findall(r'<tr>(.*?)</tr>', table, re.DOTALL)
            if len(rows) > 100:
                country_table = table
                break

        if not country_table:
            return pd.DataFrame()

        # Determine which year this data is for
        year_match = re.search(r'<span class="mw-headline" id="(\d{4})_scores">', html)
        cpi_year = year_match.group(1) if year_match else str(date.today().year)

        rows = re.findall(r'<tr>(.*?)</tr>', country_table, re.DOTALL)
        records = []

        for row in rows[1:]:  # Skip header
            cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL)
            cell_text = []
            for c in cells:
                t = re.sub(r'<[^>]+>', '', c).strip()
                t = re.sub(r'\[\d+\]', '', t).strip()  # Remove citations
                t = re.sub(r'&#160;', ' ', t)
                t = re.sub(r'&amp;', '&', t)
                cell_text.append(t)

            if len(cell_text) >= 3:
                rank = cell_text[0]
                country = cell_text[1]
                score = cell_text[2]
                rank_change = cell_text[3] if len(cell_text) > 3 else ""

                # Clean country name
                country = re.sub(r'\s*\([^)]*\)', '', country).strip()

                # Skip non-country rows
                if not country or not score:
                    continue
                if country in ('Nation or Territory', 'Score', '#', 'Rank', ''):
                    continue

                try:
                    score_val = int(score)
                except ValueError:
                    continue

                if len(country) < 3 or len(country.split()) > 8:
                    continue

                records.append({
                    "country": country,
                    "rank": int(rank) if rank.isdigit() else 0,
                    "score": score_val,
                    "rank_change": rank_change.strip(),
                })

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        today = str(date.today())
        df["date"] = today
        df["value"] = df["score"]

        df["notes"] = df.apply(
            lambda r: (
                f"TI Corruption Perceptions Index {cpi_year}·"
                f"排名第{r['rank']}/180·"
                f"评分{r['score']}/100·"
                f"排名变化:{r['rank_change'] if r['rank_change'] else '不变'}"
            ),
            axis=1,
        )

        return df[["date", "value", "notes", "country", "rank", "score", "rank_change"]]

    def cpi_country_score(self, country: str) -> pd.DataFrame:
        """Get CPI score for a specific country."""
        df = self.cpi_scores()
        if df.empty:
            return df
        result = df[df["country"] == country]
        if result.empty:
            result = df[df["country"].str.contains(country, case=False, na=False)]
        return result.head(1).copy()

    def cpi_top_risks(self, n: int = 10) -> pd.DataFrame:
        """Top N most corrupt countries (lowest CPI scores)."""
        df = self.cpi_scores()
        if df.empty:
            return df
        return df.nsmallest(n, "score")

    def cpi_cleanest(self, n: int = 10) -> pd.DataFrame:
        """Top N least corrupt countries (highest CPI scores)."""
        df = self.cpi_scores()
        if df.empty:
            return df
        return df.nlargest(n, "score")
