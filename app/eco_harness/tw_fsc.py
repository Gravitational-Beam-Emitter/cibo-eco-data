"""
Taiwan FSC (金融監督管理委員會) Enforcement Data Harness.

Fetches major enforcement/penalty cases from the FSC RSS feed.
Data includes Chinese company names (繁體), penalty details, and representative names.

RSS feed: https://www.fsc.gov.tw/RSS/Messages?serno=201202290003&language=chinese
~495 records, updated as cases occur.
"""

from __future__ import annotations

import logging
import re
from typing import Optional
from xml.etree import ElementTree as ET

import requests

from app.name_matcher import NameMatcher

logger = logging.getLogger("eco_data.tw_fsc")

FSC_RSS_URL = "https://www.fsc.gov.tw/RSS/Messages"
FSC_RSS_PARAMS = {
    "serno": "201202290003",
    "language": "chinese",
}

# Patterns for extracting structured fields from raw HTML description.
# Run on raw `desc` (before HTML cleaning) where <br> tags provide clear field delimiters.
_RE_COMPANY = re.compile(
    r"(?:受處分人|受处分人|相對人|相對人姓名)[：:]\s*(.+?)(?:<br|<div|</div|$|\n)",
)
_RE_REP = re.compile(
    r"(?:代表人[或和]管理人姓名|公司代表人)[：:]\s*(.+?)(?:<br|<div|</div|$|\n)",
)
_RE_UNIFORM_ID = re.compile(
    r"營利事業統一編號[：:]\s*(\S+?)(?:<br|<div|</div|$|\n)",
)
_RE_ADDRESS = re.compile(
    r"地址[：:]\s*(.+?)(?:<br|<div|</div|$|\n)",
)
_RE_PENALTY_AMOUNT = re.compile(
    r"核處(?:新臺幣|新台币|罰鍰新臺幣)?[（(]?(?:以下同|下同)?[）)]?\s*(\d[\d,，]*)\s*萬元?(?:罰鍰|整)?"
)
_RE_PENALTY_AMOUNT2 = re.compile(
    r"核處罰鍰新臺幣[（(]下同[）)]?\s*(\d[\d,，]*)\s*萬元?整?"
)
_RE_CASE_DATE = re.compile(
    r"(?:發文日期|裁罰時間|處分時間)[：:]\s*中華民國\s*(\d+)\s*年\s*(\d+)\s*月\s*(\d+)\s*日"
)
_RE_DOC_NUMBER = re.compile(
    r"發文字號[：:]\s*(\S+?)(?:<br|<div|</div|$|\n)",
)


