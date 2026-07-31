"""One value-parser, two CSV orientations.

Across gtappy, gtap_invest and seals there were four near-duplicate functions that
hydrate a ProjectFlow `p` from a definitions csv:

    gtappy_utils.assign_df_cols_to_object_attributes   (vertical / key+value)
    gtappy_utils.assign_df_row_to_object_attributes    (row / columns-are-attrs)
    seals_api_parsing.assign_df_row_to_object_attributes
    seals_utils.assign_df_row_to_object_attributes

They split along TWO axes that had gotten tangled together:

  1. ORIENTATION -- a real, semantic difference in the *input*:
       * vertical / 1-dim: columns are `key, value`; the whole file describes ONE
         namespace. There is no entity to iterate. Used for `*parameters*` files.
       * row / 2-dim: columns ARE the attribute names; each row is one entity
         (a scenario, an output). Iterated at run-time; row 0 used at init.
     These two are the same operation under a transpose: a vertical file is just a
     name->value mapping written down the page instead of across it. So orientation
     is a *normalization* step, not a parsing step.

  2. VALUE GRAMMAR -- which had drifted only by accident (cat-ears handling present
     in seals but not gtappy; explicit [list]/{dict} literals present in gtappy's
     vertical parser but not the row parsers; three different path-detection rules).
     There is no good reason a *parameter* can't be a path or a cat-ear reference,
     or that a *scenario* column can't hold a list. So the grammar is unified here
     and BOTH orientations get all of it.

This module owns the unified grammar (`parse_attribute_value`) and the orientation
dispatcher (`assign_df_to_object_attributes`, auto-detect with a stem fallback).
The genuinely project-specific tail logic -- SEALS' `seals_years` override and the
`model_spec` defaults -- is intentionally NOT here; it stays in each project's thin
shim, exactly as initialize_definitions.py argues for post_process hooks.

Reconciliation decisions (where the four originals disagreed):
  * Path detection: the originals used three rules -- gtappy's `'.' in value[-5:-1]`
    (an extension test that silently FAILS for >4-char extensions like .geojson),
    and seals' `'.' in value` (treats any dotted string as a path). First unified to
    an anchored extension regex OR a path separator; since 2026-07-24 hydration is
    NAME-driven instead (`*_path` columns resolve, everything else stays literal),
    because no value heuristic can separate ssh targets (user@192.168.64.2),
    backend-machine paths (C:\\GP) or free text (Expansion/Loss) from local ref
    paths. The value heuristic survives as the public `looks_like_path` for
    consumers of value-conditional columns (aoi, calibration_parameters_source).
  * gtappy's row parser ran `hb.parse_flex_to_python_object` as a pre-pass; the
    seals parsers did not. Dropped in favor of explicit [list]/{dict} literal
    parsing, which is the part that actually mattered and now applies to both
    orientations. (gtappy callers: verify nothing relied on the implicit coercion.)
  * seals_utils' standalone `elif has_cat_ears:` branch is subsumed: cat-ears are
    resolved up front, so the plain branch sets the resolved value anyway.
"""

import re

import pandas as pd

import hazelbean as hb

# A trailing ".ext" of 1-8 alphanumerics. Anchored to the end so "1.5" style
# decimals (already excluded by the is_floatable guard) and mid-string dots don't
# trip it, while long real extensions (.geojson, .parquet) still match.
_PATH_EXTENSION_RE = re.compile(r"\.[A-Za-z0-9]{1,8}$")


def _is_intable(value):
    try:
        int(value)
        return True
    except (ValueError, TypeError):
        return False


def looks_like_path(value):
    """Value-based path heuristic: a path separator or a trailing .ext.

    Since 2026-07-24 this no longer drives hydration -- `parse_attribute_value`
    resolves paths by NAME (`*_path` columns), because no value heuristic can
    separate an ssh target (user@192.168.64.2), a backend-machine path (C:\\GP)
    or free text ('Expansion/Loss') from a local ref path. It stays public for
    consumers of value-conditional columns whose values are only SOMETIMES paths
    (e.g. aoi, calibration_parameters_source): gate on looks_like_path(value),
    then resolve with get_path(..., leave_ref_path_if_fail=True).
    """
    s = str(value).strip()
    if s == "" or s.lower() == "nan" or s == "skip":
        return False
    if "/" in s or "\\" in s:
        return True
    return bool(_PATH_EXTENSION_RE.search(s))


def _cast_scalar_token(token):
    """`int(3)` -> 3, `float(2.5)` -> 2.5, otherwise the stripped string token."""
    token = token.strip()
    if token.startswith("int(") and token.endswith(")"):
        return int(token[4:-1])
    if token.startswith("float(") and token.endswith(")"):
        return float(token[6:-1])
    return token


def _parse_list_literal(value):
    inner = value.strip()[1:-1]
    if inner.strip() == "":
        return []
    return [_cast_scalar_token(tok) for tok in inner.split(",")]


def _parse_dict_literal(value):
    inner = value.strip()[1:-1]
    out = {}
    if inner.strip() == "":
        return out
    for entry in inner.split(","):
        key, raw = entry.split(":", 1)
        out[key.strip()] = _cast_scalar_token(raw)
    return out


