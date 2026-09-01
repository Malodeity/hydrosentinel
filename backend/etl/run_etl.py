from pathlib import Path

import pandas as pd

from etl.load import merge_sources, upsert_wsa_rows
from etl.municipal_money import fetch_municipal_finance, load_municipal_money, match_to_wsa_names
from etl.name_matching import match_to_known_names
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
    # blue_drop, no_drop, and bdrr are DWS's own per-WSA audits and establish
    # the canonical WSA name universe. Every other source (green drop,
    # municipal money) is matched against names already known from these —
    # never outer-joined raw — so a spelling variant can only ever attach
    # data to an existing WSA, never spawn a coordinate-less duplicate.
    blue_drop = parse_first_matching("*blue*.pdf", parse_blue_drop)
    no_drop = parse_first_matching("*no_drop*.pdf", parse_no_drop)
    bdrr = parse_first_matching("*bdn*.pdf", parse_bdrr)

    # municipal finance CSV/Excel takes priority when supplied directly;
    # otherwise fall back to the live Municipal Money API below
    money_source = next(iter(sorted(RAW_DIR.glob("municipal_money.*"))), None)
    money = load_municipal_money(money_source) if money_source else pd.DataFrame()

    merged = merge_sources(blue_drop, no_drop, pd.DataFrame(), money, bdrr)

    known_names = merged["name"].dropna().unique().tolist() if not merged.empty else []

    # green drop: merge every matching report (national Watch Report + any
    # provincial GD25 report), matched against already-known WSA names —
    # provincial file wins on overlap since it's more targeted/recent.
    # note: dws_cap_status is NOT populated here — these reports only
    # provide system-level CAP data, not per-WSA.
    green_drop_matched_count = 0
    if known_names:
        green_drop = parse_all_green_drop_sources(known_names)
        if not green_drop.empty:
            merged = merged.merge(green_drop, on="name", how="left")
            green_drop_matched_count = len(green_drop)

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
    print(
        f"ETL complete: upserted {row_count} WSA rows "
        f"({green_drop_matched_count} matched against Green Drop, {api_matched_count} matched against the live Municipal Money API)"
    )


def parse_all_green_drop_sources(known_names: list[str]) -> pd.DataFrame:
    matches = sorted(RAW_DIR.glob("*green*.pdf"))
    if not matches:
        return pd.DataFrame()

    # process provincial reports last so their rows win the dedup below —
    # they're more targeted/recent for the WSAs they cover than the
    # national Watch Report
    matches.sort(key=lambda p: "gauteng" in p.name.lower())

    frames = [parse_green_drop(path) for path in matches]
    combined = pd.concat(frames, ignore_index=True).drop_duplicates(subset=["name"], keep="last")
    return match_to_known_names(combined, "name", known_names)


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
