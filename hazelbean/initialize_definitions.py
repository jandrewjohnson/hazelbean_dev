"""Centralized scaffolding for loading *_definitions.csv files into a ProjectFlow.

Across gtappy, gtap_invest, and seals the functions initialize_parameter_definitions,
initialize_scenario_definitions, and initialize_output_definitions were copy-pasted
and then drifted. The ONLY thing that legitimately varies between them is:

  - the attribute-name stem ('parameter' | 'scenario' | 'output'),
  - which base_data module to look in for a default copy ('gtappy' | 'gtap_invest' | ...),
  - the project-specific row parser (assign_fn), and
  - an optional post-processing hook (e.g. set_derived_attributes).

Everything else -- the path_exists -> input_template/ -> base_data default_inputs ->
read csv -> hydrate row 0 sequence -- is identical boilerplate that drifted only by
accident (including a latent bug where possible_path was referenced before assignment).

This module owns that boilerplate once, with the bug fixed. The genuinely
project-specific parsing (assign_fn / post_process) is intentionally NOT centralized:
those have diverged on purpose (seals_years override, cat-ears handling, per-project
derived attributes), so each project injects its own.

Naming convention assumed on the ProjectFlow object `p` (already followed everywhere):
    getattr(p, f'{stem}_definitions_filename')  e.g. p.parameter_definitions_filename  (required)
    getattr(p, f'{stem}_definitions_path')      e.g. p.parameter_definitions_path      (optional)
    setattr(p, f'{stem}s_df', ...)              e.g. p.parameters_df / p.scenarios_df / p.outputs_df

The path is optional: when it isn't set, it is derived as os.path.join(p.input_dir, filename)
and written back onto p, so run scripts only need to declare the filename.
"""

import os

import pandas as pd

import hazelbean as hb


def initialize_definitions_csv(p, stem, base_data_module, assign_fn, post_process=None):
    # THINKING OF ABANDING THIS AI SLOP
    """Ensure p's <stem>_definitions csv exists, load it, and hydrate p from row 0.

    Resolution order when the csv is missing at p.<stem>_definitions_path:
        1. <p.script_dir>/input_template/<filename>  (standalone-project template)
        2. base_data default_inputs via p.get_path(base_data_module, 'default_inputs', filename)
        3. otherwise raise.

    Args:
        p: ProjectFlow object.
        stem: 'parameter' | 'scenario' | 'output'. Drives the attribute names.
        base_data_module: module key passed to p.get_path for the default-inputs lookup,
            e.g. 'gtappy' or 'gtap_invest'.
        assign_fn: callable(p, df) that writes the definition row onto p. The project
            supplies this so its specific parsing stays local. Two common shapes:
                - column-based:  gtappy_utils.assign_df_cols_to_object_attributes  (takes (p, df))
                - row-based:     lambda p, df: seals_utils.assign_df_row_to_object_attributes(p, df.iloc[0])
            Both of those are now thin shims over the unified parser in
            hb.assign_to_object (one merged value grammar, shared by both orientations).
            New callers can skip assign_fn entirely and use
            hb.assign_df_to_object_attributes(p, df, stem=stem), which auto-detects
            vertical vs row orientation (with a stem fallback).
            Only the first row is meaningful for initialization.
        post_process: optional callable(p) run after assignment, e.g.
            seals_utils.set_derived_attributes. Use this for any stem-specific extras
            (derived attributes, calibration override dicts, etc.).

    Returns:
        The loaded pandas DataFrame (also stored on p as p.<stem>s_df).
    """
    filename = getattr(p, f'{stem}_definitions_filename')
    df_attr = f'{stem}s_df'

    # The path can be set explicitly by the project, but the near-universal case is
    # "<input_dir>/<filename>". Derive it (and record it on p) when it isn't set, so
    # run scripts only need to declare the filename.
    path = getattr(p, f'{stem}_definitions_path', None)
    if not path:
        input_dir = getattr(p, 'input_dir', None)
        if not input_dir:
            raise Exception(
                f'Cannot locate {stem} definitions: set p.{stem}_definitions_path '
                f'or p.input_dir (filename was {filename!r}).'
            )
        path = os.path.join(input_dir, filename)
        setattr(p, f'{stem}_definitions_path', path)

    if not hb.path_exists(path):
        # 1. Standalone project: check for an input_template dir shipped with the script.
        template_path = os.path.join(p.script_dir, 'input_template', filename)
        if hb.path_exists(template_path, verbose=True):
            hb.path_copy(template_path, path)
            print(f'Found {filename} in the input_template dir of this project. Copied to {path}')
        else:
            # 2. Fall back to a matching default in the base data.
            possible_path = p.get_path(base_data_module, 'default_inputs', filename)
            if hb.path_exists(possible_path, verbose=True):
                hb.path_copy(possible_path, path)
            # 3. Nothing anywhere -- nothing we can do but fail loudly.
            else:
                raise Exception(
                    f'No {filename} found in base data or input_dir. Please provide one '
                    f'or run SEALS on the test data to generate one. Full path {path}'
                )

    df = pd.read_csv(path)
    setattr(p, df_attr, df)

    # Hydrate p from the definition row(s). The project-specific assign_fn owns the
    # parsing; for initialization only the first row matters.
    assign_fn(p, df)

    if post_process is not None:
        post_process(p)

    return df
