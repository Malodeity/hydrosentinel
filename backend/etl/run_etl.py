from pathlib import Path

import pandas as pd

from etl.load import merge_sources, upsert_wsa_rows
from etl.municipal_money import load_municipal_money
from etl.parse_blue_drop import parse_blue_drop
from etl.parse_green_drop import parse_green_drop
from etl.parse_no_drop import parse_no_drop

RAW_DIR = Path("data/raw")


def parse_first_matching(pattern: str, parser) -> pd.DataFrame:
    matches = sorted(RAW_DIR.glob(pattern))
    if not matches:
        return pd.DataFrame()
    return parser(matches[0])


def main() -> None:
    blue_drop = parse_first_matching("*blue*.pdf", parse_blue_drop)
    no_drop = parse_first_matching("*no_drop*.pdf", parse_no_drop)

    # green drop: scan for any provincial GD25 report
    # note: dws_cap_status is NOT populated here — the Green Drop Watch Report
    # only provides system-level CAP data, not per-WSA. That field will be
    # filled once the national Green Drop 2025 report with per-WSA data is available.
    green_drop = parse_first_matching("*green*.pdf", parse_green_drop)

    money_source = next(iter(sorted(RAW_DIR.glob("municipal_money.*"))), None)
    money = load_municipal_money(money_source) if money_source else pd.DataFrame()

    merged = merge_sources(blue_drop, no_drop, green_drop, money)
    if merged.empty:
        print("ETL complete: no source files found in data/raw/ — nothing to upsert")
        return

    row_count = upsert_wsa_rows(merged)
    print(f"ETL complete: upserted {row_count} WSA rows")


if __name__ == "__main__":
    main()
