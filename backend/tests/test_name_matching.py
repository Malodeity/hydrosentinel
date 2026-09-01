"""
A real incident this module exists to prevent: the Green Drop national
report used spelling variants ("Blue Crane LM", "Mangaung LM") that didn't
match any existing WSA, so the ETL's outer-join silently created 11 brand
new WSA rows with no coordinates -- they rendered stacked on Null Island
(0,0) in the Gulf of Guinea. Every one of them turned out to be a duplicate
of a WSA that already existed correctly under a different name spelling.
match_to_known_names must never let an unmatched name create new data --
only attach to WSAs that already exist.
"""
import pandas as pd

from etl.name_matching import match_to_known_names, normalize_name


def test_normalize_name_strips_common_suffixes():
    assert normalize_name("Blue Crane Route LM") == "blue crane route"
    assert normalize_name("Mangaung Local Municipality") == "mangaung"


def test_match_to_known_names_drops_unmatched_row_instead_of_creating_one():
    # this is the exact incident: "Blue Crane LM" (Green Drop's spelling)
    # doesn't match "Blue Crane Route LM" (the WSA that already exists) --
    # it must be dropped, not turned into a new coordinate-less WSA
    frame = pd.DataFrame([{"name": "Blue Crane LM", "green_drop_score": 19.0}])
    known_names = ["Blue Crane Route LM", "Some Other WSA"]

    result = match_to_known_names(frame, "name", known_names)

    assert result.empty


def test_match_to_known_names_matches_when_suffix_variant_normalizes_the_same():
    frame = pd.DataFrame([{"name": "Mangaung LM", "green_drop_score": 40.0}])
    known_names = ["Mangaung Local Municipality"]

    result = match_to_known_names(frame, "name", known_names)

    assert len(result) == 1
    assert result.iloc[0]["name"] == "Mangaung Local Municipality"
    assert result.iloc[0]["green_drop_score"] == 40.0


def test_match_to_known_names_preserves_arbitrary_value_columns():
    frame = pd.DataFrame([{"name": "Chris Hani DM", "score_a": 1.0, "score_b": "x"}])
    result = match_to_known_names(frame, "name", ["Chris Hani DM"])

    assert list(result.columns) == ["name", "score_a", "score_b"]
    assert result.iloc[0]["score_b"] == "x"


def test_match_to_known_names_handles_empty_known_names():
    frame = pd.DataFrame([{"name": "Anything", "score": 1.0}])
    result = match_to_known_names(frame, "name", [])
    assert result.empty


def test_match_to_known_names_handles_empty_frame():
    result = match_to_known_names(pd.DataFrame(columns=["name", "score"]), "name", ["Some WSA"])
    assert result.empty
