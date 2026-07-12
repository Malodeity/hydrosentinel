import re
from pathlib import Path

import pandas as pd
import pdfplumber


def _classify_nd(score: float | None) -> str:
    # thresholds from the 2023 No Drop report performance categories
    if score is None:
        return "average"
    if score >= 90.0:
        return "excellent"
    if score >= 80.0:
        return "good"
    if score >= 50.0:
        return "average"
    if score >= 31.0:
        return "poor"
    return "critical"


_SCORE_RE = re.compile(r"score of (\d+(?:\.\d+)?)\s*%", re.IGNORECASE)
_PROVINCE_RE = re.compile(r"(?:\d+\s+)?([A-Z\s\-]+):\s*NO DROP REPORT", re.IGNORECASE)
_SKIP_PREFIXES = ("CHAPTER", "SECTION", "FIGURE", "TABLE", "APPENDIX", "PROVINCE", "NATIONAL")

# Map from the headings in the PDF to the province names used in the DB
_PROVINCE_MAP = {
    "EASTERN CAPE": "Eastern Cape",
    "FREE STATE": "Free State",
    "GAUTENG": "Gauteng",
    "KWAZULU NATAL": "KwaZulu-Natal",
    "LIMPOPO": "Limpopo",
    "MPUMALANGA": "Mpumalanga",
    "NORTH WEST": "North West",
    "NORTHERN CAPE": "Northern Cape",
    "WESTERN CAPE": "Western Cape",
}


def parse_no_drop(pdf_path: str | Path) -> pd.DataFrame:
    """
    Extracts per-WSA No Drop scores from the 2023 No Drop Report PDF.

    The report is organised into provincial sections ("X PROVINCE: NO DROP REPORT")
    followed by individual WSA pages: a short header page (WSA name only) then a
    regulatory-impression page containing "score of X%".

    Returns columns: name, province, nd_performance
    (nrw_percent is not available in this PDF — it lives in the companion
    "Status of Water Loss" report which must be loaded separately).
    """
    records: list[dict] = []
    current_province: str | None = None

    with pdfplumber.open(pdf_path) as pdf:
        pages = pdf.pages
        n = len(pages)

        for i in range(50, n - 1):
            txt = (pages[i].extract_text() or "").strip()
            lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]

            if not lines:
                continue

            # Detect provincial section header
            m_prov = _PROVINCE_RE.match(lines[0])
            if m_prov:
                raw = m_prov.group(1).strip().upper()
                current_province = _PROVINCE_MAP.get(raw)
                continue

            # WSA header pages are very short (1–3 lines)
            if not (1 <= len(lines) <= 3):
                continue

            name = lines[0]
            if len(name) <= 3:
                continue
            if any(name.upper().startswith(prefix) for prefix in _SKIP_PREFIXES):
                continue
            if name[0].isdigit():
                continue

            # look for "score of X%" on the immediately following page
            next_txt = pages[i + 1].extract_text() or ""
            m_score = _SCORE_RE.search(next_txt)
            if not m_score:
                continue

            score = float(m_score.group(1))
            records.append({
                "name": name.title(),
                "province": current_province,
                "nd_performance": _classify_nd(score),
            })

    df = pd.DataFrame(records).drop_duplicates(subset=["name"])
    return df
