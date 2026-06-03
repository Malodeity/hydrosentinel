import re
from pathlib import Path

import pandas as pd
import pdfplumber


_PCT_RE = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%")

_PROVINCE_MARKERS = {
    "EASTERN CAPE": "Eastern Cape",
    "FREE STATE": "Free State",
    "GAUTENG": "Gauteng",
    "KWAZULU-NATAL": "KwaZulu-Natal",
    "KWAZULU NATAL": "KwaZulu-Natal",
    "LIMPOPO": "Limpopo",
    "MPUMALANGA": "Mpumalanga",
    "NORTHERN CAPE": "Northern Cape",
    "NORTH WEST": "North West",
    "WESTERN CAPE": "Western Cape",
}

_GARBAGE_TOKENS = (
    # parser noise / label rows
    "DURING THE AUDIT", "IN SUCH CASES", "WHERE A SYSTEM", "TABLE", "FIGURE",
    "DIAGNOSTIC", "PROVINCE", "NATIONAL", "PERFORMANCE", "BLUE DROP SCORES",
    "GREEN DROP", "WATER BOARD", "TOTAL", "SUBTOTAL", "WATER SUPPLY OPERATIONS",
    "NO PROOF", "WSI GLOBAL", "AVAILABLE", "DESIGN CAPACITY",
    # Blue Drop KPI scoring categories (appear as row labels in scoring tables)
    "DWQ", "FINANCIAL MANAGEMENT", "TECHNICAL MANAGEMENT", "RISK DEFINED",
    "CHEMICAL COMPLIANCE", "MICROBIOLOGICAL COMPLIANCE", "CAPACITY MANAGEMENT",
    "RESOURCE ABSTRACTED", "PENALTIES", "O&M BUDGET", "O&M SPEND", "BENCHMARK",
    "BONUS", "WATER SAFETY", "PROCESS CONTROL", "ASSET MANAGEMENT",
    # SA province names used as row labels in national comparison tables
    "EASTERN CAPE", "FREE STATE", "GAUTENG", "KWAZULU", "LIMPOPO",
    "MPUMALANGA", "NORTHERN CAPE", "NORTH WEST", "WESTERN CAPE",
    # SANParks rest camp / game reserve water systems (not municipal WSAs)
    "SANPARKS", "SKUKUZA", "MALELANE", "BALULE", "LETABA", "OLIFANTS",
    "NKUHLU", "PHABENE", "SHINGWEDZI", "CROCODILE BRIDGE", "LOWER SABIE",
    "KRUGER GATE", "KRUGER PARK",
    # water treatment works names (not WSAs)
    "NSEZI",
    # bullet point text extracted as cell value
    "✓", "•",
    # performance tier labels used in quality compliance tables
    "EXCELLENT", "GOOD", "UNACCEPTABLE", "ACCEPTABLE", "MODIFIED SALGA",
    # chart legend labels extracted from bar chart tables
    "BLUE DROP SCORE 20", "BDRR 20", "INCENTIVE-BASED",
    # percentage-range scale labels (">95 – 100% Excellent" etc.)
    ">", "% SPLIT",
)


def _extract_pct(raw: str | None) -> float | None:
    if not raw:
        return None
    m = _PCT_RE.search(str(raw))
    v = float(m.group(1)) if m else None
    return v if v is not None and 0.0 <= v <= 100.0 else None


def _classify_bd(score: float | None) -> str:
    if score is None:
        return "non_certified"
    if score >= 95.0:
        return "certified"
    if score >= 50.0:
        return "non_certified"
    if score >= 31.0:
        return "poor"
    return "critical"


def _detect_province(page_text: str) -> str | None:
    # only scan the first 600 chars — chapter headings are at the top of the page
    # this avoids false province changes from cross-references deep in body text
    upper = page_text[:600].upper()
    for marker, canonical in _PROVINCE_MARKERS.items():
        if f"{marker} PROVINCE" in upper:
            return canonical
    return None


