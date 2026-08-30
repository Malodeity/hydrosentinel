import re
from pathlib import Path

import pandas as pd
import pdfplumber

_PCT_RE = re.compile(r"^\d{1,3}(?:\.\d+)?%$")
_ARROW_CHARS = {"↑", "↓", "→", "="}
_SKIP_PREFIXES = ("totals", "wsa name")

# Chapter start pages (1-indexed) in the full 2023 Blue Drop report — used to
# scope the per-province table search and to label each row with its province.
_PROVINCE_CHAPTERS = {
    "Eastern Cape": 54,
    "Free State": 109,
    "Gauteng": 163,
    "KwaZulu-Natal": 201,
    "Limpopo": 260,
    "Mpumalanga": 304,
    "North West": 356,
    "Northern Cape": 398,
    "Western Cape": 467,
}


def _classify_bdrr(score: float) -> str:
    # matches the report's own BDRR Risk Barometer categories (Figure 21 legend)
    if score >= 90.0:
        return "high"  # critical collapsed into high — app's RiskLevel has 3 tiers, not 4
    if score >= 70.0:
        return "high"
    if score >= 50.0:
        return "medium"
    return "low"


def _extract_name_and_scores(row: list) -> tuple[str, float, float] | None:
    compact = [str(c).strip() for c in row if c not in (None, "")]
    if not compact:
        return None

    pct_values = [float(tok.rstrip("%")) for tok in compact if _PCT_RE.match(tok)]
    if len(pct_values) < 2:
        return None
    bdrr_2022, bdrr_2023 = pct_values[0], pct_values[1]

    name = next(
        (tok for tok in compact if not _PCT_RE.match(tok) and tok not in _ARROW_CHARS and not tok.isdigit() and len(tok) > 2),
        None,
    )
    if not name or name.lower().startswith(_SKIP_PREFIXES):
        return None

    return name, bdrr_2022, bdrr_2023


def parse_bdrr(pdf_path: str | Path) -> pd.DataFrame:
    """
    Extracts each WSA's Blue Drop Risk Rating (%BDRR/BDRRmax) for 2022 and 2023
    from the full 2023 Blue Drop Report. Unlike our own heuristic/XGBoost risk
    scoring, BDRR is computed independently by DWS auditors across 5 risk
    indicators (design capacity, operational capacity, water quality
    compliance, technical capacity, water safety plans) — a genuine
    ground-truth label for model training, not a value derived from our own
    feature set.

    Returns columns: name, province, bdrr_score_2023, bdrr_risk_level
    (bdrr_risk_level uses the app's existing low/medium/high scale; the
    report's "critical" tier (90-100%) collapses into "high").
    """
    records: list[dict] = []

    with pdfplumber.open(pdf_path) as pdf:
        n = len(pdf.pages)
        chapter_bounds = sorted(_PROVINCE_CHAPTERS.items(), key=lambda kv: kv[1])

        for idx, (province, start_page) in enumerate(chapter_bounds):
            end_page = chapter_bounds[idx + 1][1] if idx + 1 < len(chapter_bounds) else n
            # BDRR table appears within the first ~35 pages of a chapter and can span up to 3 pages
            search_end = min(start_page + 35, end_page, n)

            table_pages: list[int] = []
            for page_num in range(start_page - 1, search_end):
                tables = pdf.pages[page_num].extract_tables()
                for table in tables:
                    if not table or len(table) < 3:
                        continue
                    header_blob = " ".join(str(c or "") for row in table[:3] for c in row).upper()
                    if "WSA NAME" in header_blob and "BDRR" in header_blob:
                        table_pages.append(page_num)
                        break
                if table_pages and page_num > table_pages[-1] + 1:
                    break  # table block ended (non-consecutive page without the header)

            for page_num in table_pages:
                for table in pdf.pages[page_num].extract_tables():
                    for row in table:
                        parsed = _extract_name_and_scores(row)
                        if not parsed:
                            continue
                        name, _bdrr_2022, bdrr_2023 = parsed
                        records.append({
                            "name": name,
                            "province": province,
                            "bdrr_score_2023": bdrr_2023,
                            "bdrr_risk_level": _classify_bdrr(bdrr_2023),
                        })

    return pd.DataFrame(records).drop_duplicates(subset=["name"])
