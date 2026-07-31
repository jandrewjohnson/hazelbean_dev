"""Unit tests for hazelbean.assign_to_object -- the unified value-parser that
replaced the four divergent assign_df_*_to_object_attributes copies.

Covers: the merged value grammar (cat-ears, [list]/{dict} literals, path detection,
year/dimensions parsing, nan), the vertical<->row transpose equivalence, and
orientation auto-detection with the stem fallback.
"""

import pandas as pd
import pytest

import hazelbean as hb


class FakeP:
    """Minimal object: records get_path calls and resolves cat-ears against attrs."""

    def __init__(self, **attrs):
        for k, v in attrs.items():
            setattr(self, k, v)

    def get_path(self, p, **kwargs):
        # Mark resolution so tests can assert the path branch was taken.
        return "RESOLVED:" + str(p)


# --- merged value grammar -------------------------------------------------

def test_list_literal_with_casts():
    p = FakeP()
    assert hb.parse_attribute_value(p, "x", "[a, int(2), float(3.5)]") == ["a", 2, 3.5]


def test_dict_literal_with_casts():
    p = FakeP()
    assert hb.parse_attribute_value(p, "x", "{k: int(1), j: hello}") == {"k": 1, "j": "hello"}


def test_empty_list_literal():
    p = FakeP()
    assert hb.parse_attribute_value(p, "x", "[]") == []


@pytest.mark.parametrize("value", ["data/file.tif", "a/b/c.geojson", "thing.parquet"])
def test_path_detection_resolves(value):
    p = FakeP()
    assert hb.parse_attribute_value(p, "some_path", value) == "RESOLVED:" + value


def test_long_extension_is_a_path():
    # gtappy's old [-5:-1] test silently FAILED for >4-char extensions. Regression guard.
    # Since hydration went name-driven (2026-07-24) the value heuristic lives in
    # looks_like_path, and parse_attribute_value resolves only *_path-named attributes.
    p = FakeP()
    assert hb.looks_like_path("x.geojson")
    assert hb.parse_attribute_value(p, "out_path", "x.geojson").startswith("RESOLVED:")


def test_floatable_is_not_a_path():
    p = FakeP()
    assert hb.parse_attribute_value(p, "rate", "3.14") == "3.14"


def test_year_space_delimited():
    p = FakeP()
    assert hb.parse_attribute_value(p, "years", "2017 2020 2030") == [2017, 2020, 2030]


def test_year_single_becomes_list():
    p = FakeP()
    assert hb.parse_attribute_value(p, "years", "2017") == [2017]


def test_key_base_year_stays_scalar():
    p = FakeP()
    assert hb.parse_attribute_value(p, "key_base_year", "2017") == 2017


def test_path_wins_over_year_name():
    # base_year_lulc_path contains 'year' but is a path; path must be checked first.
    p = FakeP()
    assert hb.parse_attribute_value(p, "base_year_lulc_path", "a/b.tif").startswith("RESOLVED:")


def test_dimensions_split():
    p = FakeP()
    assert hb.parse_attribute_value(p, "dimensions", "lat lon time") == ["lat", "lon", "time"]


def test_nan_becomes_none():
    p = FakeP()
    assert hb.parse_attribute_value(p, "x", "nan") is None


def test_plain_string_passthrough():
    p = FakeP()
    assert hb.parse_attribute_value(p, "label", "ssp2_rcp45") == "ssp2_rcp45"


def test_cat_ears_resolved_against_object():
    p = FakeP(region="ssp2")
    # value has cat-ears but is otherwise a plain string -> resolved, then passthrough.
    assert hb.parse_attribute_value(p, "label", "<^region^>_scenario") == "ssp2_scenario"


# --- orientation: transpose equivalence + auto-detect ---------------------

def test_vertical_and_row_are_transpose_equivalent():
    vertical = pd.DataFrame({"key": ["years", "label"], "value": ["2017 2020", "base"]})
    row = pd.DataFrame([{"years": "2017 2020", "label": "base"}])

    p_v = FakeP()
    hb.assign_cols_to_object_attributes(p_v, vertical)
    p_r = FakeP()
    hb.assign_row_to_object_attributes(p_r, row.iloc[0])

    assert p_v.years == p_r.years == [2017, 2020]
    assert p_v.label == p_r.label == "base"


def test_detect_orientation_from_columns():
    vertical = pd.DataFrame({"key": ["a"], "value": ["b"]})
    row = pd.DataFrame([{"scenario_label": "x", "years": "2017"}])
    assert hb.detect_orientation(vertical) == "vertical"
    assert hb.detect_orientation(row) == "row"


def test_detect_orientation_stem_fallback():
    # A df without key/value columns falls back to the stem.
    ambiguous = pd.DataFrame([{"foo": "1", "bar": "2"}])
    assert hb.detect_orientation(ambiguous, stem="parameter") == "vertical"
    assert hb.detect_orientation(ambiguous, stem="scenario") == "row"


def test_detect_orientation_explicit_override():
    row = pd.DataFrame([{"scenario_label": "x"}])
    assert hb.detect_orientation(row, orientation="vertical") == "vertical"


def test_assign_df_dispatches_vertical():
    vertical = pd.DataFrame({"key": ["years"], "value": ["2017 2020"]})
    p = FakeP()
    hb.assign_df_to_object_attributes(p, vertical)
    assert p.years == [2017, 2020]


def test_assign_df_dispatches_row_via_stem():
    df = pd.DataFrame([{"years": "2017 2020"}, {"years": "2040"}])
    p = FakeP()
    hb.assign_df_to_object_attributes(p, df, stem="scenario")
    # row mode hydrates from row 0
    assert p.years == [2017, 2020]