def _parse_year(value, attribute_name, is_intable):
    if " " in str(value):
        parsed = []
        for token in str(value).split(" "):
            try:
                parsed.append(int(token))
            except ValueError:
                parsed.append(str(token))
        return parsed
    if is_intable:
        if attribute_name == "key_base_year":
            return int(value)
        if isinstance(value, list):
            return value
        return [int(value)]
    if "lulc" in attribute_name:
        return str(value)
    if "nan" in str(value):
        return None
    try:
        return [int(value)]
    except ValueError:
        return [str(value)]


def _parse_dimensions(value):
    if " " in str(value):
        return [str(i) if "nan" not in str(i) else None for i in str(value).split(" ")]
    if "nan" in str(value):
        return None
    return [str(value)]


def parse_attribute_value(input_object, attribute_name, attribute_value):
    """Apply the unified value grammar to a single (name, value) pair.

    Returns the parsed value to be assigned. The grammar, in precedence order:
        1. cat-ears (`<^attr^>`) resolved against `input_object`'s attributes
        2. explicit `[list]` literal (with `int(...)`/`float(...)` token casts)
        3. explicit `{dict}` literal
        4. `*_path`-named column -> `input_object.get_path(...)` (name-driven,
           per the EE Spec convention that path-bearing columns are named *_path;
           blank/'skip' pass through, 'nan' -> None)
        5. `*year*`-named column -> int / space-delimited list-of-int parsing
        6. `*dimensions*`-named column -> space-delimited list-of-str parsing
        7. literal 'nan' -> None; otherwise the value unchanged
    """
    value = attribute_value
    is_intable = _is_intable(value)

    # 1. cat-ears: resolve placeholders against already-set attributes (seals_utils
    # semantics: trigger on a cat-ear in EITHER the name or the value).
    has_cat_ears = hb.has_cat_ears(attribute_name) or hb.has_cat_ears(value)
    if has_cat_ears:
        value = hb.replace_cat_ears_with_object_attributes(value, input_object)

    # 2 / 3. explicit container literals (previously vertical-only; now both).
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            return _parse_list_literal(value)
        if stripped.startswith("{") and stripped.endswith("}"):
            return _parse_dict_literal(value)

    # 4. paths -- name-driven since 2026-07-24 (was value-driven, which get_path'd
    # anything dotted or slashed: ssh targets, backend-machine paths, free text).
    # Checked before year/dimensions so e.g. base_year_lulc_path (name contains
    # 'year') still resolves as a path. Columns whose values are only sometimes
    # paths (aoi, calibration_parameters_source) resolve at their consumers via
    # the public looks_like_path + get_path(leave_ref_path_if_fail=True).
    if str(attribute_name).endswith("_path"):
        if not isinstance(value, str):
            return None if str(value).lower() == "nan" else value
        stripped = value.strip()
        if stripped == "" or stripped == "skip":
            return value
        if stripped.lower() == "nan":
            return None
        if has_cat_ears:
            return input_object.get_path(stripped, leave_ref_path_if_fail=True)
        return input_object.get_path(stripped)

    if "year" in attribute_name:
        return _parse_year(value, attribute_name, is_intable)

    if "dimensions" in attribute_name:
        return _parse_dimensions(value)

    if str(value).lower() == "nan":
        return None
    return value


def assign_row_to_object_attributes(input_object, input_row):
    """Hydrate `input_object` from a single name->value mapping (a df row Series)."""
    for attribute_name, attribute_value in zip(input_row.index, input_row.values):
        parsed = parse_attribute_value(input_object, attribute_name, attribute_value)
        setattr(input_object, attribute_name, parsed)


def assign_cols_to_object_attributes(input_object, df, key_col="key", value_col="value"):
    """Hydrate from a vertical (key/value) df by transposing it into one mapping."""
    series = pd.Series(df[value_col].values, index=df[key_col].values)
    assign_row_to_object_attributes(input_object, series)


def assign_defaults_from_model_spec(input_object, model_spec_dict):
    """Set any attribute named in `model_spec_dict` that isn't already present."""
    for key, default_value in model_spec_dict.items():
        if not hasattr(input_object, key):
            setattr(input_object, key, default_value)


def detect_orientation(df, orientation="auto", stem=None):
    """'vertical' or 'row'. Auto-detect from columns, fall back to the stem.

    A df carrying both a `key` and a `value` column is unambiguously vertical.
    Otherwise fall back to the stem: `parameter` files are vertical, everything
    else (scenario, output, ...) is row-oriented.
    """
    if orientation in ("vertical", "row"):
        return orientation
    cols = {str(c).strip().lower() for c in df.columns}
    if "key" in cols and "value" in cols:
        return "vertical"
    if stem == "parameter":
        return "vertical"
    return "row"


def assign_df_to_object_attributes(input_object, df, orientation="auto", stem=None):
    """Unified entry point: detect orientation, then hydrate `input_object`.

    For row-oriented data this hydrates from row 0 (the initialization use). Callers
    that iterate scenarios/outputs should call `assign_row_to_object_attributes`
    per row directly.
    """
    if detect_orientation(df, orientation, stem) == "vertical":
        assign_cols_to_object_attributes(input_object, df)
    else:
        assign_row_to_object_attributes(input_object, df.iloc[0])
