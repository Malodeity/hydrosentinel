from pathlib import Path

import pandas as pd
import requests

from etl.name_matching import match_to_known_names, normalize_name

# recommended maintenance-to-asset-value benchmark from National Treasury
MAINT_BENCHMARK_PCT = 8.0

API_BASE = "https://municipaldata.treasury.gov.za/api"

# repairs_maintenance_facts_v2 has no single "total" line item — sum the 4 leaf items
_MAINT_ITEM_CODES = ["6001", "6002", "6003", "6004"]
_TOTAL_EXPENDITURE_ITEM = "4400"

# kept as a local alias so existing tests/imports of `_normalize` keep working
_normalize = normalize_name


def _fetch_item_totals(cube: str, item_codes: list[str], year: int) -> dict[str, float]:
    # sums amount.sum per demarcation code across the given item codes for
    # one municipal financial year, using audited actuals (the most reliable
    # amount_type available at year-level granularity)
    totals: dict[str, float] = {}
    for item_code in item_codes:
        resp = requests.get(
            f"{API_BASE}/cubes/{cube}/aggregate",
            params={
                "aggregates": "amount.sum",
                "cut": f'financial_year_end.year:{year}|period_length.length:"year"|amount_type.code:"AUDA"|item.code:"{item_code}"',
                "drilldown": "demarcation",
                "page_size": 500,
            },
            timeout=30,
        )
        resp.raise_for_status()
        for cell in resp.json().get("cells", []):
            code = cell["demarcation.code"]
            amount = cell.get("amount.sum") or 0.0
            totals[code] = totals.get(code, 0.0) + amount
    return totals


def _fetch_demarcation_labels(year: int) -> dict[str, str]:
    resp = requests.get(
        f"{API_BASE}/cubes/incexp_v2/aggregate",
        params={
            "aggregates": "amount.sum",
            "cut": f'financial_year_end.year:{year}|period_length.length:"year"|amount_type.code:"AUDA"|item.code:"{_TOTAL_EXPENDITURE_ITEM}"',
            "drilldown": "demarcation",
            "page_size": 500,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return {cell["demarcation.code"]: cell["demarcation.label"] for cell in resp.json().get("cells", [])}


def _build_finance_rows(labels: dict[str, str], maint: dict[str, float], opex: dict[str, float]) -> list[dict]:
    rows = []
    for code, label in labels.items():
        opex_total = opex.get(code)
        maint_total = maint.get(code)
        if not opex_total:
            continue

        pct = round((maint_total or 0.0) / opex_total * 100, 2)
        # audited actuals occasionally carry negative repairs & maintenance
        # entries (accounting reversals/corrections) — treat an out-of-range
        # ratio as unreliable rather than store a misleading number
        if not (0.0 <= pct <= 100.0):
            continue

        rows.append({
            "demarcation_code": code,
            "demarcation_label": label,
            "maint_expenditure": maint_total,
            "maint_pct": pct,
        })
    return rows


def fetch_municipal_finance(year: int = 2023) -> pd.DataFrame:
    """
    Fetches maintenance expenditure and total operating expenditure per
    municipality from National Treasury's Municipal Money API
    (https://municipaldata.treasury.gov.za/docs) and computes
    maint_pct = maintenance / total_expenditure * 100.

    Returns columns: demarcation_code, demarcation_label, maint_pct,
    maint_expenditure (in ZAR). asset_value is intentionally not included —
    the API's "TOTAL ASSETS" line item (financial_position_v2, item 0100) is
    a section header with no populated facts, not a real leaf value.
    """
    labels = _fetch_demarcation_labels(year)
    maint = _fetch_item_totals("repmaint_v2", _MAINT_ITEM_CODES, year)
    opex = _fetch_item_totals("incexp_v2", [_TOTAL_EXPENDITURE_ITEM], year)

    rows = _build_finance_rows(labels, maint, opex)
    return pd.DataFrame(rows, columns=["demarcation_code", "demarcation_label", "maint_pct", "maint_expenditure"])


def match_to_wsa_names(finance_df: pd.DataFrame, known_names: list[str]) -> pd.DataFrame:
    """
    Treasury's demarcation labels use yet another naming convention than the
    DWS report names already flowing through the rest of the ETL. See
    etl.name_matching.match_to_known_names for how the matching works — a
    source row that matches nothing is dropped, never turned into a new WSA.
    """
    finance_df = finance_df[["demarcation_label", "maint_pct", "maint_expenditure"]]
    matched = match_to_known_names(finance_df, "demarcation_label", known_names)
    return matched[["name", "maint_pct", "maint_expenditure"]]


def load_municipal_money(source_path: str | Path) -> pd.DataFrame:
    """
    Loads municipal finance data from a CSV or Excel file (fallback path for
    when a spreadsheet is supplied directly instead of the live API).

    Expected columns (flexible — any combination works):
      name             — municipality name, must match WSA name in the database
      maint_pct        — maintenance spend as % of asset value (direct)
      maint_expenditure — actual maintenance expenditure in ZAR
      asset_value       — total asset value in ZAR

    If maint_pct is absent but maint_expenditure and asset_value are both
    present, maint_pct is computed as (maint_expenditure / asset_value) * 100.
    """
    path = Path(source_path)
    if not path.exists():
        return pd.DataFrame(columns=["name", "maint_pct", "maint_expenditure", "asset_value"])

    frame = pd.read_csv(path) if path.suffix.lower() == ".csv" else pd.read_excel(path)

    if "name" not in frame.columns:
        raise ValueError("Municipal finance data is missing the required 'name' column")

    # compute maint_pct from raw financials when not directly supplied
    if "maint_pct" not in frame.columns:
        if "maint_expenditure" in frame.columns and "asset_value" in frame.columns:
            frame["maint_pct"] = (
                frame["maint_expenditure"] / frame["asset_value"].replace(0, float("nan")) * 100
            ).round(2)
        else:
            frame["maint_pct"] = None

    # ensure all output columns exist even when absent from the source file
    for col in ("maint_expenditure", "asset_value"):
        if col not in frame.columns:
            frame[col] = None

    output_cols = ["name", "maint_pct", "maint_expenditure", "asset_value"]
    return frame[output_cols].dropna(subset=["name"]).drop_duplicates(subset=["name"])