def _clean_html(text: str) -> str:
    """Strip HTML tags and normalize whitespace."""
    text = re.sub(r"<[^>]*>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _parse_roc_date(date_str: str) -> str:
    """Convert ROC year (中華民國) date string to ISO date.

    Accepts formats like '2025-09-25' or '中華民國114年9月25日'.
    """
    # Try ISO format first
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", date_str)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    # Try ROC year format
    m = re.search(r"中華民國\s*(\d+)\s*年\s*(\d+)\s*月\s*(\d+)\s*日", date_str)
    if m:
        roc_year = int(m.group(1))
        year = roc_year + 1911
        return f"{year:04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

    return date_str[:10] if len(date_str) >= 10 else date_str


def fetch_fsc_enforcements() -> list[dict]:
    """Fetch all Taiwan FSC enforcement cases from RSS feed.

    Returns list of structured enforcement records.
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

    logger.info("Fetching Taiwan FSC enforcement RSS feed...")
    resp = session.get(FSC_RSS_URL, params=FSC_RSS_PARAMS, timeout=30)
    resp.raise_for_status()

    root = ET.fromstring(resp.content)
    items = root.findall(".//item")
    logger.info(f"Fetched {len(items)} enforcement records from FSC RSS")

    records = []
    for item in items:
        title_el = item.find("title")
        desc_el = item.find("description")
        link_el = item.find("link")
        date_el = item.find("pubDate")

        title = title_el.text.strip() if title_el is not None and title_el.text else ""
        desc = desc_el.text if desc_el is not None and desc_el.text else ""
        link = link_el.text.strip() if link_el is not None and link_el.text else ""
        pub_date = date_el.text.strip() if date_el is not None and date_el.text else ""

        # Clean description
        desc_clean = _clean_html(desc)

        # Extract fields — regex on raw `desc` where <br> tags provide clear delimiters
        company = ""
        m = _RE_COMPANY.search(desc)
        if m:
            company = _clean_html(m.group(1)).strip()

        # Fallback: extract company name from title if not found in description
        # Titles often start with "CompanyName因/違反..." — extract the company name part
        if not company and title:
            _CJK = r"\u4e00-\u9fff"
            _SUFFIXES = (
                r"股份有限公司|有限公司|銀行|合作社|信用合作社|"
                r"保險公司|證券公司|投信公司|期貨公司|票券公司|產物保險|人壽保險"
            )
            _LOCATION = r"台灣分公司|臺灣分公司|台北分公司|臺北分公司|國際金融業務分行|分公司"
            # Clean HTML from title first
            title_clean = _clean_html(title)
            m_title = re.match(
                rf"((?:[{_CJK}A-Za-z]+)(?:{_SUFFIXES})(?:{_LOCATION})?)",
                title_clean,
            )
            if m_title:
                raw = m_title.group(1).strip()
                # Strip any remaining HTML tags (some titles have malformed HTML)
                raw = re.sub(r"<[^>]*>", "", raw)
                # Truncate at common title separators
                raw = re.split(r"因|違反|違規|涉及|涉嫌|依|之|及其|所合併|出席|於", raw)[0]
                raw = raw.strip()
                # Only accept if it looks like a company (has a suffix + no individual markers)
                if raw and not re.match(r"^[^\s]{1,4}(?:OO|ＯＯ|○○|君)", raw):
                    company = raw

        representative = ""
        m = _RE_REP.search(desc)
        if m:
            representative = _clean_html(m.group(1)).strip()

        uniform_id = ""
        m = _RE_UNIFORM_ID.search(desc)
        if m:
            uid = _clean_html(m.group(1)).strip()
            if uid and uid != "略":
                uniform_id = uid

        address = ""
        m = _RE_ADDRESS.search(desc)
        if m:
            addr = _clean_html(m.group(1)).strip()
            if addr and addr != "略" and addr != "同上":
                address = addr

        # Penalty amount (in 万元 NTD)
        penalty_amount = ""
        m = _RE_PENALTY_AMOUNT.search(desc_clean)
        if not m:
            m = _RE_PENALTY_AMOUNT2.search(desc_clean)
        if m:
            amt = m.group(1).replace(",", "").replace("，", "")
            penalty_amount = f"{amt}万元"

        # Case date
        case_date = ""
        m = _RE_CASE_DATE.search(desc_clean)
        if m:
            roc_year = int(m.group(1))
            year = roc_year + 1911
            case_date = f"{year:04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

        # Doc number — regex on raw desc for <br> delimiter, then clean HTML
        doc_number = ""
        m = _RE_DOC_NUMBER.search(desc)
        if m:
            doc_number = _clean_html(m.group(1)).strip()

        # Determine sector from title or description
        sector = ""
        if "銀行" in company or "銀行" in title:
            sector = "banking"
        elif "保險" in company or "保險" in title or "人壽" in company:
            sector = "insurance"
        elif "證券" in company or "證券" in title or "投信" in company:
            sector = "securities"
        elif "金融控股" in company or "金控" in title:
            sector = "financial_holding"
        elif "票券" in company:
            sector = "bills_finance"
        elif "期貨" in company:
            sector = "futures"
        else:
            sector = "other_financial"

        # Detect enforcement type
        enforcement_type = ""
        if "罰鍰" in desc_clean or "罰鍰" in title:
            enforcement_type = "fine"
        if "糾正" in desc_clean or "糾正" in title:
            enforcement_type = (enforcement_type + "+reprimand" if enforcement_type else "reprimand")
        if "停職" in desc_clean or "停止" in desc_clean or "解除職務" in desc_clean:
            enforcement_type = (enforcement_type + "+suspension" if enforcement_type else "suspension")
        if not enforcement_type:
            enforcement_type = "other"

        # Build notes with key details
        notes_parts = []
        if doc_number:
            notes_parts.append(f"发文字号:{doc_number}")
        if uniform_id:
            notes_parts.append(f"统编:{uniform_id}")
        if penalty_amount:
            notes_parts.append(f"处罚:{penalty_amount}")
        if address:
            notes_parts.append(f"地址:{address}")
        notes_parts.append(f"类型:{enforcement_type}")
        notes_parts.append(f"行业:{sector}")
        # Add title summary
        notes_parts.append(f"事由:{title[:200]}")

        record = {
            "source": "tw_fsc",
            "source_uid": doc_number or link[-50:],
            "name_en": "",
            "name_cn": company,
            "name_cn_norm": NameMatcher.normalize_cn(company) if company else "",
            "name_pinyin": NameMatcher.to_romanization(NameMatcher.normalize_cn(company)) if company else "",
            "name_type": "entity",  # FSC cases are mostly against companies
            "pep_level": "",
            "risk_category": "sanctions",
            "aliases": "",
            "programs": "tw_fsc_enforcement",
            "countries": "tw",
            "addresses": address,
            "source_date": case_date or _parse_roc_date(pub_date),
            "notes": " | ".join(notes_parts),
            # Extra metadata
            "_representative": representative,
            "_sector": sector,
            "_penalty_amount": penalty_amount,
            "_title": title,
            "_link": link,
        }
        records.append(record)

    return records


def load_tw_fsc_into_screening(db_path: str | None = None) -> int:
    """Fetch Taiwan FSC enforcement data and import into name_screening table.

    Returns number of records loaded.
    """
    try:
        from app.storage import init_db, upsert_screening_entry
    except ImportError:
        logger.error("Storage module not available")
        return 0

    records = fetch_fsc_enforcements()
    if not records:
        logger.warning("No Taiwan FSC enforcement records fetched")
        return 0

    conn = init_db(db_path)
    count = 0
    for rec in records:
        # Build entry for name_screening table
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
            logger.warning(f"Failed to upsert TW FSC entry: {rec['name_cn']}", exc_info=True)

    conn.close()
    logger.info(f"Loaded {count} Taiwan FSC enforcement entries into name_screening")
    return count
