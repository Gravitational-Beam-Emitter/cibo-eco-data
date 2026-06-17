"""
Hong Kong HKMA (金管局) Enforcement Data Harness.

Fetches disciplinary/enforcement press releases from the HKMA OpenAPI.
Data includes Chinese + English company names, penalty details.
Low volume (~3-5 records/year) but free and dual-language.

API: https://api.hkma.gov.hk/public/press-releases (free, no registration)
"""

from __future__ import annotations

import logging
import re

import requests

from app.name_matcher import NameMatcher

logger = logging.getLogger("eco_data.hk_hkma")

HKMA_API_URL = "https://api.hkma.gov.hk/public/press-releases"

# Keywords to identify disciplinary/enforcement press releases
# These are specific to actual HKMA disciplinary actions
_ENFORCEMENT_KW = [
    "紀律處分行動", "disciplinary action",
    "執法行動", "enforcement action",
    "紀律處分程序", "disciplinary proceeding",
]

# Company name suffix alternatives (shared across patterns)
_CO_SUFFIX_EN = (
    r"Limited|Ltd\.?|Inc\.?|Corp\.?|Corporation|PLC|LLC|Group|Holdings|"
    r"International|Financial|Capital|Securities|Insurance|"
    r"Bank(?:\s+AG)?|Banking\s+Corporation|"
    r"Financial\s+Services(?:\s+Limited)?|"
    r"Hong\s+Kong\s+Branch|"
    r"(?:[A-Z]{2,6}\s+Branch)"
)

# English company name — "fined/reprimanded XXXX HK$" or "fined/reprimanded XXXX ("
_RE_EN_FINED = re.compile(
    r"(?:fined|reprimanded)\s+(?:and\s+(?:fined|reprimanded)\s+)?"
    r"([A-Z0-9][A-Za-z0-9\s&.()（）,-]+?(?:" + _CO_SUFFIX_EN + r"))"
    r"(?:\s+\(|\s+HK\$|$)",
    re.IGNORECASE,
)

# English company name — "against XXX for/under" (handles "33 Financial Services Limited")
_RE_EN_AGAINST = re.compile(
    r"against\s+"
    r"([A-Z0-9][A-Za-z0-9\s&.()（）,-]+?(?:" + _CO_SUFFIX_EN + r"))"
    r"(?:\s+(?:for|under|of|\,|;|and|or|\())",
    re.IGNORECASE,
)

# English company names — colon-separated list after "in relation to"
# e.g. "in relation to three banks: Indian Overseas Bank, Hong Kong Branch (IOBHK), ..."
_RE_EN_COLON_LIST = re.compile(
    r"in\s+relation\s+to\s+(?:three\s+banks|the\s+following|the\s+banks)\s*:\s*"
    r"(.+?)(?:\.\s+The\s+Monetary|\.\s+The\s+disciplinary)",
    re.IGNORECASE,
)

# Individual company name extraction from a text snippet
_RE_EN_CO_NAME = re.compile(
    r"([A-Z][A-Za-z0-9\s&.()（）,-]+?(?:" + _CO_SUFFIX_EN + r"))"
    r"(?:\s+\([A-Z]+\))?",
    re.IGNORECASE,
)
# Chinese company name — suffix-based, from content area
_RE_CN_CONTENT = re.compile(
    r"((?:[\u4e00-\u9fff（）()A-Za-z0-9]{2,60}?)"
    r"(?:有限公司|股份有限公司|銀行|香港分行|香港分公司|"
    r"金融服務有限公司|保險公司|國際有限公司|集團))",
)
# Penalty: HK$ X,XXX,XXX / X港元
_RE_PENALTY = re.compile(
    r"(?:罰款|fine(?:d)?)\s*(?:of\s*)?(?:HK\$|港元?)?\s*"
    r"([\d,，]+)\s*(?:million|萬|万|元|港元?)?",
    re.IGNORECASE,
)
# HK$ amount directly
_RE_HKD = re.compile(
    r"(?:HK\$|HK\$|港元?)\s*([\d,，]+(?:\.\d+)?)\s*(?:million|萬|万|元)?",
    re.IGNORECASE,
)


def _is_enforcement(title: str) -> bool:
    """Check if a press release title is enforcement-related."""
    title_lower = title.lower()
    return any(kw.lower() in title_lower for kw in _ENFORCEMENT_KW)


