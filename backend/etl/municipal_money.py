from pathlib import Path

import pandas as pd


# recommended maintenance-to-asset-value benchmark from National Treasury
MAINT_BENCHMARK_PCT = 8.0


def load_municipal_money(source_path: str | Path) -> pd.DataFrame:
    """
    Loads municipal finance data from a CSV or Excel file.

    Expected columns (flexible — any combination works):
      name             — municipality name, must match WSA name in the database
      maint_pct        — maintenance spend as % of asset value (direct)
      maint_expenditure — actual maintenance expenditure in ZAR
      asset_value       — total asset value in ZAR

    If maint_pct is absent but maint_expenditure and asset_value are both
    present, maint_pct is computed as (maint_expenditure / asset_value) * 100.

    This loader is designed for CSV input now and for a future Municipal Money
    API integration — the API response should be normalised to these same column
    names before passing to this function.
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
