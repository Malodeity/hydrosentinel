"""
The national Green Drop report wraps some municipality names across two
table cells (e.g. "Mogalakwena\\nLM"). Left unnormalized, that name never
matches the WSA already in the database and the score silently drops —
3 of 85 rows in the real national report hit this before the fix.
"""
from etl.parse_green_drop import _extract_pct, _is_wsa_name, _normalize_cell


def test_normalize_cell_joins_wrapped_name_with_space():
    assert _normalize_cell("Mogalakwena\nLM") == "Mogalakwena LM"


def test_normalize_cell_handles_multiple_wraps():
    assert _normalize_cell("Dr Ruth\nMompati DM") == "Dr Ruth Mompati DM"


def test_normalize_cell_handles_none():
    assert _normalize_cell(None) == ""


def test_normalize_cell_passes_through_unwrapped_name():
    assert _normalize_cell("Chris Hani DM") == "Chris Hani DM"


def test_is_wsa_name_accepts_normalized_wrapped_name():
    assert _is_wsa_name("Mogalakwena LM") is True


def test_is_wsa_name_rejects_short_fragment():
    # the un-normalized second half of a wrapped cell, e.g. "LM" alone
    assert _is_wsa_name("LM") is False


def test_is_wsa_name_rejects_garbage_tokens():
    assert _is_wsa_name("TOTAL") is False
    assert _is_wsa_name("Table 4: Green Drop scores") is False


def test_extract_pct_finds_percentage():
    assert _extract_pct("26.0%") == 26.0
    assert _extract_pct("Score: 44%") == 44.0


def test_extract_pct_returns_none_for_no_match():
    assert _extract_pct("no score here") is None
    assert _extract_pct(None) is None