def _is_wsa_name(value: str | None) -> bool:
    if not value:
        return False
    v = value.strip()
    if len(v) < 4 or len(v) > 80:
        return False
    if v[0].isdigit():
        return False
    if "(" in v or ")" in v:
        return False
    upper = v.upper()
    if any(upper.startswith(g) for g in _GARBAGE_TOKENS):
        return False
    if v.count(".") > 1 or v.count(",") > 3:
        return False
    return True


def _combined_header(table: list, nrows: int = 2) -> str:
    return " ".join(
        str(c or "").upper()
        for row in table[:nrows]
        for c in row
    )


def _find_name_col(header: list) -> int:
    return next(
        (i for i, c in enumerate(header)
         if any(t in str(c or "").upper() for t in ("WSA", "WB NAME", "WB/WSP", "NAME", "MUNICIPALITY", "INSTITUTION"))),
        0,
    )


def _find_score_col(table: list, nrows: int = 2) -> int | None:
    """
    Finds the 2023 BD score column across up to nrows header rows.
    Skips columns that are clearly BDRR (risk rating) rather than BD score.
    """
    if not table:
        return None
    max_cols = max(len(r) for r in table[:nrows])
    for col in range(max_cols):
        cell_text = " ".join(
            str(table[row][col] or "").upper()
            for row in range(min(nrows, len(table)))
            if col < len(table[row])
        )
        # must mention 2023 and BD or SCORE or AUDIT or BLUE DROP
        if "2023" not in cell_text:
            continue
        if not any(t in cell_text for t in ("BD", "SCORE", "AUDIT", "BLUE DROP")):
            continue
        # exclude pure BDRR columns (risk rating, not score)
        if "BDRR" in cell_text and "SCORE" not in cell_text:
            continue
        return col
    return None


def _find_wss_col(table: list, nrows: int = 2) -> int | None:
    if not table:
        return None
    max_cols = max(len(r) for r in table[:nrows])
    for col in range(max_cols):
        cell_text = " ".join(
            str(table[row][col] or "").upper()
            for row in range(min(nrows, len(table)))
            if col < len(table[row])
        )
        if "WSS" in cell_text and "#" in cell_text:
            return col
    return None


def _extract_name_from_row(row: list, hint_col: int) -> str | None:
    """
    Handles pdfplumber's merged-cell offset: the actual name may be at
    hint_col, hint_col+1, or hint_col+2 depending on how cells were expanded.
    Scans a small window and returns the first valid WSA name found.
    """
    for col in range(max(0, hint_col - 1), min(len(row), hint_col + 4)):
        v = str(row[col] or "").strip()
        if _is_wsa_name(v):
            return v
    return None


def _extract_score_from_row(row: list, hint_col: int) -> float | None:
    """
    Handles merged-cell offset: score may be at hint_col, hint_col+1, or hint_col+2.
    Returns the first valid 0-100 percentage found in the window.
    """
    for col in range(hint_col, min(len(row), hint_col + 3)):
        s = _extract_pct(str(row[col] or ""))
        if s is not None:
            return s
    return None


def _data_start(table: list) -> int:
    if len(table) < 2:
        return 1
    second = table[1]
    has_pct = any(_extract_pct(str(c or "")) is not None for c in second)
    has_name = _is_wsa_name(str(second[0] or "")) or _is_wsa_name(str(second[1] if len(second) > 1 else ""))
    if not has_pct and not has_name:
        return 2
    return 1


def _looks_like_data_row(row: list) -> bool:
    if not row or len(row) < 2:
        return False
    # name can be in col 0 or col 1 (merged cell offset)
    has_name = any(_is_wsa_name(str(row[c] or "")) for c in range(min(3, len(row))))
    has_pct = any(_extract_pct(str(c or "")) is not None for c in row[1:])
    return has_name and has_pct


