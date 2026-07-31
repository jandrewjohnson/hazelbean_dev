"""Unit tests for hazelbean.initialize_definitions.initialize_definitions_csv.

These pin down the resolution order (existing path -> input_template/ -> base_data
default_inputs -> raise) and, importantly, the fixed bug: the old per-project copies
referenced `possible_path` before it was assigned, so a truly-missing definitions
file raised NameError instead of the intended clean Exception. The
test_raises_when_missing_everywhere case guards that fix.

The scaffold is intentionally decoupled from any real ProjectFlow: it only needs a
small object exposing <stem>_definitions_path, <stem>_definitions_filename,
script_dir, and a get_path(module, kind, filename) method. We fake that here.
"""

import os

import pandas as pd
import pytest

import hazelbean as hb


class FakeProjectFlow:
    """Minimal stand-in for a ProjectFlow `p` for the bits the scaffold touches."""

    def __init__(self, root, stem, filename, base_data_path):
        # Where the project expects its definitions csv to live (initially absent).
        self.script_dir = os.path.join(root, "script")
        self.input_dir = os.path.join(root, "input")
        os.makedirs(self.script_dir, exist_ok=True)
        os.makedirs(self.input_dir, exist_ok=True)

        setattr(self, f"{stem}_definitions_path", os.path.join(self.input_dir, filename))
        setattr(self, f"{stem}_definitions_filename", filename)

        # What p.get_path(...) should return for the base_data default_inputs lookup.
        self._base_data_path = base_data_path

    def get_path(self, module, kind, filename):
        return self._base_data_path


def _write_csv(path, value="from_this_source"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pd.DataFrame([{"marker_col": value, "res": 300}]).to_csv(path, index=False)
    return path


def _recording_assign_fn():
    calls = {}

    def assign_fn(p, df):
        calls["df"] = df
        # Mimic real assigners: hydrate p from row 0.
        for col in df.columns:
            setattr(p, col, df.iloc[0][col])

    return assign_fn, calls


def test_loads_existing_csv(temp_dir):
    """If the definitions csv already exists, it is read and assign_fn is called."""
    p = FakeProjectFlow(temp_dir, "parameter", "myproj_parameters.csv", base_data_path="/does/not/exist.csv")
    _write_csv(p.parameter_definitions_path, value="already_here")

    assign_fn, calls = _recording_assign_fn()
    df = hb.initialize_definitions_csv(p, "parameter", "gtappy", assign_fn)

    assert calls["df"] is not None
    assert df.iloc[0]["marker_col"] == "already_here"
    assert p.parameters_df.iloc[0]["marker_col"] == "already_here"
    assert p.marker_col == "already_here"  # hydrated onto p


def test_copies_from_input_template(temp_dir):
    """Missing csv is sourced from <script_dir>/input_template/ before base_data."""
    filename = "myproj_scenarios.csv"
    p = FakeProjectFlow(temp_dir, "scenario", filename, base_data_path="/does/not/exist.csv")
    # Definitions path is absent; an input_template copy exists.
    template_path = os.path.join(p.script_dir, "input_template", filename)
    _write_csv(template_path, value="from_template")

    assign_fn, calls = _recording_assign_fn()
    df = hb.initialize_definitions_csv(p, "scenario", "gtappy", assign_fn)

    assert hb.path_exists(p.scenario_definitions_path)  # got copied into place
    assert df.iloc[0]["marker_col"] == "from_template"
    assert p.scenarios_df.iloc[0]["marker_col"] == "from_template"


def test_copies_from_base_data_default_inputs(temp_dir):
    """Missing csv with no input_template falls back to base_data default_inputs."""
    filename = "myproj_outputs.csv"
    base_data_path = os.path.join(temp_dir, "base_data", filename)
    _write_csv(base_data_path, value="from_base_data")

    p = FakeProjectFlow(temp_dir, "output", filename, base_data_path=base_data_path)

    assign_fn, calls = _recording_assign_fn()
    df = hb.initialize_definitions_csv(p, "output", "gtap_invest", assign_fn)

    assert hb.path_exists(p.output_definitions_path)
    assert df.iloc[0]["marker_col"] == "from_base_data"
    assert p.outputs_df.iloc[0]["marker_col"] == "from_base_data"


def test_raises_when_missing_everywhere(temp_dir):
    """Regression for the possible_path-before-assignment bug.

    With no csv at the path, no input_template, and a non-existent base_data path,
    the scaffold must raise a clean Exception (not NameError).
    """
    p = FakeProjectFlow(temp_dir, "parameter", "missing.csv", base_data_path="/does/not/exist.csv")

    assign_fn, _ = _recording_assign_fn()
    with pytest.raises(Exception) as excinfo:
        hb.initialize_definitions_csv(p, "parameter", "gtappy", assign_fn)

    assert not isinstance(excinfo.value, NameError)
    assert "missing.csv" in str(excinfo.value)


def test_derives_path_from_input_dir(temp_dir):
    """When no explicit *_definitions_path is set, it is derived from p.input_dir."""
    filename = "derived_parameters.csv"

    class FakeWithoutPath:
        def __init__(self, root):
            self.script_dir = os.path.join(root, "script")
            self.input_dir = os.path.join(root, "input")
            os.makedirs(self.script_dir, exist_ok=True)
            os.makedirs(self.input_dir, exist_ok=True)
            self.parameter_definitions_filename = filename
            # NOTE: parameter_definitions_path is intentionally NOT set.

        def get_path(self, module, kind, fname):
            return "/does/not/exist.csv"

    p = FakeWithoutPath(temp_dir)
    _write_csv(os.path.join(p.input_dir, filename), value="derived_ok")

    assign_fn, _ = _recording_assign_fn()
    df = hb.initialize_definitions_csv(p, "parameter", "gtappy", assign_fn)

    assert df.iloc[0]["marker_col"] == "derived_ok"
    # The derived path is recorded back onto p.
    assert p.parameter_definitions_path == os.path.join(p.input_dir, filename)


def test_post_process_hook_runs(temp_dir):
    """post_process(p) is invoked after assignment when provided."""
    p = FakeProjectFlow(temp_dir, "scenario", "s.csv", base_data_path="/no.csv")
    _write_csv(p.scenario_definitions_path)

    assign_fn, _ = _recording_assign_fn()
    flag = {}

    def post_process(p):
        flag["ran"] = True

    hb.initialize_definitions_csv(p, "scenario", "gtappy", assign_fn, post_process=post_process)
    assert flag.get("ran") is True


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
