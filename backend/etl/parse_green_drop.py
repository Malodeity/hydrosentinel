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


_GARBAGE_TOKENS = (
    "DURING THE AUDIT", "IN SUCH CASES", "WHERE A SYSTEM", "TABLE", "FIGURE",
    "DIAGNOSTIC", "PROVINCE", "NATIONAL", "PERFORMANCE", "BLUE DROP", "GREEN DROP",
    "TOTAL", "SUBTOTAL", "WATER BOARD",
)


def _is_wsa_name(value: str | None) -> bool:
    if not value:
        return False
    v = value.strip()
    if len(v) < 4 or len(v) > 80:
        return False
    if v[0].isdigit():
        return False
    upper = v.upper()
    if any(upper.startswith(g) for g in _GARBAGE_TOKENS):
        return False
    if v.count(".") > 1 or v.count(",") > 3:
        return False
    return True


def parse_green_drop(pdf_path: str | Path) -> pd.DataFrame:
    """
    Extracts per-WSA Green Drop scores from a provincial Green Drop Report PDF
    (e.g. GD25 Report_Gauteng_Rev01_29Mar26.pdf).

    Only Gauteng WSAs are available in the current source file; scores for other
    provinces will remain null until the national Green Drop 2025 report is released.

    The GD25 report has multi-row headers; the score column is identified by
    "GD" + "Score" appearing in the first header row. Because pdfplumber flattens
    multi-row headers, the score is usually the last percentage value in each row.
    """
    records: dict[str, float] = {}

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

                # must contain a WSA/name column and a GD score column
                has_wsa = "WSA" in header_text or "MUNICIPALITY" in header_text or "NAME" in header_text
                has_gd_score = ("GD" in header_text or "GREEN DROP" in header_text) and "SCORE" in header_text
                if not has_wsa or not has_gd_score:
                    continue

                name_col = next(
                    (i for i, c in enumerate(header) if "WSA" in str(c or "").upper() or "NAME" in str(c or "").upper()),
                    0,
                )

                # try to locate score column explicitly; GD reports often put it last
                score_col = next(
                    (
                        i for i, c in enumerate(header)
                        if ("GD" in str(c or "").upper() or "GREEN DROP" in str(c or "").upper())
                        and "SCORE" in str(c or "").upper()
                    ),
                    None,
                )

                # skip second header row if present (multi-row headers in GD25)
                data_start = 1
                if len(table) > 1:
                    has_digits = any(c and re.search(r"\d", str(c)) for c in table[1][1:])
                    if not has_digits:
                        data_start = 2

                for row in table[data_start:]:
                    if not row:
                        continue
                    name = str(row[name_col] or "").strip()
                    if not _is_wsa_name(name):
                        continue

                    score: float | None = None

                    # try explicit score column first
                    if score_col is not None and len(row) > score_col:
                        score = _extract_pct(str(row[score_col] or ""))

                    # fall back: find the last percentage value in the row
                    if score is None:
                        for cell in reversed(row):
                            score = _extract_pct(str(cell or ""))
                            if score is not None:
                                break

                    if score is not None:
                        records.setdefault(name, score)

    if not records:
        return pd.DataFrame(columns=["name", "green_drop_score"])

    return pd.DataFrame(
        [{"name": name, "green_drop_score": score} for name, score in records.items()]
    ).drop_duplicates(subset=["name"])
