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
_SKIP_PREFIXES = ("CHAPTER", "SECTION", "FIGURE", "TABLE", "APPENDIX", "PROVINCE", "NATIONAL")


def parse_no_drop(pdf_path: str | Path) -> pd.DataFrame:
    """
    Extracts per-WSA No Drop scores from the 2023 No Drop Report PDF.

    The report gives each WSA a section: one page with just the WSA name (and
    sometimes a page-number), followed immediately by a page containing
    "score of X%" in the regulatory impression text.

    Returns columns: name, nd_performance
    (nrw_percent is not available in this PDF — it lives in the companion
    "Status of Water Loss" report which must be loaded separately).
    """
    records: dict[str, float] = {}

    with pdfplumber.open(pdf_path) as pdf:
        pages = pdf.pages
        n = len(pages)

        # scan from page ~60 onward where provincial/WSA sections begin
        for i in range(50, n - 1):
            txt = (pages[i].extract_text() or "").strip()
            lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]

            # WSA header pages are very short (1–3 lines) — a name plus maybe a page number
            if not (1 <= len(lines) <= 3):
                continue

            name = lines[0]

            # skip obvious non-WSA pages
            if len(name) <= 3:
                continue
            if any(name.upper().startswith(prefix) for prefix in _SKIP_PREFIXES):
                continue
            if name[0].isdigit():
                continue

            # look for "score of X%" in the immediately following page
            next_txt = pages[i + 1].extract_text() or ""
            m = _SCORE_RE.search(next_txt)
            if not m:
                continue

            score = float(m.group(1))
            # title-case the name for consistent matching against DB rows
            records.setdefault(name.title(), score)

    rows = [
        {
            "name": name,
            "nd_performance": _classify_nd(score),
        }
        for name, score in records.items()
    ]

    return pd.DataFrame(rows).drop_duplicates(subset=["name"])
