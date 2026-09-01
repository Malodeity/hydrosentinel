import re

import pandas as pd

# a handful of metros have structurally different names across sources than
# the DWS report names already in the WSA table (e.g. "Cape Town" vs
# "City of Cape Town") — suffix stripping alone doesn't bridge these
METRO_ALIASES: dict[str, list[str]] = {
    "cape town": ["city of cape town"],
    "ethekwini": ["ethekwini metropolitan municipality", "durban"],
    "city of ekurhuleni": ["ekurhuleni"],
    "city of johannesburg": ["johannesburg"],
    "city of tshwane": ["tshwane"],
    "mangaung": ["mangaung metropolitan municipality"],
    "nelson mandela bay": ["nelson mandela bay metropolitan municipality", "nelson mandela bay metropolitan"],
}

_SUFFIX_RE = re.compile(
    r"\b(local municipality|district municipality|metropolitan municipality|metropolitan)\b|\b(DM|LM|MM)\b",
    re.IGNORECASE,
)


def normalize_name(name: str) -> str:
    cleaned = _SUFFIX_RE.sub("", name)
    cleaned = re.sub(r"[^a-z0-9 ]", "", cleaned.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def match_to_known_names(frame: pd.DataFrame, label_column: str, known_names: list[str]) -> pd.DataFrame:
    """
    Different sources spell the same municipality differently (district
    labels dropping a "DM" suffix, metros diverging structurally). Rather
    than let a name mismatch silently create a brand-new, coordinate-less
    WSA row, this expands each source row into one row per already-known
    WSA name that normalizes to the same municipality, dropping the row
    entirely when nothing matches — so a new source can only ever attach
    data to a WSA that already exists, never invent a duplicate.

    `label_column` is replaced by "name" in the output; every other column
    is preserved as-is on each expanded row.
    """
    norm_to_names: dict[str, list[str]] = {}
    for name in known_names:
        norm_to_names.setdefault(normalize_name(name), []).append(name)

    other_columns = [c for c in frame.columns if c != label_column]
    rows = []
    for _, source_row in frame.iterrows():
        label_norm = normalize_name(str(source_row[label_column]))
        candidate_norms = {label_norm, *(normalize_name(a) for a in METRO_ALIASES.get(label_norm, []))}

        matched_names: set[str] = set()
        for norm in candidate_norms:
            matched_names.update(norm_to_names.get(norm, []))

        for wsa_name in matched_names:
            row = {"name": wsa_name}
            for col in other_columns:
                row[col] = source_row[col]
            rows.append(row)

    return pd.DataFrame(rows, columns=["name", *other_columns])