def parse_blue_drop(pdf_path: str | Path) -> pd.DataFrame:
    """
    Extracts per-WSA Blue Drop scores, certification tier, and WSS count from
    the 2023 Blue Drop Report PDF.

    Key challenge: pdfplumber expands merged-cell table headers with empty
    placeholder columns, so the actual data in each row is offset by +1 from
    the column index indicated by the header label. _extract_name_from_row and
    _extract_score_from_row both scan a small window around the header-derived
    column to handle this reliably.
    """
    score_records: dict[str, float] = {}
    wss_records: dict[str, int] = {}
    province_records: dict[str, str] = {}
    current_province: str | None = None
    in_non_municipal = False  # SANParks and other non-municipal sections

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""

            # stop extracting once we enter the SANParks / non-municipal section
            # only check after page 500 to avoid false-positive on the table of contents
            if page.page_number > 500 and (
                "NON-MUNICIPAL SYSTEMS" in page_text.upper()
                or "SANPARKS WATER MANAGEMENT" in page_text.upper()
            ):
                in_non_municipal = True
            if in_non_municipal:
                continue

            detected = _detect_province(page_text)
            if detected:
                current_province = detected

            tables = page.extract_tables()
            if not tables:
                continue

            for table in tables:
                if not table or len(table) < 2:
                    continue

                header = table[0]
                combined = _combined_header(table, nrows=2)
                start = _data_start(table)
                name_col = _find_name_col(header)

                has_wsa = any(t in combined for t in ("WSA", "WB NAME", "WB/WSP", "NAME", "MUNICIPALITY", "INSTITUTION"))
                has_score = (
                    "2023" in combined
                    and any(t in combined for t in ("BD", "SCORE", "AUDIT", "BLUE DROP"))
                    # skip pure BDRR risk rating tables
                    and not ("BDRR" in combined and "SCORE" not in combined and "AUDIT" not in combined)
                    # skip performance/benchmark tables
                    and not any(t in combined for t in ("BENCHMARK", "OPERATIONS COST", "O&M BUDGET"))
                )
                has_wss = "WSS" in combined and "#" in combined

                if has_wsa and has_score:
                    score_col = _find_score_col(table, nrows=2)
                    if score_col is not None:
                        for row in table[start:]:
                            name = _extract_name_from_row(row, name_col)
                            if not name:
                                continue
                            score = _extract_score_from_row(row, score_col)
                            if score is not None:
                                score_records.setdefault(name, score)
                                if current_province and name not in province_records:
                                    province_records[name] = current_province

                if has_wsa and has_wss:
                    wss_col = _find_wss_col(table, nrows=2)
                    if wss_col is not None:
                        for row in table[start:]:
                            name = _extract_name_from_row(row, name_col)
                            if not name:
                                continue
                            try:
                                # WSS count also suffers merged-cell offset
                                wss = None
                                for col in range(wss_col, min(len(row), wss_col + 3)):
                                    val = str(row[col] or "").strip().replace(",", "")
                                    if val.isdigit():
                                        wss = int(val)
                                        break
                            except (ValueError, TypeError):
                                continue
                            if wss and wss > 0:
                                wss_records.setdefault(name, wss)
                                if current_province and name not in province_records:
                                    province_records[name] = current_province

                # continuation tables (split across page breaks — no header row)
                elif current_province and not has_score:
                    data_rows = [r for r in table if _looks_like_data_row(r)]
                    if len(data_rows) >= max(2, len(table) // 2):
                        for row in data_rows:
                            name = _extract_name_from_row(row, 0)
                            if not name:
                                continue
                            score = None
                            for cell in reversed(row):
                                score = _extract_pct(str(cell or ""))
                                if score is not None:
                                    break
                            if score is not None:
                                score_records.setdefault(name, score)
                                if name not in province_records:
                                    province_records[name] = current_province

    records = [
        {
            "name": name,
            "province": province_records.get(name),
            "blue_drop_score": score,
            "bd_certification": _classify_bd(score),
            "num_water_supply_systems": wss_records.get(name),
        }
        for name, score in score_records.items()
    ]

    return pd.DataFrame(records).drop_duplicates(subset=["name"])
