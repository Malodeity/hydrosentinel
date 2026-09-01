from pathlib import Path

import pandas as pd

from etl.load import merge_sources, upsert_wsa_rows
from etl.municipal_money import fetch_municipal_finance, load_municipal_money, match_to_wsa_names
from etl.parse_bdrr import parse_bdrr
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

    # green drop: merge every matching report (national Watch Report +
    # any provincial GD25 report), with the provincial file's WSAs taking
    # precedence — it's the more targeted, more recent source for those.
    # note: dws_cap_status is NOT populated here — these reports only
    # provide system-level CAP data, not per-WSA.
    green_drop = parse_all_green_drop_sources()

    # municipal finance CSV/Excel takes priority when supplied directly;
    # otherwise fall back to the live Municipal Money API below
    money_source = next(iter(sorted(RAW_DIR.glob("municipal_money.*"))), None)
    money = load_municipal_money(money_source) if money_source else pd.DataFrame()

    # BDRR: DWS-audited ground-truth risk label, from the full national Blue
    # Drop report (not the smaller per-province summary already parsed above)
    bdrr = parse_first_matching("*bdn*.pdf", parse_bdrr)

    merged = merge_sources(blue_drop, no_drop, green_drop, money, bdrr)

    api_matched_count = 0
    if money.empty and not merged.empty:
        api_matched = _fetch_municipal_money_api(merged["name"].dropna().unique().tolist())
        if not api_matched.empty:
            merged = merged.merge(api_matched, on="name", how="left")
            api_matched_count = len(api_matched)

    if merged.empty:
        print("ETL complete: no source files found in data/raw/ — nothing to upsert")
        return

    row_count = upsert_wsa_rows(merged)
    print(f"ETL complete: upserted {row_count} WSA rows ({api_matched_count} matched against the live Municipal Money API)")


def parse_all_green_drop_sources() -> pd.DataFrame:
    matches = sorted(RAW_DIR.glob("*green*.pdf"))
    if not matches:
        return pd.DataFrame()

    # process provincial reports last so their rows win the dedup below —
    # they're more targeted/recent for the WSAs they cover than the
    # national Watch Report
    matches.sort(key=lambda p: "gauteng" in p.name.lower())

    frames = [parse_green_drop(path) for path in matches]
    combined = pd.concat(frames, ignore_index=True)
    return combined.drop_duplicates(subset=["name"], keep="last")


def _fetch_municipal_money_api(known_names: list[str]) -> pd.DataFrame:
    try:
        finance = fetch_municipal_finance()
    except Exception as exc:  # noqa: BLE001 — a network/API failure shouldn't abort the rest of the ETL run
        print(f"Municipal Money API fetch failed, skipping: {exc}")
        return pd.DataFrame()

    if finance.empty:
        return pd.DataFrame()
    return match_to_wsa_names(finance, known_names)


if __name__ == "__main__":
    main()