def _extract_content_text(html: str) -> str:
    """Extract just the content area text from a HKMA press release page."""
    # Try to find the content-area div
    m = re.search(
        r'class="content-area[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>',
        html, re.DOTALL,
    )
    if not m:
        # Fallback: try content-wrapper
        m = re.search(
            r'class="content-wrapper[^"]*"[^>]*>(.*?)(?:<footer|</main)',
            html, re.DOTALL,
        )
    if m:
        text = m.group(1)
    else:
        text = html

    # Strip HTML tags
    text = re.sub(r"<[^>]*>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_names_from_html(html: str) -> tuple[list[str], list[str]]:
    """Extract company names from HKMA press release body HTML.

    Returns (companies, []) — individuals are rare in HKMA actions.
    """
    text = _extract_content_text(html)
    companies = []

    # Pattern 1: "fined/reprimanded XXXX HK$" or "fined/reprimanded XXXX ("
    for m in _RE_EN_FINED.finditer(text):
        name = m.group(1).strip()
        if len(name) > 4:
            companies.append(name)

    # Pattern 2: "against XXXX for/under"
    for m in _RE_EN_AGAINST.finditer(text):
        name = m.group(1).strip()
        if len(name) > 4 and name not in companies:
            companies.append(name)

    # Pattern 3: Colon-separated bank list after "in relation to three banks:"
    for m in _RE_EN_COLON_LIST.finditer(text):
        list_text = m.group(1).strip()
        # Split on ") ," or ") and" or "), " to get individual bank names
        parts = re.split(r"\)\s*(?:,|and)\s*", list_text)
        for part in parts:
            part = part.strip().rstrip(").")
            # Extract the company name before the abbreviation "(XXX)"
            name_m = _RE_EN_CO_NAME.search(part)
            if name_m:
                name = name_m.group(1).strip()
                if len(name) > 4 and name not in companies:
                    companies.append(name)

    # Pattern 4: Chinese company names in body
    for m in _RE_CN_CONTENT.finditer(text):
        name = m.group(1).strip()
        if len(name) >= 4 and name not in companies:
            companies.append(name)

    companies = list(dict.fromkeys(companies))
    return companies, []


def _extract_penalty_from_html(html: str) -> str:
    """Extract penalty amount from HKMA press release HTML."""
    text = _extract_content_text(html)

    # Try "fined HK$X" or "罰款 X港元"
    m = _RE_PENALTY.search(text)
    if m:
        amt = m.group(1).replace(",", "").replace("，", "")
        return f"HK${amt}"

    # Try direct HK$ amount near "fine" context
    m = _RE_HKD.search(text)
    if m:
        amt = m.group(1).replace(",", "").replace("，", "")
        return f"HK${amt}"

    return ""


def _extract_names_from_title(title: str) -> tuple[str, str]:
    """Extract primary company name from a HKMA press release title.

    Returns (name, type) where type is 'entity' or 'individual'.
    """
    _CN_CO = (
        r"(?:有限公司|股份有限公司|銀行|香港分行|香港分公司|"
        r"金融服務有限公司|保險公司|國際有限公司|集團|"
        r"Hong\s+Kong\s+Branch|Limited|Ltd\.?|Inc\.?|Bank|Branch)"
    )

    # Pattern 1: "對XXX違反/採取" (disciplinary against XXX)
    m = re.search(rf"對\s*((?:[\u4e00-\u9fff（）()A-Za-z0-9]{{2,40}}?){_CN_CO})(?:違反|採取|的調查)", title)
    if m:
        return m.group(1).strip(), "entity"

    # Pattern 2: "XXX因..." (company at start, before 因)
    m = re.search(rf"((?:[\u4e00-\u9fff（）()A-Za-z0-9]{{2,40}}?){_CN_CO})(?:因|及其|的)", title)
    if m:
        return m.group(1).strip(), "entity"

    # Pattern 3: Company after dash separator in joint releases
    # "金管局與證監會合作執法行動 - XXX因..."
    m = re.search(rf"[-—]\s*((?:[\u4e00-\u9fff（）()A-Za-z0-9]{{2,40}}?){_CN_CO})", title)
    if m:
        return m.group(1).strip(), "entity"

    return "", "entity"


def _extract_penalty_from_title(title: str) -> str:
    """Extract penalty from title (e.g. '罰款1,085萬港元')."""
    m = re.search(
        r"(?:罰款|罰鍰|罰金|罰)\s*"
        r"(?:HK\$?|港元?)?\s*"
        r"([\d,，]+)\s*"
        r"(?:萬|万|億|亿|元|港元?)?",
        title,
    )
    if m:
        amt = m.group(1).replace(",", "").replace("，", "")
        return f"HK${amt}万"
    return ""


def _fetch_detail_page(url: str) -> str:
    """Fetch a HKMA press release detail page. Returns HTML text."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 "
            "Chrome/125.0.0.0 Safari/537.36 "
            "EcoData/1.0"
        ),
    })
    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        logger.warning(f"Failed to fetch HKMA detail page {url}: {e}")
        return ""


def fetch_hkma_enforcements() -> list[dict]:
    """Fetch HKMA enforcement press releases and extract structured data.

    Names are extracted from the press release title (structured format).
    Penalties are extracted from the detail page body.
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36 "
            "EcoData/1.0"
        ),
    })

    logger.info("Fetching HKMA press releases...")
    resp = session.get(HKMA_API_URL, params={
        "pagesize": 1000,
        "sort": "date-DESC",
        "lang": "tc",
    }, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    all_releases = data["result"]["records"]
    logger.info(f"Fetched {len(all_releases)} HKMA press releases")

    # Filter for enforcement-related
    enforcement = [r for r in all_releases if _is_enforcement(r["title"])]
    logger.info(f"Found {len(enforcement)} enforcement-related releases")

    records = []
    for rel in enforcement:
        title_cn = rel["title"]
        date = rel["date"]
        link_tc = rel["link"]
        link_en = link_tc.replace("/chi/", "/eng/")

        # Extract names from the Chinese title (structured format)
        name_cn, name_type = _extract_names_from_title(title_cn)

        # Fetch English page for English name + penalty from body
        html_en = _fetch_detail_page(link_en)
        penalty = ""
        en_companies = []
        if html_en:
            penalty = _extract_penalty_from_html(html_en)
            en_companies, _ = _extract_names_from_html(html_en)

        # Also fetch Chinese page for penalty and additional Chinese names
        html_cn = _fetch_detail_page(link_tc)
        cn_companies = []
        if html_cn:
            if not penalty:
                penalty = _extract_penalty_from_html(html_cn)
            cn_companies, _ = _extract_names_from_html(html_cn)

        # If Chinese name extraction from title failed, try from body
        if not name_cn and cn_companies:
            name_cn = cn_companies[0]

        # If Chinese name still empty (e.g. "three banks"), use English company names
        if not name_cn and en_companies:
            name_cn = en_companies[0]

        # Try penalty from title as last resort
        if not penalty:
            penalty = _extract_penalty_from_title(title_cn)

        # Determine which names to create records for
        # If multiple companies extracted from body, create a record for each
        if len(en_companies) > 1:
            names_to_record = []
            for en_name in en_companies:
                names_to_record.append((en_name, en_name))  # (name_en, name_cn)
        else:
            name_en = en_companies[0] if en_companies else ""
            names_to_record = [(name_en, name_cn)]

        for idx, (name_en, rec_cn) in enumerate(names_to_record):
            # Build notes
            notes_parts = [f"来源:HK HKMA"]
            if penalty:
                notes_parts.append(f"处罚:{penalty}")
            if len(names_to_record) > 1:
                notes_parts.append(f"涉及银行{idx+1}/{len(names_to_record)}")
            notes_parts.append(f"事由:{title_cn[:300]}")

            record = {
                "source": "hk_hkma",
                "source_uid": link_tc.rsplit("/", 2)[-2] if "/" in link_tc else date,
                "name_en": name_en,
                "name_cn": rec_cn,
                "name_cn_norm": NameMatcher.normalize_cn(rec_cn) if rec_cn else "",
                "name_pinyin": NameMatcher.to_romanization(
                    NameMatcher.normalize_cn(rec_cn)
                ) if rec_cn else "",
                "name_type": name_type,
                "pep_level": "",
                "risk_category": "sanctions",
                "aliases": "",
                "programs": "hk_hkma_enforcement",
                "countries": "hk",
                "addresses": "",
                "source_date": date,
                "notes": " | ".join(notes_parts),
                "_penalty_amount": penalty,
                "_title": title_cn,
            }
            # For multi-name records, make source_uid unique
            if len(names_to_record) > 1:
                record["source_uid"] = f"{record['source_uid']}_{idx}"
            records.append(record)

    return records


def load_hk_hkma_into_screening(db_path: str | None = None) -> int:
    """Fetch HKMA enforcement data and import into name_screening table."""
    try:
        from app.storage import init_db, upsert_screening_entry
    except ImportError:
        logger.error("Storage module not available")
        return 0

    records = fetch_hkma_enforcements()
    if not records:
        logger.warning("No HKMA enforcement records fetched")
        return 0

    conn = init_db(db_path)
    count = 0
    for rec in records:
        entry = {
            "source": rec["source"],
            "source_uid": rec["source_uid"],
            "name_en": rec["name_en"],
            "name_cn": rec["name_cn"],
            "name_cn_norm": rec["name_cn_norm"],
            "name_pinyin": rec["name_pinyin"],
            "name_type": rec["name_type"],
            "pep_level": rec["pep_level"],
            "risk_category": rec["risk_category"],
            "aliases": rec["aliases"],
            "programs": rec["programs"],
            "countries": rec["countries"],
            "addresses": rec["addresses"],
            "source_date": rec["source_date"],
            "notes": rec["notes"],
        }
        try:
            upsert_screening_entry(conn, entry)
            count += 1
        except Exception:
            logger.warning(f"Failed to upsert HKMA entry: {rec['name_cn']}", exc_info=True)

    conn.close()
    logger.info(f"Loaded {count} HKMA enforcement entries into name_screening")
    return count
