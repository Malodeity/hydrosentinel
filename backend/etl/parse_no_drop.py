import re
from pathlib import Path

import pandas as pd
import pdfplumber


_PCT_RE = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%")


def _extract_pct(raw: str | None) -> float | None:
    if not raw:
        return None
    m = _PCT_RE.search(str(raw))
    return float(m.group(1)) if m else None


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


def _is_wsa_name(value: str | None) -> bool:
    if not value:
        return False
    v = value.strip()
    return len(v) > 3 and not v.upper().startswith("TOTAL") and not v.upper().startswith("WSA") and not v.upper().startswith("PROVINCE")


def parse_no_drop(pdf_path: str | Path) -> pd.DataFrame:
    """
    Extracts per-WSA NRW percent and No Drop performance category from the 2023
    No Drop Report PDF.

    Scans all pages for tables that contain:
      - A WSA / municipality name column
      - A score or NRW column expressed as a percentage

    The No Drop overall score is used to derive nd_performance. NRW % is stored
    directly as nrw_percent when found in a separate NRW-labelled column.
    """
    score_records: dict[str, float] = {}
    nrw_records: dict[str, float] = {}

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            if not tables:
                continue

            for table in tables:
                if not table or len(table) < 2:
                    continue

                header = table[0]
                header_text = " ".join(str(c or "").upper() for c in header)

                has_wsa_col = "WSA" in header_text or "MUNICIPALITY" in header_text or "NAME" in header_text
                if not has_wsa_col:
                    continue

                name_col = next(
                    (i for i, c in enumerate(header) if "WSA" in str(c or "").upper() or "MUNICIPALITY" in str(c or "").upper() or "NAME" in str(c or "").upper()),
                    0,
                )

                # skip a second header row if present
                data_start = 1
                if len(table) > 1:
                    first_data = table[1]
                    has_digits = any(
                        c and re.search(r"\d", str(c))
                        for c in first_data[1:]
                    )
                    if not has_digits:
                        data_start = 2

                # --- NRW column ---
                nrw_col = next(
                    (i for i, c in enumerate(header) if "NRW" in str(c or "").upper() or "NON-REVENUE" in str(c or "").upper() or "WATER LOSS" in str(c or "").upper()),
                    None,
                )

                # --- No Drop score column ---
                score_col = next(
                    (
                        i for i, c in enumerate(header)
                        if ("NO DROP" in str(c or "").upper() or "SCORE" in str(c or "").upper() or "CRITERIA" in str(c or "").upper())
                        and i != name_col
                    ),
                    None,
                )

                for row in table[data_start:]:
                    if not row or len(row) <= name_col:
                        continue
                    name = str(row[name_col] or "").strip()
                    if not _is_wsa_name(name):
                        continue

                    if nrw_col is not None and len(row) > nrw_col:
                        nrw = _extract_pct(str(row[nrw_col] or ""))
                        if nrw is not None:
                            nrw_records.setdefault(name, nrw)

                    if score_col is not None and len(row) > score_col:
                        score = _extract_pct(str(row[score_col] or ""))
                        if score is not None:
                            score_records.setdefault(name, score)

    # merge: prefer explicit NRW column; fall back to overall score as nrw proxy
    all_names = set(score_records) | set(nrw_records)
    records = [
        {
            "name": name,
            "nrw_percent": nrw_records.get(name),
            "nd_performance": _classify_nd(score_records.get(name)),
        }
        for name in all_names
    ]

    return pd.DataFrame(records).drop_duplicates(subset=["name"])
