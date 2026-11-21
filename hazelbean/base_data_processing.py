"""Publishing into the canonical base data store on Cloudflare R2.

Spec: earth_economy_devstack/docs/proposal_base_data_store.qmd. Publishing is the only write to R2. The current version of
a dataset lives at its plain ref path (pyramids/ha_per_cell_10sec.tif); a version it replaces is archived, unless asked
not to, at static/<ref path without extension>/v<release that published it, dots as underscores>.<extension>.

Publishing gates each dataset, stages its new bytes under _staging/, archives the versions being replaced, claims the next
release ID, writes one catalogue entry per dataset, and commits by compare-and-swap on _release/latest.json. Only then are
the plain paths overwritten from staging. If another curator's release commits first, the release and entries this one wrote are
deleted and it stops: rerun it. If overwriting a plain path fails after the commit, rerunning the manifest command finishes it.

Datasets in the public bucket only: single files (POG rasters, GeoPackage vectors and CSV or XLSX tables) and POG tile sets. The R2 calls are in
hazelbean.cloud_utils; credentials come from ~/.config/hazelbean/machine.env (see cloud_utils.get_r2_client).

A tile set (kind 'tileset') is listed and published through its VRT: <stem>_partial.vrt in the dataset folder while tiles are still
being produced, over the tiles in subpogs/<stem>_<rung>sec_<edge>deg/ (hb.build_pog_tileset_vrt). The VRT is the global raster from
the first tile on, an absent tile reading as zero, so a partial set is published like a complete one, marked partial in its
catalogue entry and on its page. Its tiles are uploaded to their own paths beside it, each once; only the VRT is staged and
committed, and a tile set's earlier versions aren't archived (an archived VRT would point at tiles that aren't under static/).

Each dataset folder in base_data carries its own manifest, <name>_base_data_manifest.csv, written by the ingestion script
beside it (<name>_base_data_ingestion.py, usually a call to add_directory_to_base_data). publish_base_data_from_manifests
finds every manifest under base_data, combines them, converts any listed raster that isn't a POG yet, compares the
result with the latest release, and publishes what is new or changed.

A categorical raster's classes are documented by a legend, <name>_base_data_legend.csv beside the manifest: one row per
class, with its id, label, name, description and colour (read_base_data_legend). The manifest's legend column names it,
add_directory_to_base_data writes its colours into the header of each raster it converts, and the dataset's page, its yml
sidecar and its readme show it. The readme (readme.md beside the manifest, write_base_data_readme) is what the dataset's page
shows, as a file that travels with the data: the ingestion script's docstring, the manifest's metadata and every legend,
as a table and as a QGIS colour map.

A continuous raster has no classes, and a float GeoTIFF cannot hold a colour table, so its colours are a colour ramp named in
the manifest's color_ramp column (read_color_ramp), one of four kinds chosen by what a zero means and whether the values have
a middle: 'proportion <colour>' for a share of the cell from 0 to 1; 'divergent <negative colour> <positive colour>' for a
change, on a range symmetric about zero; 'amount <colour> <median> <high>' for any other quantity of which zero means none
(hectares, tonnes, counts, densities, yields); and 'measure <ramp> <low> <high>' for a measurement of which zero is a value like
any other (elevation, temperature, distance). The first three are transparent at exactly zero and opaque everywhere else; a
measure is opaque throughout (get_color_ramp_stops). The page, the sidecar and the readme give the ramp as a QGIS colour map.
"""
import ast
import concurrent.futures
import datetime
import fnmatch
import getpass
import hashlib
import html
import json
import mimetypes
import os
import posixpath
import re
import shutil
import subprocess
import tempfile

import pandas as pd
import yaml

import hazelbean as hb
from hazelbean import cloud_utils

__all__ = ["publish_base_data", "publish_base_data_from_manifests", "retire_base_data", "add_directory_to_base_data", "find_base_data_manifests",
           "write_base_data_index_pages", "resolve_dry_run", "read_base_data_legend", "get_legend_color_table", "get_qgis_color_map",
           "write_base_data_readme", "write_base_data_readme_html", "set_base_data_legend", "read_color_ramp", "get_color_ramp_stops", "get_qgis_color_ramp", "describe_color_ramp",
           "get_raster_range", "get_raster_quantiles", "complete_color_ramp", "set_base_data_color_ramp"]

BUCKET = "teems-public-data"
BUCKETS = {"public": BUCKET, "internal": "teems-private-data"}  # where each hosted tier's files are stored. Releases, catalogue entries, sidecars and pages are all in BUCKET, whatever the tier
URLS = {"public": "https://data.teemlabs.org", "internal": "https://internal.teemlabs.org"}  # where each tier's files are served: openly; behind a login (a script reads the bucket itself, with a token)
LATEST_KEY = "_release/latest.json"
ARCHIVE_FOLDER = "static"
CURRENT_CACHE_CONTROL = "public, max-age=3600"  # a plain path is overwritten by each new version, so caches must not keep it long
REVISION_TOKENS = {"final", "new", "old", "copy", "bak", "backup", "temp", "tmp", "draft"}
MANIFEST_COLUMNS = ("ref_path", "kind", "tier", "variable_class", "license", "units", "data_source", "description", "code", "legend", "color_ramp")
TIERS = ("public", "internal", "unpublished")  # where a manifest row's file is hosted: at data.teemlabs.org; in the bucket behind a token or a login, listed on the public pages as requiring credentials; or nowhere, a file that is part of base data but kept on local disks, as one too large to be worth hosting
OPTIONAL_MANIFEST_COLUMNS =("legend", "color_ramp")  # added 2026-11-19: a manifest written before then lacks them and reads as if they were empty
COLOR_RAMP_KINDS = {"proportion": (1, 0), "divergent": (2, 0), "amount": (1, 2), "measure": (1, 2)}  # a ramp's kind: how many colours it names, and how many numbers (read_color_ramp)
NAMED_RAMPS = {"viridis": ("#440154", "#3b528b", "#21918c", "#5ec962", "#fde725"),  # what a measure may name: perceptually even, readable in grey and by the colour-blind,
               "magma": ("#000004", "#51127c", "#b73779", "#fc8961", "#fcfdbf"),    # each given by five colours evenly spaced from its low end to its high end
               "cividis": ("#00224e", "#434e6c", "#7d7c78", "#bcaf6f", "#fee838")}
FAINT_SHARE = 0.12  # the colour just off zero: this much of the ramp's strong colour over white, opaque
ZERO_STEP = 1e-6    # how far from zero, as a share of the ramp's range, the first opaque colour sits: exactly zero is transparent
MANIFEST_SUFFIX = "_base_data_manifest.csv"
LEGEND_SUFFIX = "_base_data_legend.csv"  # a categorical raster's classes: id, label, name, description, color (read_base_data_legend)
LEGEND_COLUMNS = ("id", "label", "name", "description", "color")
README_NAME = "readme.md"  # a dataset folder's generated readme (write_base_data_readme)
README_HTML_NAME = "readme.html"  # that readme as a page in the look of the data site (write_base_data_readme_html)
SITE_DIR = os.path.join(os.path.expanduser("~"), "Files", "earth_economy_devstack", "docs", "base_data")  # the data site's page templates, where write_base_data_readme_html looks by default
RAW_FOLDER = "raw"  # a dataset folder's raw downloads, exactly as provided: read by its ingestion script, never listed or uploaded
INTERMEDIATE_FOLDER = "intermediate"  # the ingestion run file's ProjectFlow task folders (the dataset folder is its project folder): never listed or uploaded
SUBPOG_FOLDER = "subpogs"  # a dataset folder's tiles, in one folder per tile set: listed and published through the tile set's VRT, never file by file
PARTIAL_SUFFIX = "_partial.vrt"  # the VRT of a tile set whose tiles are still being produced
KINDS_BY_EXTENSION = {".tif": "pog", ".tiff": "pog", ".csv": "table", ".xlsx": "table", ".gpkg": "vector", ".shp": "vector", ".vrt": "tileset"}
SHAPEFILE_SIDECARS = (".shx", ".dbf", ".prj", ".cpg", ".sbn", ".sbx", ".qix")  # copied with their .shp, but not datasets of their own
CONTENT_TYPES = {".tif": "image/tiff", ".gpkg": "application/geopackage+sqlite3", ".csv": "text/csv", ".vrt": "application/xml",
                 ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}  # the kinds publishing supports (a .vrt is a tile set's index)
NOT_DATA = (".py", ".pyc", ".ipynb", ".r", ".sh", ".aux.xml", ".yml", ".md", README_HTML_NAME, MANIFEST_SUFFIX, LEGEND_SUFFIX)  # ingestion scripts, manifests, legends, readmes (and their pages), GDAL sidecars and the geometamaker yml sidecars (linneabean.metadata) aren't datasets
PAGE_CACHE_CONTROL = "public, max-age=300"  # the index pages are rebuilt after every publish
PAGE_FIELDS = (("variable_class", "Variable class"), ("units", "Units"), ("license", "Licence"), ("data_source", "Source"),
               ("description", "Description"), ("code", "Code"))  # the manifest columns a folder page shows, and their labels

def resolve_dry_run(dry_run):
    """Turn a dry_run setting into True or False. A bool is returned as it is. A date, as datetime.date or 'YYYY-MM-DD',
    arms a real run until that day is over: today or a later date means a real run, an earlier date means a dry run. So a
    script left with the date it was last run on goes back to dry runs by itself the next day. Either way one line is
    logged saying which it is. A date far in the future keeps a script armed until then; the comparison is by local
    calendar day."""
    if isinstance(dry_run, bool):
        return dry_run
    if isinstance(dry_run, datetime.datetime):
        date = dry_run.date()
    elif isinstance(dry_run, datetime.date):
        date = dry_run
    elif isinstance(dry_run, str):
        try:
            date = datetime.date.fromisoformat(dry_run.strip())
        except ValueError:
            raise ValueError(f"dry_run must be True, False or a date as 'YYYY-MM-DD', not {dry_run!r}.")
    else:
        raise TypeError(f"dry_run must be True, False or a date as 'YYYY-MM-DD', not {dry_run!r}.")
    today = datetime.date.today()
    if date < today:
        hb.log(f"dry_run={dry_run!r} is before today ({today}): a dry run. Set it to today's date for a real run.")
        return True
    hb.log(f"dry_run={dry_run!r} is today or later: a REAL run, until the end of {date}.")
    return False

def add_directory_to_base_data(source_dir, ref_folder, manifest_path, license, units, data_source, description, code=None, variable_class=None,
                               legend=None, color_ramp=None, overrides=None, include=None, include_subdirectories=True, make_pogs=True, overwrite=False, base_data_dir=None,
                               parallel=True, n_workers=None, dry_run=True, client=None, remove_intermediate_files=False):
    """Add a directory's files to the local base_data and list them in a dataset manifest, ready to publish.

    This is what a dataset's ingestion script (<name>_base_data_ingestion.py, beside its data) calls. Each file goes to
    <base_data_dir>/<ref_folder>/<its path relative to source_dir>; with source_dir already that folder, files stay where
    they are. GeoTIFFs that are already POGs are kept or copied as they are; the rest are converted with hb.make_path_pog
    using their declared variable class (in place, the original is deleted once its POG is written), or, with
    make_pogs=False, left for publishing to convert. Tables and vectors are kept or copied as they are. A POG tile set is listed
    by its VRT, where it is (source_dir must be its folder in base_data); its tiles, in subpogs/, are never listed one by one, and
    the row of a <stem>_partial.vrt that has since been promoted to <stem>.tif or <stem>.vrt is dropped. Hidden files,
    code, manifests, GDAL and metadata (.yml) sidecars, displaced or temporary files and raw/ folders (raw downloads) are skipped. Every new dataset gets a row in
    manifest_path, which is created if missing; rows already there are left alone. Nothing is written to R2: the run
    ends with the publishing dry run.

    A categorical raster should come with a legend (legend, or an override): its colours are written into the header of a
    raster converted here, a raster that already is a POG is expected to carry them, and a new categorical row without a
    legend is reported as a warning (a raster of zone ids, where colours mean nothing, is the case that has none). A real run
    also writes the folder's readme.md beside the manifest (write_base_data_readme).

    Args:
        source_dir (str): The directory to add: usually the dataset's own folder in base_data, or anywhere on disk.
        ref_folder (str): Its folder in base_data, e.g. 'lulc/esa'.
        manifest_path (str): The dataset's manifest, <name>_base_data_manifest.csv beside its ingestion script.
        license, units, data_source, description, code (str): Manifest metadata for every file, unless overridden.
        variable_class (str): For rasters that don't declare one: 'extensive', 'intensive', 'categorical' or 'covariate'.
            Never guessed: a raster with no class declared anywhere is refused.
        legend (str): For categorical rasters: the file name of their legend, <name>_base_data_legend.csv beside the
            manifest (read_base_data_legend). Usually given per file through overrides.
        color_ramp (str): For continuous rasters: how they are coloured (read_color_ramp). 'proportion #rrggbb' for a share of
            the cell between 0 and 1; 'divergent #rrggbb #rrggbb' for a change; 'amount #rrggbb' for another quantity of which
            zero means none; 'measure viridis' for a measurement of which zero is a value like any other. An amount's and a
            measure's numbers are taken from each raster as it is listed (complete_color_ramp), so they need not be given.
            Usually given per file through overrides. A new continuous raster without one is reported as a warning.
        overrides (dict): Per-file changes, keyed by a pattern matched against each file's path relative to source_dir,
            e.g. {'*_yield_*.tif': {'units': 't/ha', 'variable_class': 'intensive'}}. Later patterns win. 'tier' can be
            overridden too, to one of TIERS: 'public' (the default) is published to data.teemlabs.org; 'unpublished' lists
            a file in the manifest and hosts it nowhere (publishing reports it as unpublished), for a dataset that is part
            of base data but kept on local disks and shared on request, as one too large to be worth hosting; 'internal'
            is published to the bucket behind a token or a login, and listed on the public pages with its description.
        include (list): Patterns (matched like overrides); if given, only matching files are added.
        include_subdirectories (bool): Also add files in source_dir's subdirectories.
        make_pogs (bool): Convert rasters that aren't POGs now. False lists them with their variable class, and
            publishing converts them.
        overwrite (bool): Replace files already in base_data that differ, and convert again rasters converted before.
        base_data_dir (str): The local base_data. Defaults to ~/Files/base_data.
        parallel (bool): Check, convert and copy several files at a time (the default), on n_workers threads. False does
            one file at a time. Threads, not processes: the work is GDAL, numpy and hashing, which release Python's lock,
            and threads don't re-run a flat ingestion script the way spawned processes would.
        n_workers (int): Threads when parallel. Defaults to one less than the CPUs this process may use (hb.available_cpu_count).
        dry_run (bool or date): Report what would be done and write nothing. True by default. A date ('YYYY-MM-DD') means a
            real run on that day or later and a dry run once it has passed (hb.resolve_dry_run).
        client: An S3 client for R2, for the publishing dry run. Built from machine.env when not given.
        remove_intermediate_files (bool): Delete the intermediates of each POG conversion when it is done. False by default:
            they are kept in intermediate/add_directory_to_base_data/ beside the manifest, for the researcher to look at
            and to remove.

    Returns:
        dict: 'actions' (ref path -> what was or would be done), 'skipped', 'problems', 'warnings' and 'publish' (the
        publishing dry run's report, or None in a dry run).
    """
    dry_run = resolve_dry_run(dry_run)
    if not source_dir or not os.path.isdir(source_dir):
        raise ValueError(f"source_dir must be an existing directory, not {source_dir!r}.")
    if not ref_folder:
        raise ValueError("Give ref_folder, the folder in base_data the files go to, e.g. 'lulc/esa'.")
    if not os.path.basename(manifest_path).endswith(MANIFEST_SUFFIX):
        raise ValueError(f"A dataset manifest's name must end with {MANIFEST_SUFFIX}, so publishing finds it: {manifest_path}")
    base_data_dir = base_data_dir or os.path.join(os.path.expanduser("~"), "Files", "base_data")
    ref_folder = ref_folder.replace("\\", "/").strip("/")
    defaults = dict(license=license, units=units, data_source=data_source, description=description, code=code, variable_class=variable_class, tier="public", legend=legend, color_ramp=color_ramp)
    manifest_dir = os.path.dirname(os.path.abspath(manifest_path))
    listed = set(_read_manifest(manifest_path)["ref_path"]) if os.path.exists(manifest_path) else set()

    n_workers = n_workers or max(1, hb.available_cpu_count() - 1)

    # Find the files (cheap, in order).
    items, skipped, n_not_included = [], [], 0
    for root, dirs, files in os.walk(source_dir):
        skipped += [os.path.relpath(os.path.join(root, d), source_dir).replace(os.sep, "/") + "/ (raw input, never added)" for d in dirs if d == RAW_FOLDER]
        skipped += [os.path.relpath(os.path.join(root, d), source_dir).replace(os.sep, "/") + "/ (run file intermediates, never added)" for d in dirs if d == INTERMEDIATE_FOLDER]
        skipped += [os.path.relpath(os.path.join(root, d), source_dir).replace(os.sep, "/") + "/ (tiles, listed through their tile set's VRT)" for d in dirs if d == SUBPOG_FOLDER]
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in ("__pycache__", RAW_FOLDER, INTERMEDIATE_FOLDER, SUBPOG_FOLDER))
        if not include_subdirectories:
            skipped += [os.path.relpath(os.path.join(root, d), source_dir).replace(os.sep, "/") + "/ (subdirectory)" for d in dirs]
            dirs[:] = []
        for name in sorted(files):
            source = os.path.join(root, name)
            relative = os.path.relpath(source, source_dir).replace(os.sep, "/")
            # Displaced originals and temporary files (<name>_displaced_<stamp>.tif and the like) are leftovers, not data.
            if name.startswith(".") or name.lower().endswith(NOT_DATA) or any(marker in name for marker in hb.pog.TEMP_NAME_MARKERS):
                skipped.append(relative)
                continue
            if include and not any(fnmatch.fnmatch(relative, pattern) for pattern in include):
                n_not_included += 1
                continue
            stem, extension = os.path.splitext(relative)
            extension = extension.lower()
            ref_path = posixpath.join(ref_folder, stem + (".tif" if extension == ".tiff" else extension))
            settings = dict(defaults)
            for pattern, changes in (overrides or {}).items():
                if fnmatch.fnmatch(relative, pattern):
                    settings.update(changes)
            items.append({"source": source, "relative": relative, "ref_path": ref_path, "path": os.path.join(base_data_dir, *ref_path.split("/")),
                          "kind": KINDS_BY_EXTENSION.get(extension, "other"), "settings": settings, "is_dataset": extension not in SHAPEFILE_SIDECARS})

    # Decide what happens to each file (POG checks and hashes: the slow part, so in parallel).
    def plan(item):
        relative, settings, problems = item["relative"], item["settings"], []
        in_place = os.path.exists(item["path"]) and os.path.samefile(item["source"], item["path"])
        if settings["tier"] not in TIERS:
            problems.append(f"{relative}: its tier is '{settings['tier']}', which is not one of {', '.join(TIERS)}")
        if item["kind"] == "pog":
            settings["variable_class"] = settings["variable_class"] or hb.get_pog_metadata(item["source"]).get("POG_VARIABLE_CLASS") or ""
        if item["kind"] == "pog" and not hb.is_path_pog(item["source"]):
            if not settings["variable_class"]:
                problems.append(f"{relative}: declare its variable class (variable_class, or an override); it is never guessed")
            if make_pogs:
                item["action"] = "make POG in place" if in_place else "make POG"
            else:
                item["action"] = "leave for publishing to make POG" if in_place else "copy; publishing makes POG"
        else:
            item["action"] = "already there" if in_place else "copy"
        if item["kind"] == "tileset":
            if not in_place:
                problems.append(f"{relative}: a tile set is listed where it is, with its tiles; run this on its folder in base_data")
            elif not hb.is_path_pog_tileset(item["source"]):
                problems.append(f"{relative}: fails hb.is_path_pog_tileset; run it with verbose=True to see why")
            else:
                settings["variable_class"] = settings["variable_class"] or hb.get_pog_metadata(_get_tileset_files(item["source"], item["ref_path"])[1][0]).get("POG_VARIABLE_CLASS") or ""
        if not in_place and os.path.exists(item["path"]) and not overwrite:
            if item["action"].startswith("copy") and hb.hash_file_path(item["source"]) == hb.hash_file_path(item["path"]):
                item["action"] = "already there"
            elif item["action"] == "make POG" and hb.is_path_pog(item["path"]):
                item["action"] = "already there"  # converted by an earlier run; overwrite=True converts the source again
            else:
                problems.append(f"{relative}: {item['ref_path']} already exists in base_data and differs; set overwrite to replace it")
        item["manifest"] = "already listed" if item["ref_path"] in listed else ("new row" if item["is_dataset"] else "no row")
        if item["manifest"] == "new row":
            absent = [k for k in ("license", "units", "data_source", "description") if not settings[k]]
            if absent:
                problems.append(f"{relative}: these are required for its manifest row: {absent}")
        # A categorical raster's legend: checked, and its colours either written by the conversion or expected in the header.
        item["warnings"], item["color_table"] = [], None
        if item["kind"] in ("pog", "tileset") and settings["variable_class"] == "categorical":
            if settings["legend"]:
                try:
                    item["color_table"] = get_legend_color_table(os.path.join(manifest_dir, settings["legend"]))
                except (OSError, ValueError) as e:
                    problems.append(f"{relative}: its legend can't be used: {e}")
                raster_path = item["source"] if item["kind"] == "pog" else (_get_tileset_files(item["source"], item["ref_path"])[1:2] or [(None,)])[0][0]
                if item["manifest"] == "new row" and not item["action"].startswith("make POG") and raster_path and not _has_color_table(raster_path):
                    item["warnings"].append(f"{relative}: has a legend but no colour table in its header, and is not converted here; build it with "
                                            f"hb.make_path_pog(..., color_table=hb.get_legend_color_table(<legend>))")
            elif item["manifest"] == "new row":
                item["warnings"].append(f"{relative}: a categorical raster with no legend; give it one ({LEGEND_SUFFIX}) unless its values are ids that colours say nothing about")
        # A continuous raster's colour ramp: checked; an intensive raster listed without one is worth a warning.
        if item["kind"] in ("pog", "tileset") and settings["variable_class"] != "categorical":
            if settings["color_ramp"]:
                try:
                    read_color_ramp(settings["color_ramp"])
                except ValueError as e:
                    problems.append(f"{relative}: {e}")
            elif item["manifest"] == "new row":
                item["warnings"].append(f"{relative}: a continuous raster with no colour ramp; give it color_ramp='proportion #rrggbb' (a share of the cell), 'divergent "
                                        f"#rrggbb #rrggbb' (a change), 'amount #rrggbb' (another quantity, zero meaning none) or 'measure viridis' (zero being a value)")
        return problems

    problems = [p for item_problems in _run_each(plan, items, parallel, n_workers) for p in item_problems]
    warnings = [w for item in items for w in item["warnings"]]

    hb.log(f"{'Dry run: ' if dry_run else ''}adding {source_dir} to base_data as {ref_folder}/: {len(items)} files, {len(skipped)} skipped"
           + (f", {n_not_included} not matching include" if include else "")
           + "".join(f"\n  {i['action']:33s} {i['manifest']:15s} {i['ref_path']}" for i in items)
           + "".join(f"\n  skipped                           {s}" for s in skipped) + "".join(f"\n  WARNING {w}" for w in warnings)
           + "".join(f"\n  PROBLEM {p}" for p in problems))
    result = {"actions": {i["ref_path"]: i["action"] for i in items}, "skipped": skipped, "problems": problems, "warnings": warnings, "publish": None}
    if dry_run:
        return result
    if problems:
        raise ValueError("Nothing was added:\n  " + "\n  ".join(problems))

    # Put the files in place, in parallel, then list the new datasets in the dataset's manifest.
    to_do = [i for i in items if i["action"] not in ("already there", "leave for publishing to make POG")]
    hb.log(f"Putting {len(to_do)} files in place, {min(n_workers, max(1, len(to_do))) if parallel else 1} at a time.")

    def put_in_place(numbered):
        n, item = numbered
        hb.log(f"{item['action'][0].upper() + item['action'][1:]} {n}/{len(to_do)}: {item['ref_path']}")
        os.makedirs(os.path.dirname(item["path"]), exist_ok=True)
        if item["action"].startswith("copy"):
            shutil.copy2(item["source"], item["path"])
        else:
            in_place = item["action"] == "make POG in place"
            hb.make_path_pog(item["source"], None if in_place else item["path"], variable_class=item["settings"]["variable_class"], force_rewrite=overwrite,
                             remove_displaced_files=in_place, remove_intermediate_files=remove_intermediate_files, color_table=item["color_table"],
                             intermediate_dir=os.path.join(manifest_dir, INTERMEDIATE_FOLDER, "add_directory_to_base_data"))
        hb.log(f"Done {n}/{len(to_do)}: {item['ref_path']}")

    failures = _run_each_collecting_failures(put_in_place, list(enumerate(to_do, 1)), parallel, n_workers, label=lambda numbered: numbered[1]["ref_path"])
    if failures:
        raise RuntimeError("These files couldn't be put in place, so the manifest wasn't updated; the others are done, and a rerun "
                           "skips them:\n  " + "\n  ".join(failures))
    def complete(item):  # an amount's or a measure's numbers, from the raster now in place; a raster that gives none keeps the ramp as it was given
        try:
            return complete_color_ramp(item["settings"]["color_ramp"], item["path"])
        except ValueError as e:
            hb.log(f"WARNING {e}")
            return item["settings"]["color_ramp"]
    rows = [dict({k: i["settings"][k] or "" for k in ("variable_class", "license", "units", "data_source", "description", "code")}, ref_path=i["ref_path"],
                 kind=i["kind"], tier=i["settings"]["tier"], legend=i["settings"]["legend"] if i["color_table"] else "",
                 color_ramp=complete(i) if i["settings"]["color_ramp"] and i["kind"] in ("pog", "tileset") and i["settings"]["variable_class"] != "categorical" else "")
            for i in items if i["manifest"] == "new row"]
    existing = _read_manifest(manifest_path) if os.path.exists(manifest_path) else pd.DataFrame(columns=list(MANIFEST_COLUMNS))
    def is_promoted(ref_path):  # a partial tile set's row, once its VRT has gone and the finished product is in its place
        stem = os.path.join(base_data_dir, *ref_path[:-len(PARTIAL_SUFFIX)].split("/"))
        return ref_path.endswith(PARTIAL_SUFFIX) and not os.path.exists(stem + PARTIAL_SUFFIX) and (os.path.exists(stem + ".tif") or os.path.exists(stem + ".vrt"))
    promoted = [r for r in existing["ref_path"] if is_promoted(r)]
    if rows or promoted:
        pd.concat([existing[~existing["ref_path"].isin(promoted)]] + ([pd.DataFrame(rows)[list(MANIFEST_COLUMNS)]] if rows else [])).to_csv(manifest_path, index=False, encoding="utf-8-sig")
    if os.path.exists(manifest_path):
        write_base_data_readme(manifest_path, ref_folder=ref_folder)
    hb.log(f"Added {len(items)} files to base_data and {len(rows)} rows to {manifest_path}" + (f"; dropped the rows of promoted partial tile sets: {promoted}" if promoted else "")
           + ". Publishing dry run:")
    manifest_paths = sorted(set(find_base_data_manifests(base_data_dir)) | {os.path.abspath(manifest_path)})
    result["publish"] = publish_base_data_from_manifests(base_data_dir=base_data_dir, manifest_paths=manifest_paths, dry_run=True, client=client)
    return result

def read_base_data_legend(legend_path):
    """A categorical raster's legend, <name>_base_data_legend.csv, as a DataFrame, checked.

    One row per class the raster can hold, with the columns id (the cell value, a whole number from 0), label (short, lowercase,
    as the EE Spec defines a label), name (for people, short enough for a map legend), description (what the class is, in the
    source's own definition where it gives one) and color (#rrggbb). Every cell is filled, ids and labels are unique. The file
    is UTF-8 with a byte order mark, like the manifests."""
    df = pd.read_csv(legend_path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    missing = [c for c in LEGEND_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"The legend {legend_path} lacks the columns {missing}.")
    df = df[list(LEGEND_COLUMNS)]
    problems = [f"{column} is empty in {int((df[column].str.strip() == '').sum())} rows" for column in LEGEND_COLUMNS if (df[column].str.strip() == "").any()]
    problems += [f"id {v!r} is not a whole number from 0" for v in df["id"] if not v.isdigit()]
    problems += [f"color {v!r} is not #rrggbb" for v in df["color"] if v and not re.fullmatch(r"#[0-9a-fA-F]{6}", v)]
    problems += [f"{column} {v!r} is given more than once" for column in ("id", "label") for v in df[column][df[column].duplicated()].unique()]
    if problems or df.empty:
        raise ValueError(f"The legend {legend_path} " + ("has no rows." if df.empty else "is not usable: " + "; ".join(problems[:10]) + "."))
    return df.assign(id=df["id"].astype(int)).sort_values("id").reset_index(drop=True)

def get_legend_color_table(legend_path):
    """A legend's colours as a dict of cell value to (r, g, b): what hb.make_path_pog's color_table takes."""
    legend = read_base_data_legend(legend_path)
    return {i: tuple(int(color[k:k + 2], 16) for k in (1, 3, 5)) for i, color in zip(legend["id"], legend["color"])}

def get_qgis_color_map(legend_path):
    """A legend as the text of a QGIS colour map file: a line 'value,red,green,blue,alpha,name' per class.

    Saved as a .txt it loads in QGIS under Layer Properties, Symbology, with the render type Paletted/Unique values or
    Singleband pseudocolor: Load Color Map from File. A comma in a name is written as a semicolon, since the format has no quoting."""
    legend = read_base_data_legend(legend_path)
    colors = get_legend_color_table(legend_path)
    return "\n".join(["# QGIS Generated Color Map Export File", "INTERPOLATION:EXACT"]
                     + [f"{i},{colors[i][0]},{colors[i][1]},{colors[i][2]},255,{name.replace(',', ';')}" for i, name in zip(legend["id"], legend["name"])]) + "\n"

def read_color_ramp(color_ramp):
    """A manifest's color_ramp as (kind, colours, numbers): the kind, its colours as (r, g, b), and the numbers it carries, if any.

    Which kind a continuous raster takes is settled by two questions: does a cell of exactly 0 mean there is nothing there,
    and do the values have a middle they run away from in two directions?

    'proportion #rrggbb': a share of the cell between 0 and 1. The colour is the one a full cell (1.0) takes, strong and
    fitting the subject (a green for tree cover, a blue for water).
    'divergent #rrggbb #rrggbb': a change, with zero its middle. The first colour is the largest decrease, the second the
    largest increase, a pair that reads as opposites and that the colour-blind can tell apart (a red or brown against a blue
    or blue-green, not red against green).
    'amount #rrggbb <median> <high>': any other quantity of which zero means none: hectares, tonnes, counts, a density, a
    yield. The colour is the one the highest cells take. The numbers are the median and the 98th percentile of the cells that
    are not zero (get_raster_quantiles): such quantities are skewed, a few cells holding most of the total, and a ramp drawn
    straight to the maximum would leave nearly every cell in its faintest tenth.
    'measure <viridis, magma or cividis> <low> <high>': a measurement of which zero is a value like any other: elevation,
    temperature, distance, a score. No value is singled out, so the ramp has many hues and is opaque throughout. The numbers
    are the 2nd and 98th percentiles of the cells.

    An amount or a measure may be given without its numbers ('amount #08306b'): add_directory_to_base_data then takes them
    from the raster when it lists it (complete_color_ramp), and the manifest holds the whole text."""
    parts = str(color_ramp).split()
    problem = f"color_ramp {color_ramp!r} is none of 'proportion #rrggbb', 'divergent #rrggbb #rrggbb', 'amount #rrggbb [median high]' and 'measure <{', '.join(NAMED_RAMPS)}> [low high]'."
    if not parts or parts[0] not in COLOR_RAMP_KINDS:
        raise ValueError(problem)
    n_colors, n_numbers = COLOR_RAMP_KINDS[parts[0]]
    names, numbers = parts[1:1 + n_colors], parts[1 + n_colors:]
    if parts[0] == "measure":
        if len(names) != 1 or names[0] not in NAMED_RAMPS:
            raise ValueError(problem)
        names = NAMED_RAMPS[names[0]]
    if len(names) < n_colors or not all(re.fullmatch(r"#[0-9a-fA-F]{6}", c) for c in names) or len(numbers) not in (0, n_numbers):
        raise ValueError(problem)
    try:
        numbers = [float(n) for n in numbers]
    except ValueError:
        raise ValueError(problem)
    if numbers and not (numbers[0] < numbers[1] and (parts[0] != "amount" or numbers[0] > 0)):
        raise ValueError(f"color_ramp {color_ramp!r}: its two numbers must rise" + (", from above zero." if parts[0] == "amount" else "."))
    return parts[0], [tuple(int(c[k:k + 2], 16) for k in (1, 3, 5)) for c in names], numbers

def get_color_ramp_stops(color_ramp, minimum=None, maximum=None):
    """The stops of a colour ramp, lowest value first, each (value, (r, g, b), alpha): colours run straight between neighbours,
    and a value beyond the last stop at either end takes that stop's colour.

    In a proportion, a divergent ramp and an amount, exactly zero is transparent, so a cell with nothing in it shows what is
    under the layer, and every other value is opaque: the stop next to zero, ZERO_STEP of the range away, is the faint
    colour (FAINT_SHARE of the strong one over white), so a cell with very little in it is still seen.

    A proportion runs from that faint colour to the strong one at 1.0, whatever the raster holds: 1.0 means a full cell in
    every map. A divergent ramp is symmetric: its range is minus to plus the larger of |minimum| and |maximum|, the raster's
    own extremes (get_raster_range), so equal changes up and down get equally strong colours and zero is the middle.
    An amount passes through the colour halfway between faint and strong at its median and reaches the strong one at its
    high number, so half of the cells that hold anything are drawn in the lower half of the ramp and half in the upper,
    however skewed they are; the 2 percent of cells above the high number all take the strong colour. A measure spreads its
    named ramp evenly from its low number to its high one, opaque everywhere, zero included."""
    kind, colors, numbers = read_color_ramp(color_ramp)
    faint = lambda rgb: tuple(round(255 - FAINT_SHARE * (255 - v)) for v in rgb)
    if kind == "proportion":
        return [(0.0, faint(colors[0]), 0), (ZERO_STEP, faint(colors[0]), 255), (1.0, colors[0], 255)]
    if kind == "divergent":
        if minimum is None or maximum is None:
            raise ValueError("A divergent colour ramp needs the raster's minimum and maximum: its range is the larger of the two in absolute value, both ways.")
        extreme = max(abs(float(minimum)), abs(float(maximum))) or 1.0
        return [(-extreme, colors[0], 255), (-extreme * ZERO_STEP, faint(colors[0]), 255), (0.0, (255, 255, 255), 0), (extreme * ZERO_STEP, faint(colors[1]), 255), (extreme, colors[1], 255)]
    if not numbers:
        raise ValueError(f"color_ramp {color_ramp!r} has no numbers yet: hb.complete_color_ramp takes them from the raster.")
    if kind == "amount":
        middle = tuple(round((a + b) / 2) for a, b in zip(faint(colors[0]), colors[0]))
        return [(0.0, faint(colors[0]), 0), (min(numbers[1] * ZERO_STEP, numbers[0] / 2), faint(colors[0]), 255), (numbers[0], middle, 255), (numbers[1], colors[0], 255)]
    return [(numbers[0] + (numbers[1] - numbers[0]) * i / (len(colors) - 1), rgb, 255) for i, rgb in enumerate(colors)]

def get_qgis_color_ramp(color_ramp, minimum=None, maximum=None):
    """A colour ramp as the text of a QGIS colour map file: a line 'value,red,green,blue,alpha,label' per stop, interpolated between.

    Saved as a .txt it loads in QGIS under Layer Properties, Symbology, with the render type Singleband pseudocolor: Load
    Color Map from File. minimum and maximum, the raster's own, are needed for a divergent ramp only (get_color_ramp_stops)."""
    stops = get_color_ramp_stops(color_ramp, minimum, maximum)
    return "\n".join(["# QGIS Generated Color Map Export File", "INTERPOLATION:INTERPOLATED"]
                     + [f"{value:.10g},{rgb[0]},{rgb[1]},{rgb[2]},{alpha},{value:.4g}" for value, rgb, alpha in stops]) + "\n"

def describe_color_ramp(color_ramp, minimum=None, maximum=None):
    """A colour ramp in a sentence, for a readme, a page or a sidecar: its stops as colours, and what happens at zero."""
    kind, colors, numbers = read_color_ramp(color_ramp)
    name = lambda rgb: "#%02x%02x%02x" % tuple(rgb)
    if kind in ("amount", "measure") and not numbers:
        return f"{'An amount' if kind == 'amount' else 'A measure'} whose range has not been taken from the raster yet."
    stops = get_color_ramp_stops(color_ramp, 0 if minimum is None else minimum, 1 if maximum is None else maximum)
    if kind == "proportion":
        return f"A proportion: transparent at exactly 0, then opaque from {name(stops[1][1])} just above 0 to {name(stops[2][1])} at 1.0."
    if kind == "amount":
        return (f"An amount: transparent at exactly 0, then opaque from {name(stops[1][1])} just above 0, through {name(stops[2][1])} at {numbers[0]:.4g}, to {name(stops[3][1])} at "
                f"{numbers[1]:.4g} and above. The two numbers are the median and the 98th percentile of the cells that are not zero, unless they were set by hand to hold several rasters to one scale.")
    if kind == "measure":
        return (f"A measure, opaque throughout, zero included: {color_ramp.split()[1]}, from {name(stops[0][1])} at {numbers[0]:.4g} and below to {name(stops[-1][1])} at "
                f"{numbers[1]:.4g} and above. The two numbers are the 2nd and 98th percentiles of the cells, unless they were set by hand to hold several rasters to one scale.")
    symmetric = f"plus and minus {stops[4][0]:.4g}" if minimum is not None and maximum is not None else "plus and minus the larger of the raster's |minimum| and |maximum|"
    return (f"A change, on a range symmetric about zero ({symmetric}): {name(stops[0][1])} at the largest decrease, {name(stops[1][1])} just below 0, "
            f"transparent at exactly 0, {name(stops[3][1])} just above 0, {name(stops[4][1])} at the largest increase.")

def get_raster_quantiles(raster_path, percentiles, exclude_zero=False, max_blocks=400):
    """Percentiles of a raster's cells at full resolution, nodata left out and, with exclude_zero, zeros too: from every block of
    512 x 512 cells that holds such cells when there are max_blocks of them or fewer, otherwise from max_blocks of them spread
    evenly.

    Which blocks hold such cells is read off a coarse overview, where the raster has one, so a global raster whose data cover
    one country is sampled where the data are; the percentiles themselves are always taken from full-resolution cells, never
    from an overview, whose cells are other quantities (an extensive raster's are sums). The blocks are the same on every
    call, so the answer is too. On a large raster it is an estimate, good to the two or three digits a colour ramp needs.
    Returns None when the raster holds no such cell."""
    import numpy as np
    from osgeo import gdal
    ds = gdal.Open(raster_path)
    band, size, nodata = ds.GetRasterBand(1), 512, ds.GetRasterBand(1).GetNoDataValue()
    def wanted(array):
        keep = np.isfinite(array)
        if nodata is not None:
            keep &= array != nodata
        return keep & (array != 0) if exclude_zero else keep
    coarse = next((band.GetOverview(k) for k in range(band.GetOverviewCount()) if band.GetOverview(k).XSize <= 8192), None) if ds.RasterXSize > 8192 else None
    if coarse is not None:  # the blocks under the overview cells that hold something
        rows, cols = np.nonzero(wanted(coarse.ReadAsArray()))
        factor = ds.RasterXSize / coarse.XSize
        block_corners = sorted({(int(c * factor) // size * size, int(r * factor) // size * size) for r, c in zip(rows.tolist(), cols.tolist())}, key=lambda xy: (xy[1], xy[0]))
    else:
        block_corners = [(x, y) for y in range(0, ds.RasterYSize, size) for x in range(0, ds.RasterXSize, size)]
    if len(block_corners) > max_blocks:
        block_corners = [block_corners[int(i * len(block_corners) / max_blocks)] for i in range(max_blocks)]
    values = [np.zeros(0)]
    for x, y in block_corners:
        array = band.ReadAsArray(x, y, min(size, ds.RasterXSize - x), min(size, ds.RasterYSize - y))
        values.append(array[wanted(array)].astype(np.float64))
    ds = None
    values = np.concatenate(values)
    return [float(v) for v in np.percentile(values, percentiles)] if values.size else None

def complete_color_ramp(color_ramp, raster_path):
    """color_ramp with the numbers an amount or a measure needs, taken from the raster and rounded to three significant digits; any
    other ramp, and one that already has its numbers, is returned as it is.

    An amount gets the median and the 98th percentile of its cells that are not zero, a measure the 2nd and 98th percentiles
    of its cells (get_raster_quantiles). For an extensive raster the numbers are those of its own cell size: its overviews
    hold sums over ever larger cells, so zoomed out every cell passes the high number and the map goes to the strong colour.
    Where a quantity is to be read at every zoom, give it as a proportion or a density (an intensive raster) instead."""
    kind, _, numbers = read_color_ramp(color_ramp)
    if kind not in ("amount", "measure") or numbers:
        return color_ramp
    quantiles = get_raster_quantiles(raster_path, [50, 98] if kind == "amount" else [2, 98], exclude_zero=kind == "amount")
    quantiles = quantiles and [float(f"{q:.3g}") for q in quantiles]
    if quantiles is None or not quantiles[0] < quantiles[1]:  # no cells, or cells so alike that the two numbers are one
        raise ValueError(f"{raster_path} gives no range for color_ramp {color_ramp!r}: its cells yield the percentiles {quantiles}. Give the two numbers by hand.")
    return color_ramp + " " + " ".join(f"{q:g}" for q in quantiles)

def get_raster_range(raster_path):
    """The (minimum, maximum) a POG or a POG tile set's VRT records in its exact statistics, or None when it records none."""
    try:
        if raster_path.lower().endswith(".vrt"):
            ranges = [get_raster_range(tile_path) for tile_path, _ in _get_tileset_files(raster_path, "x.vrt")[1:]]
            return (min(r[0] for r in ranges), max(r[1] for r in ranges)) if ranges and all(ranges) else None
        stats = hb.get_pog_info(raster_path)["stats"]
        return float(stats["minimum"]), float(stats["maximum"])
    except Exception:
        return None

def _get_color_ramp_sections(rows, path_of):
    """What a readme or a page says of the colour ramps a folder's rows name. Per ramp, a tuple of the files' rows, the sentence
    describing the ramp, its QGIS colour map (None when the range is not known: a divergent ramp whose raster records no extremes, an
    amount or a measure still without its numbers) and, where rasters share a ramp's kind and colour but each has its own two
    numbers (the crops of a set), those numbers per row, the colour map then being the first row's, as the pattern for the others."""
    groups = {}
    for row in rows:
        if row.get("color_ramp"):
            kind, _, numbers = read_color_ramp(row["color_ramp"])
            value_range = get_raster_range(path_of(row)) if kind == "divergent" else None
            groups.setdefault((" ".join(row["color_ramp"].split()[:len(row["color_ramp"].split()) - len(numbers)]), value_range), []).append(row)
    sections = []
    for (base, value_range), group in groups.items():
        kind, first = read_color_ramp(base)[0], group[0]["color_ramp"]
        known = kind == "proportion" or value_range is not None or bool(read_color_ramp(first)[2])
        color_map = get_qgis_color_ramp(first, *(value_range or (None, None))) if known else None
        if len({row["color_ramp"] for row in group}) > 1:
            sentence = (f"{'An amount' if kind == 'amount' else 'A measure'} ({base}), each raster with its own two numbers, listed below: "
                        + ("transparent at exactly 0, then opaque from a faint tint just above 0, through the colour halfway to strong at the raster's first number "
                           "(the median of its cells that are not zero), to the strong colour at its second (their 98th percentile) and above." if kind == "amount" else
                           "opaque throughout, zero included, the ramp running evenly from the raster's first number (the 2nd percentile of its cells) to its second (the 98th)."))
            sections.append((group, sentence, color_map, [read_color_ramp(row["color_ramp"])[2] for row in group]))
        else:
            sections.append((group, describe_color_ramp(first, *(value_range or (None, None))), color_map, None))
    return sections

def write_base_data_readme(manifest_path, ref_folder=None):
    """Write readme.md beside a dataset manifest: what the dataset's page on the data site shows, as a file that travels with the data.

    Built from the same three sources as the page, and never edited by hand (rerun the ingestion script instead): the
    docstring of the ingestion script beside the manifest (its first paragraph as the summary, all of it as the processing
    steps), the manifest (the metadata every file shares, then a table of the files, published or not) and every legend the
    manifest names, each as a table of its classes and as a QGIS colour map (get_qgis_color_map).

    Args:
        manifest_path (str): The dataset's manifest, <name>_base_data_manifest.csv.
        ref_folder (str): The folder's place in base_data, for the title. Defaults to the folder of the manifest's first row.

    Returns:
        str: The readme's path.
    """
    folder = os.path.dirname(os.path.abspath(manifest_path))
    rows = _read_manifest(manifest_path).to_dict("records")
    if not ref_folder:  # the part of a row's ref path that ends with the manifest's folder: its rows may sit in subfolders
        ref_folder = posixpath.dirname(rows[0]["ref_path"]) if rows else os.path.basename(folder)
        while os.path.basename(folder) in ref_folder.split("/")[:-1]:
            ref_folder = posixpath.dirname(ref_folder)
    script_name = os.path.basename(manifest_path)[:-len(MANIFEST_SUFFIX)] + "_base_data_ingestion.py"
    docstring = _read_module_docstring(os.path.join(folder, script_name))
    escape = lambda text: str(text).replace("|", "\\|").replace("\n", " ")
    out = [f"# {ref_folder}", ""]
    if docstring:
        out += [_get_docstring_texts(docstring)["about"] or _get_docstring_texts(docstring)["tagline"], ""]
    out += [f"*This file is generated by `hb.write_base_data_readme` from `{os.path.basename(manifest_path)}`, the docstring of `{script_name}` and the legends "
            "named in the manifest. Do not edit it: change those and rerun the ingestion script. Part of the TEEMs base data, https://data.teemlabs.org.*", ""]
    if rows:
        rows = sorted(rows, key=lambda row: _natural_sort_key(row["ref_path"]))
        fields = (("kind", "Kind"),) + PAGE_FIELDS + (("legend", "Legend"),)  # the colour ramps have their own section: they may differ file by file
        shared = [(k, label) for k, label in fields if len({row[k] for row in rows}) == 1]
        varying = [(k, label) for k, label in fields if (k, label) not in shared]
        name = lambda row: f"`{posixpath.relpath(row['ref_path'], ref_folder)}`"
        out += ["## Metadata", ""] + [f"- **{label}:** {rows[0][k]}" for k, label in shared if rows[0][k]] + [""]
        groups = {}
        for row in rows:
            groups.setdefault(tuple(row[k] for k, _ in varying), []).append(row)
        if len(groups) == len(rows) or not varying:  # every file differs (or none does): a table, a row per file
            out += ["| " + " | ".join(["File"] + [label for _, label in varying]) + " |", "|" + " --- |" * (1 + len(varying))]
            out += ["| " + " | ".join([name(row)] + [escape(row[k]) for k, _ in varying]) + " |" for row in rows] + [""]
        else:  # files that share their metadata are listed together under it, so a text 173 files share is written once
            for values, group in groups.items():
                out += [f"### {len(group)} file{'s' if len(group) != 1 else ''}", ""] + [f"- **{label}:** {value}" for (_, label), value in zip(varying, values) if value]
                out += ["", ", ".join(name(row) for row in group), ""]
    for legend_name in sorted({row["legend"] for row in rows if row["legend"]}):
        legend_path = os.path.join(folder, legend_name)
        legend, colors = read_base_data_legend(legend_path), get_legend_color_table(legend_path)
        users = [f"`{posixpath.relpath(row['ref_path'], ref_folder)}`" for row in rows if row["legend"] == legend_name]
        first = os.path.join(folder, *posixpath.relpath(next(row["ref_path"] for row in rows if row["legend"] == legend_name), ref_folder).split("/"))
        out += [f"## Legend: {legend_name}", "", f"The classes of {', '.join(users[:5])}" + (f" and {len(users) - 5} more files" if len(users) > 5 else "")
                + f". {_get_header_colors_note(first)} The legend itself is `{legend_name}`, beside this file.", "",
                "| Value | Label | Name | Colour | RGB | Description |", "| --- | --- | --- | --- | --- | --- |"]
        out += [f"| {r['id']} | `{r['label']}` | {escape(r['name'])} | `{r['color']}` | {', '.join(str(v) for v in colors[r['id']])} | {escape(r['description'])} |"
                for r in legend.to_dict("records")]
        out += ["", "As a QGIS colour map (save the block as a `.txt` file; in QGIS: Layer Properties, Symbology, Paletted/Unique values, "
                "Load Color Map from File). Each line is value, red, green, blue, alpha, name:", "", "```text", get_qgis_color_map(legend_path).rstrip("\n"), "```", ""]
    for group, sentence, color_map, numbers in _get_color_ramp_sections(rows, lambda row: os.path.join(folder, *posixpath.relpath(row["ref_path"], ref_folder).split("/"))):
        users = [f"`{posixpath.relpath(row['ref_path'], ref_folder)}`" for row in group]
        title = group[0]["color_ramp"] if numbers is None else " ".join(group[0]["color_ramp"].split()[:2]) + ", per raster"
        out += [f"## Colour ramp: {title}", "", f"For {', '.join(users[:5])}" + (f" and {len(users) - 5} more files" if len(users) > 5 else "")
                + f". {sentence} A float raster cannot carry colours in its header, so a viewer shows these only once the ramp is loaded.", ""]
        if numbers is not None:
            out += ["| File | First number | Second number |", "| --- | --- | --- |"] + [f"| {user} | {' | '.join(f'{n:g}' for n in pair) if pair else 'not taken | not taken'} |" for user, pair in zip(users, numbers)]
            out += ["", f"The colour map below is that of {users[0]}: for another raster, put its two numbers in place of the last two lines' values (and half its first number, at most, in the second line).", ""]
        if color_map:
            out += ["As a QGIS colour map (save the block as a `.txt` file; in QGIS: Layer Properties, Symbology, Singleband pseudocolor, Load Color Map from File). "
                    "Each line is value, red, green, blue, alpha, label, and colours are interpolated between the lines:", "", "```text", color_map.rstrip("\n"), "```", ""]
        else:
            out += ["The raster records no minimum and maximum, so its range is not given here: use the larger of the two in absolute value, both ways.", ""]
    if docstring:
        out += ["## Processing steps", "", _get_docstring_markdown(docstring), "", f"From the ingestion script that made these files, `{script_name}`.", ""]
    readme_path = os.path.join(folder, README_NAME)
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    hb.log(f"Wrote {readme_path}")
    write_base_data_readme_html(manifest_paths=[manifest_path])
    return readme_path

def write_base_data_readme_html(site_dir=None, base_data_dir=None, manifest_paths=None):
    """Render each dataset folder's readme.md as readme.html beside it, in the look of https://data.teemlabs.org.

    The page is the readme, unchanged, in the data site's folder page template (site_dir/_folder_page.qmd and _styles.css),
    with the styles and the logo embedded: one file that opens from disk with no server and no connection. Unlike a folder's
    page on the site it needs nothing to be published, so it shows what the readme shows, for every file the manifest lists,
    and none of what only a release knows (versions, sizes, download links). Links to the site are written in full, since
    the template's are relative to the site's root, and a colour written as `#rrggbb` (a legend's classes) gets a swatch.
    The page is rewritten from the readme on every call: never edit it, and it is not data (NOT_DATA).
    write_base_data_readme calls this for its own folder, so whatever writes a readme (add_directory_to_base_data, so every
    ingestion script) writes the page with it.

    Args:
        site_dir (str): The templates, in earth_economy_devstack/docs/base_data. Defaults to SITE_DIR, the devstack under ~/Files.
        base_data_dir (str): The local base_data, searched for manifests. Defaults to ~/Files/base_data.
        manifest_paths (list): Use the folders of these manifests instead of searching base_data_dir.

    Returns:
        list: The paths of the pages written. Empty, with a message, when Quarto isn't installed or the templates aren't there.
    """
    quarto = shutil.which("quarto")
    if quarto is None:
        hb.log("Quarto isn't installed (https://quarto.org), so no readme.html was written.")
        return []
    site_dir = site_dir or SITE_DIR
    if not os.path.exists(os.path.join(site_dir, "_folder_page.qmd")):
        hb.log(f"The page templates aren't in {site_dir}, so no readme.html was written.")
        return []
    base_data_dir = base_data_dir or os.path.join(os.path.expanduser("~"), "Files", "base_data")
    manifest_paths = find_base_data_manifests(base_data_dir) if manifest_paths is None else list(manifest_paths)
    folders = sorted({os.path.dirname(os.path.abspath(manifest_path)) for manifest_path in manifest_paths})
    folders = [folder for folder in folders if os.path.exists(os.path.join(folder, README_NAME))]
    built_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    swatch = r'<span style="display:inline-block;width:1em;height:1em;border:1px solid #888;vertical-align:-.15em;background:\1"></span> `\1`'
    with open(os.path.join(site_dir, "_folder_page.qmd"), encoding="utf-8") as f:
        folder_template = f.read()
    html_paths = []
    with tempfile.TemporaryDirectory() as project_dir:  # one Quarto project for every readme, a numbered folder each, as write_base_data_index_pages does
        shutil.copy(os.path.join(site_dir, "_styles.css"), os.path.join(project_dir, "styles.css"))
        shutil.copy(os.path.join(site_dir, "teems_logo.png"), project_dir)
        with open(os.path.join(project_dir, "_quarto.yml"), "w", encoding="utf-8") as f:
            f.write("project:\n  type: default\n  output-dir: _site\n")
        for i, folder in enumerate(folders):
            with open(os.path.join(folder, README_NAME), encoding="utf-8") as f:
                readme = f.read()
            title = readme.split("\n", 1)[0].lstrip("#").strip()  # a readme's first line is its ref folder, as a heading
            crumbs = ['<a href="/">data.teemlabs.org</a>'] + [f"<span>{html.escape(part)}</span>" for part in title.split("/")]  # only the site itself is a link: the folder may not be published
            page = _fill_placeholders(folder_template, page_title=json.dumps(f"{title} · TEEMs Base Data"), description=json.dumps(f"The readme of the {title} folder of the TEEMs base data."),
                                      root="../", breadcrumbs='<span class="sep">/</span>'.join(crumbs), body=re.sub(r"`(#[0-9a-fA-F]{6})`", swatch, readme),
                                      release="none: this page is the folder's readme.md, rendered from the local copy", built_at=built_at)
            os.makedirs(os.path.join(project_dir, str(i)))
            with open(os.path.join(project_dir, str(i), "index.qmd"), "w", encoding="utf-8") as f:
                f.write(page)
        subprocess.run([quarto, "render", project_dir, "--quiet"], check=True)
        for i, folder in enumerate(folders):
            with open(os.path.join(project_dir, "_site", str(i), "index.html"), encoding="utf-8") as f:
                page = f.read()
            html_paths.append(os.path.join(folder, README_HTML_NAME))
            with open(html_paths[-1], "w", encoding="utf-8") as f:
                f.write(page.replace('href="/', 'href="https://data.teemlabs.org/'))
    hb.log(f"Wrote {README_HTML_NAME} beside {len(html_paths)} readmes.")
    return html_paths

def set_base_data_legend(manifest_path, legend, include=None):
    """Name a legend on the categorical rasters a manifest already lists, and rewrite the folder's readme.

    add_directory_to_base_data records a legend on the rows it adds and leaves rows already listed alone; this is for those:
    a dataset ingested before it had a legend. Only the manifest's legend column and readme.md change. The rasters are not
    touched, so one built without a colour table still has none in its header (that takes a rebuild, hb.make_path_pog with
    color_table=hb.get_legend_color_table(legend)); its page, yml sidecar and readme show the classes all the same.

    Args:
        manifest_path (str): The dataset's manifest, <name>_base_data_manifest.csv.
        legend (str): The legend's file name, <name>_base_data_legend.csv beside the manifest. Checked (read_base_data_legend).
        include (list): Patterns matched against each row's ref path and its file name; if given, only matching rows are set.

    Returns:
        list: The ref paths whose legend changed.
    """
    read_base_data_legend(os.path.join(os.path.dirname(os.path.abspath(manifest_path)), legend))
    df = _read_manifest(manifest_path)
    matches = df["ref_path"].map(lambda r: not include or any(fnmatch.fnmatch(r, pattern) or fnmatch.fnmatch(posixpath.basename(r), pattern) for pattern in include))
    to_set = (df["variable_class"] == "categorical") & df["kind"].isin(["pog", "tileset"]) & matches & (df["legend"] != legend)
    changed = df.loc[to_set, "ref_path"].tolist()
    if changed:
        df.loc[to_set, "legend"] = legend
        df.to_csv(manifest_path, index=False, encoding="utf-8-sig")
    hb.log(f"{legend} named on {len(changed)} rows of {manifest_path}")
    write_base_data_readme(manifest_path)
    return changed

def set_base_data_color_ramp(manifest_path, color_ramp, include=None, base_data_dir=None):
    """Name a colour ramp on the continuous rasters a manifest already lists, and rewrite the folder's readme.

    The counterpart of set_base_data_legend for rasters that are not categorical: a dataset listed before it had a ramp.
    Only the manifest's color_ramp column and readme.md change; the rasters are read, for an amount's or a measure's numbers
    (complete_color_ramp, per raster unless the ramp is given with its numbers), and never written. A raster that gives no
    numbers keeps the ramp as it was given, with a line in the log.

    Args:
        manifest_path (str): The dataset's manifest, <name>_base_data_manifest.csv.
        color_ramp (str): The ramp (read_color_ramp), e.g. 'proportion #006d2c', 'amount #08306b' or 'measure viridis 0 3000'.
        include (list): Patterns matched against each row's ref path and its file name; if given, only matching rows are set.
        base_data_dir (str): The local base_data the ref paths are under. Defaults to ~/Files/base_data.

    Returns:
        dict: ref path -> the ramp now in the manifest, for the rows that changed.
    """
    read_color_ramp(color_ramp)
    base_data_dir = base_data_dir or os.path.join(os.path.expanduser("~"), "Files", "base_data")
    df = _read_manifest(manifest_path)
    matches = df["ref_path"].map(lambda r: not include or any(fnmatch.fnmatch(r, pattern) or fnmatch.fnmatch(posixpath.basename(r), pattern) for pattern in include))
    changed = {}
    for index in df.index[(df["variable_class"] != "categorical") & df["kind"].isin(["pog", "tileset"]) & matches]:
        try:
            ramp = complete_color_ramp(color_ramp, os.path.join(base_data_dir, *df.at[index, "ref_path"].split("/")))
        except Exception as e:  # no range in the raster, or no raster on this machine
            hb.log(f"WARNING {e}")
            ramp = color_ramp
        if df.at[index, "color_ramp"] != ramp:
            df.at[index, "color_ramp"] = changed[df.at[index, "ref_path"]] = ramp
    if changed:
        df.to_csv(manifest_path, index=False, encoding="utf-8-sig")
    hb.log(f"{color_ramp!r} named on {len(changed)} rows of {manifest_path}")
    write_base_data_readme(manifest_path)
    return changed

def find_base_data_manifests(base_data_dir=None):
    """Every dataset manifest (<name>_base_data_manifest.csv) under base_data, sorted."""
    base_data_dir = base_data_dir or os.path.join(os.path.expanduser("~"), "Files", "base_data")
    found = []
    for root, dirs, files in os.walk(base_data_dir):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in ("__pycache__", RAW_FOLDER, INTERMEDIATE_FOLDER))
        found += [os.path.join(root, f) for f in files if f.endswith(MANIFEST_SUFFIX)]
    return sorted(found)

def publish_base_data_from_manifests(base_data_dir=None, manifest_paths=None, note=None, archive_previous=True, parallel=True, n_workers=None, dry_run=True,
                                     client=None, site_dir=None, remove_intermediate_files=False):
    """Combine every dataset manifest under base_data, compare it with the local files and the latest release, and publish what is new or changed.

    The manifests (<name>_base_data_manifest.csv, each beside its dataset's ingestion script) are combined into one
    list; a ref path listed by two manifests is an error. A listed raster that isn't a POG yet is converted in place with
    its row's variable_class before anything else, on a real run only: a dry run reports it as 'needs_pog'. Public rows
    publish: POG rasters (.tif), GeoPackage vectors (.gpkg), tables (.csv, .xlsx) and POG tile sets (.vrt, with their tiles;
    a partial one too, marked as partial); shapefiles don't yet. A public row's file goes to data.teemlabs.org and an internal row's to the bucket behind the login; both are in the one release. Every row then gets a status: 'new' (not yet published), 'changed' (the local bytes differ from the published version), 'unchanged',
    'unpublished' (its tier is unpublished: listed, and hosted nowhere; these are counted, not named one by one),
    'unfinished' (published, but its plain path doesn't hold those bytes yet, because an earlier run stopped after its
    commit), 'missing_locally', or 'unsupported' (a kind publishing can't handle yet), or 'tier_changed' (published on one tier and listed on another: nothing is done; retire it with retire_base_data, then publish). Published datasets that no
    manifest lists are reported as 'not_in_manifest'. Unfinished plain paths are completed from the local files, then the
    new and changed rows are published together as one release, with each row's metadata.

    Args:
        base_data_dir (str): The local base_data, searched for manifests and read for files. Defaults to ~/Files/base_data.
        manifest_paths (list): Use these manifests instead of searching base_data_dir.
        note (str): One-line change note for the release. Required unless dry_run.
        archive_previous (bool): Keep each replaced version under static/ (see publish_base_data).
        parallel (bool): Check, convert and hash files several at a time (the default), on n_workers threads. False does
            one file at a time. Uploads go one file at a time either way.
        n_workers (int): Threads when parallel. Defaults to one less than the CPUs this process may use.
        dry_run (bool or date): Report and run the gate only; write nothing. True by default, so publishing is always explicit.
            A date ('YYYY-MM-DD') means a real run on that day or later and a dry run once it has passed (hb.resolve_dry_run).
        client: An S3 client for R2. Built from machine.env when not given.
        site_dir (str): The page templates (earth_economy_devstack/docs/base_data). When given, every real run ends by
            rebuilding and uploading the pages of https://data.teemlabs.org (write_base_data_index_pages).
        remove_intermediate_files (bool): Delete the intermediates of each POG conversion when it is done. False by default:
            they are kept in intermediate/publish_base_data_from_manifests/ beside the raster's manifest, for the researcher
            to look at and to remove.

    Returns:
        dict: 'statuses' (ref path -> status), 'manifests' (the manifests combined), and 'plan' (publish_base_data's
        plan, or None when nothing is to publish).
    """
    dry_run = resolve_dry_run(dry_run)
    base_data_dir = base_data_dir or os.path.join(os.path.expanduser("~"), "Files", "base_data")
    manifest_paths = find_base_data_manifests(base_data_dir) if manifest_paths is None else list(manifest_paths)
    if not manifest_paths:
        raise ValueError(f"No dataset manifests (*{MANIFEST_SUFFIX}) found under {base_data_dir}.")
    df = pd.concat([_read_manifest(p).assign(manifest=p) for p in manifest_paths], ignore_index=True)
    duplicates = df[df["ref_path"].duplicated(keep=False)]
    if len(duplicates):
        raise ValueError("These ref paths are listed more than once:\n  " + "\n  ".join(f"{r.ref_path} in {r.manifest}" for r in duplicates.itertuples()))
    unknown_tiers = df[~df["tier"].isin(TIERS)]
    if len(unknown_tiers):
        raise ValueError(f"A manifest row's tier is one of {', '.join(TIERS)}. These are not:\n  " + "\n  ".join(f"{r.ref_path}: '{r.tier}' in {r.manifest}" for r in unknown_tiers.itertuples()))
    client = client or cloud_utils.get_r2_client()
    current = (_read_latest_release(client)[0] or {}).get("datasets", {})

    rows = df.to_dict("records")
    for row in rows:
        row["path"] = os.path.join(base_data_dir, *row["ref_path"].split("/"))
    publishable = [row for row in rows if _is_publishable(row) and os.path.isfile(row["path"])]

    # Rasters an ingestion script listed without converting: convert them now (real runs only).
    is_pog = _run_each(lambda row: row["kind"] != "pog" or hb.is_path_pog(row["path"]), publishable, parallel, n_workers)
    needs_pog = [row for row, pog in zip(publishable, is_pog) if not pog]
    unclassed = [row["ref_path"] for row in needs_pog if not row["variable_class"]]
    if unclassed and not dry_run:
        raise ValueError(f"These rasters aren't POGs yet and their manifest rows declare no variable_class: {unclassed}")
    if not dry_run and needs_pog:
        def make_pog(numbered):
            n, row = numbered
            hb.log(f"Making POG {n}/{len(needs_pog)}: {row['ref_path']} ({row['variable_class']})")
            hb.make_path_pog(row["path"], variable_class=row["variable_class"], remove_displaced_files=True, remove_intermediate_files=remove_intermediate_files,
                             intermediate_dir=os.path.join(os.path.dirname(os.path.abspath(row["manifest"])), INTERMEDIATE_FOLDER, "publish_base_data_from_manifests"))
            hb.log(f"Made POG {n}/{len(needs_pog)}: {row['ref_path']}")
        failures = _run_each_collecting_failures(make_pog, list(enumerate(needs_pog, 1)), parallel, n_workers, label=lambda numbered: numbered[1]["ref_path"])
        if failures:
            raise RuntimeError("These rasters couldn't be made POGs, so nothing was published; the others are converted, and a rerun skips them:\n  "
                               + "\n  ".join(failures))
        needs_pog = []
    skip = {row["ref_path"] for row in needs_pog}

    # Hash every file that could be published (the slow part of every run).
    files = {row["ref_path"]: _get_tileset_files(row["path"], row["ref_path"]) if row["kind"] == "tileset" else [(row["path"], row["ref_path"])]
             for row in publishable if row["ref_path"] not in skip}  # a tile set is its VRT, then its tiles
    to_hash = [path for dataset_files in files.values() for path, _ in dataset_files]
    hashes = dict(zip(to_hash, _run_each(hb.hash_file_path, to_hash, parallel, n_workers)))

    statuses, rows_to_publish, unfinished = {}, [], []
    for row in rows:
        ref_path, path = row["ref_path"], row["path"]
        if ref_path in skip:
            statuses[ref_path] = "needs_pog"
        elif ref_path in current and current[ref_path].get("tier", "public") != row["tier"]:
            statuses[ref_path] = "tier_changed"
        elif row["tier"] == "unpublished":
            statuses[ref_path] = "unpublished"
        elif not _is_publishable(row):
            statuses[ref_path] = "unsupported"
        elif not os.path.isfile(path):
            statuses[ref_path] = "missing_locally"
        else:
            previous, sha256 = current.get(ref_path), hashes[path]
            dataset_sha256 = _get_tileset_sha256([(r, hashes[p]) for p, r in files[ref_path]]) if row["kind"] == "tileset" else _get_dataset_sha256(ref_path, sha256)
            if previous and previous["dataset_sha256"] == dataset_sha256:
                served = cloud_utils.read_r2_object_metadata(client, BUCKETS[row["tier"]], ref_path) or {}
                statuses[ref_path] = "unchanged" if served.get("sha256") == sha256 else "unfinished"
                if statuses[ref_path] == "unfinished":
                    unfinished.append((path, ref_path, sha256, BUCKETS[row["tier"]]))
            else:
                statuses[ref_path] = "changed" if previous else "new"
                rows_to_publish.append(row)
    statuses.update({r: "not_in_manifest" for r in current if r not in statuses})

    counts = pd.Series(statuses, dtype=str).value_counts().to_dict()
    hb.log(f"{len(manifest_paths)} manifests, {len(df)} rows, against {BUCKET}: {counts}" + "".join(f"\n  {s:16s} {r}" for r, s in statuses.items() if s not in ("unchanged", "unpublished")))
    if unclassed:
        hb.log(f"PROBLEM: these rasters aren't POGs yet and their manifest rows declare no variable_class: {unclassed}")
    if not dry_run:
        for i, (path, ref_path, sha256, bucket) in enumerate(unfinished, 1):  # finish what an interrupted run committed but didn't move into place
            cloud_utils.upload_path_to_r2(client, bucket, path, ref_path, metadata={"sha256": sha256, "md5": hb.hash_file_path(path, "md5")}, content_type=_get_content_type(ref_path),
                                          cache_control=CURRENT_CACHE_CONTROL, skip_if_exists=False, progress_label=f"Finishing {i}/{len(unfinished)} {ref_path}")
            client.delete_object(Bucket=bucket, Key=_get_staging_key(ref_path, sha256))
    plan = None
    if rows_to_publish:
        if not dry_run and not note:
            raise ValueError("Give a one-line change note to publish.")
        plan = publish_base_data([r["path"] for r in rows_to_publish], [r["ref_path"] for r in rows_to_publish], note or "(dry run)",
                                 *([r[k] for r in rows_to_publish] for k in ("license", "units", "data_source", "description", "code")),
                                 archive_previous=archive_previous, parallel=parallel, n_workers=n_workers, dry_run=dry_run, client=client,
                                 tier=[r["tier"] for r in rows_to_publish])
    if site_dir and not dry_run:
        if shutil.which("quarto"):
            write_base_data_index_pages(site_dir, base_data_dir, manifest_paths, dry_run=False, client=client)
        else:
            hb.log("Quarto isn't installed, so the pages of https://data.teemlabs.org weren't rebuilt.")
    return {"statuses": statuses, "manifests": manifest_paths, "plan": plan}

def write_base_data_index_pages(site_dir, base_data_dir=None, manifest_paths=None, output_dir=None, dry_run=True, client=None):
    """Build the browsable pages of https://data.teemlabs.org from the manifests and the latest release, and upload them.

    The landing page (index.html) is site_dir/_landing.html filled in with the latest release's numbers and a card per
    collection (a top-level folder). Every other folder holding published datasets, or above one, gets <folder>/index.html:
    site_dir/_folder_page.qmd filled in and rendered with Quarto. A folder's page shows its title and text from
    site_dir/_collections.yml, cards for its subfolders, the docstring of its ingestion script as its About section, and a
    table of its published files: their manifest rows, with each file's version, release, size, resolution, archived
    versions and a link to its yml sidecar. Metadata every row shares is shown once above the table. Manifest rows not yet
    published are left out. The order on a page: Metadata (the shared fields and the table), the subfolder cards and
    tree, then the docstring as Processing steps. A card shows the first sentences of its folder's text (_first_sentences);
    the folder's own page shows all of it.

    Args:
        site_dir (str): The templates, in earth_economy_devstack/docs/base_data.
        base_data_dir (str): The local base_data, searched for manifests. Defaults to ~/Files/base_data.
        manifest_paths (list): Use these manifests instead of searching base_data_dir.
        output_dir (str): Where to build the pages. Defaults to a new temporary folder.
        dry_run (bool or date): Build the pages only, to preview (python -m http.server -d <output_dir>); True by default. A date
            is read as in hb.resolve_dry_run.
        client: An S3 client for R2. Built from machine.env when not given.

    Returns:
        str: output_dir.
    """
    dry_run = resolve_dry_run(dry_run)
    quarto = shutil.which("quarto")
    if quarto is None:
        raise RuntimeError("Quarto isn't installed (https://quarto.org), so the pages can't be built.")
    base_data_dir = base_data_dir or os.path.join(os.path.expanduser("~"), "Files", "base_data")
    manifest_paths = find_base_data_manifests(base_data_dir) if manifest_paths is None else list(manifest_paths)
    client = client or cloud_utils.get_r2_client()
    release = _read_latest_release(client)[0]
    if release is None:
        raise ValueError(f"Nothing is published in {BUCKET} yet, so there are no pages to build.")
    with open(os.path.join(site_dir, "_collections.yml"), encoding="utf-8") as f:
        texts = yaml.safe_load(f) or {}

    # The published rows, each with its release entry, catalogue entry, archived versions and ingestion script.
    rows = []
    for manifest_path in manifest_paths:
        script_path = manifest_path[:-len(MANIFEST_SUFFIX)] + "_base_data_ingestion.py"
        rows += [dict(row, script_path=script_path, **release["datasets"][row["ref_path"]])
                 for row in _read_manifest(manifest_path).to_dict("records") if row["ref_path"] in release["datasets"]]
    rows.sort(key=lambda row: _natural_sort_key(row["ref_path"]))
    entries = _run_each(lambda row: cloud_utils.read_r2_json(client, BUCKET, f"_catalogue/{row['ref_path']}/{row['release']}.json")[0], rows)
    tiers = {entry.get("tier", "public") for entry in entries}
    archive_keys = {tier: cloud_utils.list_r2_keys(client, BUCKETS[tier], ARCHIVE_FOLDER + "/") for tier in tiers}
    for row, entry in zip(rows, entries):
        archive_folder = f"{ARCHIVE_FOLDER}/{os.path.splitext(row['ref_path'])[0]}/"
        row.update(tier=entry.get("tier", "public"),  # the tier it is published on, whatever its manifest row says now
                   size=sum(f["size"] for f in entry["files"]), rung=entry["lattice"]["rung"] if entry.get("lattice") else None,  # vectors and tables have no rung
                   archive_keys=[k for k in archive_keys[entry.get("tier", "public")] if k.startswith(archive_folder)],
                   tiles=entry["lattice"] if (entry.get("lattice") or {}).get("storage_form") == "tileset" else None)
    hb.log(f"Building pages for {len(rows)} published datasets of release {release['release']}.")

    rows_by_folder = {}
    for row in rows:
        rows_by_folder.setdefault(posixpath.dirname(row["ref_path"]), []).append(row)
    folders = sorted({"/".join(f.split("/")[:i + 1]) for f in rows_by_folder if f for i in range(f.count("/") + 1)})
    # A folder's title, tagline and text come from _collections.yml; a folder it doesn't list gets its tagline and text from
    # the first paragraph of its ingestion script's docstring, so a new folder arrives on the site with a real card.
    docstrings = {folder: _read_module_docstring(folder_rows[0]["script_path"]) for folder, folder_rows in rows_by_folder.items()}
    for folder in folders:
        if folder not in texts and docstrings.get(folder):
            texts[folder] = _get_docstring_texts(docstrings[folder])
    collections = [f for f in texts if f in folders and "/" not in f] + [f for f in folders if "/" not in f and f not in texts]
    def rows_under(folder):
        return [row for row in rows if row["ref_path"].startswith(folder + "/")]
    n_files = {f: len(rows_under(f)) for f in folders}  # on the pages a dataset is a folder such as lulc/esa, and its rows are files
    def chips(folder_rows):
        arcseconds = sorted({hb.token_to_arcseconds(row["rung"]) for row in folder_rows if row["rung"]})
        resolutions = _format_resolution(arcseconds[0]) + (f" to {_format_resolution(arcseconds[-1])}" if len(arcseconds) > 1 else "") if arcseconds else ""
        return (f'<ul class="chips"><li><b>{len(folder_rows)}</b> file{"s" if len(folder_rows) != 1 else ""}</li>'
                f'<li><b>{_format_size(sum(row["size"] for row in folder_rows))}</b></li>' + (f"<li>{resolutions}</li>" if resolutions else "") + "</ul>")
    def card(folder, link_class="card"):
        text = texts.get(folder, {})
        return (f'<a class="{link_class}" href="/{folder}/"><span class="path">{folder}/</span><h3>{html.escape(text.get("title", folder.rsplit("/", 1)[-1]))}</h3>'
                + (f'<p class="tagline">{html.escape(text["tagline"])}</p>' if text.get("tagline") else "")
                + (f'<p>{html.escape(_first_sentences(text["about"]))}</p>' if text.get("about") else "") + chips(rows_under(folder)) + '<div class="go">Browse &rarr;</div></a>')

    def folder_body(folder):
        text, here = texts.get(folder, {}), rows_by_folder.get(folder, [])
        body = [f'```{{=html}}\n<h1><span class="path">{folder}/</span>{html.escape(text.get("title", folder.rsplit("/", 1)[-1]))}</h1>\n'
                + (f'<p class="tagline">{html.escape(text["tagline"])}</p>\n' if text.get("tagline") else "") + chips(rows_under(folder)) + "\n```"]
        if text.get("about"):
            body.append(f'::: {{.lede}}\n{html.escape(text["about"])}\n:::')
        if here:  # the folder's own files first: the metadata they share, then the table, with each file's yml sidecar in its last column
            body.append("## Metadata\n\n```{=html}\n" + _get_dataset_table_html(here) + "\n```")
            for legend_name in sorted({row["legend"] for row in here if row.get("legend")}):  # each legend the folder's files name, read from beside their manifest
                legend_path = os.path.join(os.path.dirname(here[0]["script_path"]), legend_name)  # beside the manifest
                if os.path.exists(legend_path):
                    files = [posixpath.basename(row["ref_path"]) for row in here if row.get("legend") == legend_name]
                    first = os.path.join(base_data_dir, *next(row["ref_path"] for row in here if row.get("legend") == legend_name).split("/"))
                    body.append(f"## Legend\n\n```{{=html}}\n{_get_legend_html(legend_path, files, _get_header_colors_note(first))}\n```")
        for group, sentence, color_map, numbers in _get_color_ramp_sections(here, lambda row: os.path.join(base_data_dir, *row["ref_path"].split("/"))):
            files = [posixpath.basename(row["ref_path"]) for row in group]
            names = ", ".join(f"<code>{html.escape(n)}</code>" for n in files[:5]) + (f" and {len(files) - 5} more files" if len(files) > 5 else "")
            if numbers is not None:  # each raster's own two numbers, in a table that opens on demand
                sentence += f" The colour map is that of {files[0]}; every raster's numbers are in the folder's readme.md and in its manifest's color_ramp column."
            if not color_map and read_color_ramp(group[0]["color_ramp"])[0] != "divergent":  # an amount or a measure still without its numbers: a sentence, no bar
                body.append(f'## Colour ramp\n\n```{{=html}}\n<p class="legend-note">For {names}. {html.escape(sentence)}</p>\n```')
                continue
            stops = get_color_ramp_stops(group[0]["color_ramp"], -1, 1)
            gradient = ", ".join("rgba(%d,%d,%d,%.0f) %.0f%%" % (rgb + (alpha / 255, 100 * i / (len(stops) - 1))) for i, (_, rgb, alpha) in enumerate(stops))
            body.append(f'## Colour ramp\n\n```{{=html}}\n<p class="legend-note">For {names}. {html.escape(sentence)}</p>\n'
                        f'<div style="height:1.2em;max-width:28em;border:1px solid #888;background:linear-gradient(to right, {gradient})"></div>\n'
                        + (f"<details><summary>QGIS colour map (save as a .txt file; Layer Properties, Symbology, Singleband pseudocolor, Load Color Map from File)</summary>"
                           f"<pre>{html.escape(color_map)}</pre></details>" if color_map else "") + "\n```")
        children = [f for f in folders if posixpath.dirname(f) == folder]
        if children:
            # Three levels: a collection (top-level folder) holds datasets, and a dataset holds derived products. A card per direct
            # subfolder, then everything below this folder as a tree, as on the landing page but pared to this subtree.
            heading = "Datasets" if "/" not in folder else "Derived products"
            body.append(f"## {heading}\n\n```{{=html}}\n<div class=\"cards\">" + "".join(card(f) for f in children) + "</div>\n"
                        + _get_folder_tree_html(folders, texts, n_files, root=folder) + "\n```")
        if here and docstrings.get(folder):  # the ingestion script's docstring, rendered by Quarto as Markdown
            script_ref = "base_data/" + os.path.relpath(here[0]["script_path"], base_data_dir).replace(os.sep, "/")
            body.append(f"## Processing steps\n\n{_get_docstring_markdown(docstrings[folder])}\n\n"
                        f'```{{=html}}\n<p class="source-note">From the ingestion script that made these files, <code>{script_ref}</code>.</p>\n```')
        return "\n\n".join(body)

    # The folder pages: fill the template for each folder and render them all with Quarto, in a project of their own.
    output_dir = output_dir or tempfile.mkdtemp(prefix="base_data_site_")
    built_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with open(os.path.join(site_dir, "_folder_page.qmd"), encoding="utf-8") as f:
        folder_template = f.read()
    with tempfile.TemporaryDirectory() as project_dir:
        shutil.copy(os.path.join(site_dir, "_styles.css"), os.path.join(project_dir, "styles.css"))
        shutil.copy(os.path.join(site_dir, "teems_logo.png"), project_dir)
        with open(os.path.join(project_dir, "_quarto.yml"), "w", encoding="utf-8") as f:
            f.write("project:\n  type: default\n  output-dir: _site\n")
        for folder in folders:
            parts = folder.split("/")
            crumbs = ['<a href="/">data.teemlabs.org</a>'] + [f'<a href="/{"/".join(parts[:i + 1])}/">{p}</a>' for i, p in enumerate(parts[:-1])] + [f"<span>{parts[-1]}</span>"]
            title = texts.get(folder, {}).get("title", parts[-1])
            page = _fill_placeholders(folder_template, page_title=json.dumps(f"{title} · TEEMs Base Data"),
                                      description=json.dumps(texts.get(folder, {}).get("tagline", f"The {folder} folder of the TEEMs base data store.")),
                                      root="../" * len(parts), breadcrumbs='<span class="sep">/</span>'.join(crumbs), body=folder_body(folder),
                                      release=release["release"], built_at=built_at)
            os.makedirs(os.path.join(project_dir, folder), exist_ok=True)
            with open(os.path.join(project_dir, folder, "index.qmd"), "w", encoding="utf-8") as f:
                f.write(page)
        subprocess.run([quarto, "render", project_dir, "--quiet"], check=True)
        for folder in folders:
            os.makedirs(os.path.join(output_dir, folder), exist_ok=True)
            shutil.copy(os.path.join(project_dir, "_site", folder, "index.html"), os.path.join(output_dir, folder, "index.html"))

    # The landing page.
    newest = [row for row in rows if row["release"] == release["release"]] or rows
    example = newest[-1]["ref_path"]
    total = sum(row["size"] for row in rows)
    with open(os.path.join(site_dir, "_landing.html"), encoding="utf-8") as f:
        landing_template = f.read()
    with open(os.path.join(site_dir, "_styles.css"), encoding="utf-8") as f:
        styles = f.read()
    landing = _fill_placeholders(landing_template, styles=styles, n_datasets=len(rows), n_collections=len(collections),
                                 total_size=f"{total / (1e9 if total >= 1e9 else 1e6):.1f}", total_size_unit="GB" if total >= 1e9 else "MB",
                                 release=release["release"], release_date=release["created_at"][:10], release_note=html.escape(release.get("note") or ""),
                                 collection_cards="\n".join(card(f) for f in collections), example_ref=example,
                                 folder_tree=_get_folder_tree_html(folders, texts, n_files),
                                 example_archive=_get_archive_key(example, release["release"]), built_at=built_at)
    with open(os.path.join(output_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(landing)
    shutil.copy(os.path.join(site_dir, "teems_logo.png"), output_dir)

    pages = ["index.html"] + [f"{folder}/index.html" for folder in folders]
    if dry_run:
        hb.log(f"Built {len(pages)} pages in {output_dir}; nothing uploaded. To preview: python -m http.server -d {output_dir}")
        return output_dir
    for key in pages + ["teems_logo.png"]:
        cloud_utils.upload_path_to_r2(client, BUCKET, os.path.join(output_dir, *key.split("/")), key, content_type=mimetypes.guess_type(key)[0],
                                      cache_control=PAGE_CACHE_CONTROL, skip_if_exists=False)
    hb.log(f"Uploaded {len(pages)} pages to https://data.teemlabs.org.")
    return output_dir

def publish_base_data(sources, ref_paths, note, license, units, data_source, description, code=None, archive_previous=True, parallel=True, n_workers=None,
                      dry_run=False, client=None, tier="public"):
    """Publish datasets (POG rasters, GeoPackage vectors, CSV or XLSX tables, and POG tile sets by their VRT) into the base data store as one release.

    A dataset's files go to the bucket of its tier: the public one, served at data.teemlabs.org, or the internal one, read
    with a token or behind a login at internal.teemlabs.org. The release, the catalogue entries and the pages are in the
    public bucket for both, so an internal dataset is listed and described openly and only its bytes need credentials.

    A tile set's tiles are uploaded to their own paths beside its VRT before the commit, each once: a tile already served
    with the same bytes is skipped, so publishing a set again as it grows uploads only the new tiles. Its VRT is staged,
    committed and moved into place like any single file, and its earlier versions aren't archived.

    Args:
        sources (str | list): Local file paths, one per dataset.
        ref_paths (str | list): Destination ref paths, in the same order.
        note (str): One-line change note.
        license (str | list): Licence identifier, e.g. 'CC-BY-4.0'. This and the metadata below are given once for
            every dataset, or as a list with one value per dataset.
        units (str | list): Units of the values.
        data_source (str | list): Where the data come from.
        description (str | list): What the data are and how to interpret them.
        code (str | list): The code that produced the files.
        archive_previous (bool): When a dataset already has a version, keep that version under static/ before its plain
            path is overwritten. False saves the storage: the old version is then gone, and its successor's catalogue
            entry records that it wasn't archived.
        parallel (bool): Run the gate (POG validation and hashing) on several datasets at a time (the default), on
            n_workers threads. Uploads go one file at a time either way; boto3 already uploads each file's parts in parallel.
        n_workers (int): Threads when parallel. Defaults to one less than the CPUs this process may use.
        dry_run (bool or date): Gate and plan only; write nothing. Works without credentials, against an empty store. A date is
            read as in hb.resolve_dry_run.
        client: An S3 client for R2. Built from machine.env when not given.
        tier (str | list): 'public' (the default) or 'internal', once or per dataset. A published dataset can't change
            tier here: retire it first (retire_base_data).

    Returns:
        dict: The release ID, parent release, per-dataset plan, problems found, and whether anything was written.
    """
    dry_run = resolve_dry_run(dry_run)
    sources = [sources] if isinstance(sources, str) else list(sources)
    ref_paths = [ref_paths] if isinstance(ref_paths, str) else list(ref_paths)
    if len(sources) != len(ref_paths):
        raise ValueError("Give one ref path per source.")
    metadata = {k: list(v) if isinstance(v, (list, tuple)) else [v] * len(sources)
                for k, v in dict(license=license, units=units, data_source=data_source, description=description, code=code, tier=tier).items()}
    if any(len(v) != len(sources) for v in metadata.values()):
        raise ValueError("Give each piece of metadata once, or once per source.")
    client = client or cloud_utils.get_r2_client()
    if client is None and not dry_run:
        raise RuntimeError("No R2 credentials: set HB_R2_ACCOUNT_ID, HB_R2_ACCESS_KEY_ID and HB_R2_SECRET_ACCESS_KEY in machine.env.")

    # The parent release and the next release ID (YYYY.MM.DD.N, N counting up within a day).
    parent, parent_etag = _read_latest_release(client)
    current = parent["datasets"] if parent else {}
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y.%m.%d")
    same_day = parent and parent["release"].startswith(today + ".")
    release_id = f"{today}.{int(parent['release'].rsplit('.', 1)[1]) + 1 if same_day else 1}"

    # The gate.
    problems = [] if note else ["a one-line change note is required"]
    datasets = []
    checked = _run_each(lambda pair: check_publication_status(*pair), list(zip(sources, ref_paths)), parallel, n_workers)
    for i, (dataset, ref_path) in enumerate(zip(checked, ref_paths)):
        dataset["metadata"] = {k: v[i] for k, v in metadata.items()}
        absent = [k for k in ("license", "units", "data_source", "description") if not dataset["metadata"][k]]
        if absent:
            dataset["problems"].append(f"these are required: {absent}")
        previous = current.get(ref_path)
        if dataset["metadata"]["tier"] not in BUCKETS:
            raise ValueError(f"{ref_path}: its tier is '{dataset['metadata']['tier']}', and only {', '.join(BUCKETS)} are published.")
        dataset["bucket"] = BUCKETS[dataset["metadata"]["tier"]]
        if previous and previous.get("tier", "public") != dataset["metadata"]["tier"]:
            dataset["problems"].append(f"published on the {previous.get('tier', 'public')} tier; retire it before publishing it as {dataset['metadata']['tier']}")
        if previous and previous["dataset_sha256"] == dataset.get("dataset_sha256"):
            dataset["problems"].append(f"identical to the current version {previous['version']}")
        missing = [r for r in dataset.get("depends_on", []) if r not in current and r not in ref_paths]
        if missing:
            dataset["problems"].append(f"depends on datasets that are not published: {missing}")
        dataset["version"] = previous["version"] + 1 if previous else 1
        dataset["previous"] = previous
        dataset["archive_key"] = _get_archive_key(ref_path, previous["release"]) if previous and archive_previous and dataset["kind"] != "tileset" else None
        if dataset["archive_key"] and client:  # what gets archived is whatever the plain path serves, so it must be the published version
            served = cloud_utils.read_r2_object_metadata(client, dataset["bucket"], ref_path) or {}
            if _get_dataset_sha256(ref_path, served.get("sha256", "")) != previous["dataset_sha256"]:
                dataset["problems"].append("its plain path doesn't hold the published version; run the manifest command once to finish the previous release")
        problems += [f"{ref_path}: {p}" for p in dataset.pop("problems")]
        datasets.append(dataset)

    plan = {"release": release_id, "parent": parent["release"] if parent else None, "problems": problems, "written": False,
            "datasets": [{"ref_path": d["ref_path"], "version": d["version"], "size": d.get("size"), "dataset_sha256": d.get("dataset_sha256"),
                          "archive_key": d["archive_key"]} for d in datasets]}
    hb.log(f"{'Dry run' if dry_run else 'Publishing'}: release {release_id} of {BUCKET} (parent {plan['parent']}), {len(datasets)} datasets, "
           f"{sum(d.get('size') or 0 for d in datasets) / 1e6:,.1f} MB" + "".join(f"\n  PROBLEM {p}" for p in problems))
    if dry_run:
        return plan
    if problems:
        raise ValueError("Publication refused:\n  " + "\n  ".join(problems))

    # Stage the new bytes and archive the versions being replaced. Neither changes anything a reader sees.
    for i, d in enumerate(datasets, 1):
        f = d["files"][0]
        cloud_utils.upload_path_to_r2(client, d["bucket"], d["source_path"], _get_staging_key(d["ref_path"], f["sha256"]),
                                      metadata={"sha256": f["sha256"], "md5": f["md5"]}, content_type=_get_content_type(d["ref_path"]),
                                      progress_label=f"Uploading {i}/{len(datasets)} {d['ref_path']}")
        for n, (tile, tile_path) in enumerate(zip(d["files"][1:], d["source_paths"][1:]), 1):  # a tile set's tiles, straight to their own paths
            if (cloud_utils.read_r2_object_metadata(client, d["bucket"], tile["ref_path"]) or {}).get("sha256") != tile["sha256"]:
                cloud_utils.upload_path_to_r2(client, d["bucket"], tile_path, tile["ref_path"], metadata={"sha256": tile["sha256"], "md5": tile["md5"]},
                                              content_type=_get_content_type(tile["ref_path"]), cache_control=CURRENT_CACHE_CONTROL, skip_if_exists=False,
                                              progress_label=f"Uploading tile {n}/{len(d['files']) - 1} of {d['ref_path']}")
        if d["archive_key"] and cloud_utils.read_r2_object_metadata(client, d["bucket"], d["archive_key"]) is None:
            served = cloud_utils.read_r2_object_metadata(client, d["bucket"], d["ref_path"])
            cloud_utils.copy_r2_object(client, d["bucket"], d["ref_path"], d["archive_key"], metadata=served, content_type=_get_content_type(d["ref_path"]),
                                       progress_label=f"Archiving inside R2 {i}/{len(datasets)} {d['ref_path']} as {d['archive_key']}")

    # Claim the release ID, write the entries, then commit. Only the commit makes the release visible.
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    snapshot = {"release": release_id, "parent": plan["parent"], "created_at": now, "created_by": getpass.getuser(), "note": note,
                "datasets": dict(current, **{d["ref_path"]: {"dataset_sha256": d["dataset_sha256"], "version": d["version"], "release": release_id, "tier": d["metadata"]["tier"]} for d in datasets})}
    written = []
    try:
        cloud_utils.write_r2_json(client, BUCKET, f"_release/{release_id}.json", snapshot, IfNoneMatch="*")
        written.append(f"_release/{release_id}.json")
        for d in datasets:
            m = d["metadata"]
            entry = {"dataset": d["ref_path"], "kind": d["kind"], "tier": m["tier"], "version": d["version"], "dataset_sha256": d["dataset_sha256"], "release": release_id,
                     "previous": dict(d["previous"], archive_key=d["archive_key"]) if d["previous"] else None,  # archive_key None: not archived
                     "lattice": d["lattice"], "semantics": dict(d["semantics"] or {}, units=m["units"]), "files": d["files"],  # lattice None: not a raster
                     "depends_on": d["depends_on"], "license": {"id": m["license"]}, "description": m["description"],
                     "provenance": {"source": m["data_source"], "code": m["code"], "promoted_from": None, "published_by": getpass.getuser(),
                                    "published_at": now, "note": note}}  # promoted_from: the submission it was promoted from (none until that route exists)
            cloud_utils.write_r2_json(client, BUCKET, f"_catalogue/{d['ref_path']}/{release_id}.json", entry, IfNoneMatch="*")
            written.append(f"_catalogue/{d['ref_path']}/{release_id}.json")
        conditions = {"IfMatch": parent_etag} if parent_etag else {"IfNoneMatch": "*"}
        cloud_utils.write_r2_json(client, BUCKET, LATEST_KEY, {"release": release_id}, cache_control="no-cache", **conditions)
    except Exception as e:
        if cloud_utils.get_r2_error_status(e) not in (409, 412):
            raise
        for key in written:
            client.delete_object(Bucket=BUCKET, Key=key)
        raise RuntimeError("Another release was published first, so nothing from this run was. Rerun to publish on top of it.") from e
    plan["written"] = True

    # The release is committed: move each new version into its plain path, overwriting the old one there.
    hb.log(f"Committed release {release_id}; moving {len(datasets)} staged files into their plain paths (a copy inside R2: nothing is uploaded again).")
    unfinished = []
    for i, d in enumerate(datasets, 1):
        f = d["files"][0]
        try:
            cloud_utils.copy_r2_object(client, d["bucket"], _get_staging_key(d["ref_path"], f["sha256"]), d["ref_path"], metadata={"sha256": f["sha256"], "md5": f["md5"]},
                                       content_type=_get_content_type(d["ref_path"]), cache_control=CURRENT_CACHE_CONTROL,
                                       progress_label=f"Moving into place inside R2 {i}/{len(datasets)} {d['ref_path']}")
            client.delete_object(Bucket=d["bucket"], Key=_get_staging_key(d["ref_path"], f["sha256"]))
        except Exception as e:
            unfinished.append(f"{d['ref_path']} ({e})")
    if unfinished:
        raise RuntimeError(f"Release {release_id} is committed, but these plain paths still serve their previous bytes: {unfinished}. "
                           "Run the manifest command again to finish them.")
    hb.log(f"Published release {release_id}.")
    return plan

def retire_base_data(ref_paths, note, remove_archived=False, site_dir=None, base_data_dir=None, dry_run=True, client=None):
    """Withdraw published datasets from the public base data store, as one release that no longer lists them.

    The release is committed first (the same compare-and-swap on _release/latest.json as publishing), then each dataset's
    files are deleted: its plain path and a tile set's tiles (from its tier's bucket), and its yml sidecar, with the page of any folder left holding
    no published dataset. Its catalogue entries stay, as the record of what was published. A file already deleted by hand
    is no obstacle: retiring it then only corrects the release. The local files and the manifests are not touched; a
    retired dataset whose manifest row is still 'public' is published again by the next publish.

    Args:
        ref_paths (str | list): Ref paths of the published datasets to withdraw.
        note (str): One-line change note.
        remove_archived (bool): Also delete the datasets' earlier versions under static/. They are kept by default.
        site_dir (str): Folder of the site's templates (docs/base_data in earth_economy_devstack). When given, the pages
            of https://data.teemlabs.org are rebuilt after a real run, if Quarto is installed.
        base_data_dir (str): The base data directory, for rebuilding the pages. Defaults to ~/Files/base_data.
        dry_run (bool or date): Plan only; write and delete nothing (the default). A date is read as in hb.resolve_dry_run.
        client: An S3 client for R2. Built from machine.env when not given.

    Returns:
        dict: The release ID, parent release, the ref paths retired, the keys deleted, problems found, and whether anything was written.
    """
    dry_run = resolve_dry_run(dry_run)
    ref_paths = [ref_paths] if isinstance(ref_paths, str) else list(ref_paths)
    client = client or cloud_utils.get_r2_client()
    if client is None:
        raise RuntimeError("No R2 credentials: set HB_R2_ACCOUNT_ID, HB_R2_ACCESS_KEY_ID and HB_R2_SECRET_ACCESS_KEY in machine.env.")
    parent, parent_etag = _read_latest_release(client)
    current = parent["datasets"] if parent else {}
    problems = ([] if note else ["a one-line change note is required"]) + [f"{r}: not in the latest release" for r in ref_paths if r not in current]
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y.%m.%d")
    same_day = parent and parent["release"].startswith(today + ".")
    release_id = f"{today}.{int(parent['release'].rsplit('.', 1)[1]) + 1 if same_day else 1}"
    remaining = {r: d for r, d in current.items() if r not in ref_paths}

    # What to delete: each dataset's files as its catalogue entry lists them, its sidecar, and the pages of folders left empty.
    keys = set()  # (bucket, key): a dataset's files are in its tier's bucket, its sidecar and the pages in the public one
    for ref_path in (r for r in ref_paths if r in current):
        entry = cloud_utils.read_r2_json(client, BUCKET, f"_catalogue/{ref_path}/{current[ref_path]['release']}.json")[0] or {}
        bucket = BUCKETS[entry.get("tier", "public")]
        keys |= {(bucket, f["ref_path"]) for f in entry.get("files", [])} | {(bucket, ref_path), (BUCKET, ref_path + ".yml")}
        if remove_archived:
            keys |= {(bucket, k) for k in cloud_utils.list_r2_keys(client, bucket, f"{ARCHIVE_FOLDER}/{os.path.splitext(ref_path)[0]}/")}
        folder = posixpath.dirname(ref_path)
        while folder and not any(r.startswith(folder + "/") for r in remaining):
            keys.add((BUCKET, folder + "/index.html"))
            folder = posixpath.dirname(folder)
    buckets_and_keys = sorted(keys, key=lambda pair: (pair[1], pair[0]))
    keys = [key for _, key in buckets_and_keys]

    plan = {"release": release_id, "parent": parent["release"] if parent else None, "retired": ref_paths, "deleted": keys, "problems": problems, "written": False}
    hb.log(f"{'Dry run' if dry_run else 'Retiring'}: release {release_id} of {BUCKET} (parent {plan['parent']}) withdraws {len(ref_paths)} datasets and deletes {len(keys)} keys"
           + "".join(f"\n  {key}" + (f"  (in {bucket})" if bucket != BUCKET else "") for bucket, key in buckets_and_keys) + "".join(f"\n  PROBLEM {p}" for p in problems))
    if dry_run:
        return plan
    if problems:
        raise ValueError("Retirement refused:\n  " + "\n  ".join(problems))

    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    snapshot = {"release": release_id, "parent": plan["parent"], "created_at": now, "created_by": getpass.getuser(), "note": note, "retired": ref_paths, "datasets": remaining}
    try:
        cloud_utils.write_r2_json(client, BUCKET, f"_release/{release_id}.json", snapshot, IfNoneMatch="*")
        cloud_utils.write_r2_json(client, BUCKET, LATEST_KEY, {"release": release_id}, cache_control="no-cache", IfMatch=parent_etag)
    except Exception as e:
        if cloud_utils.get_r2_error_status(e) not in (409, 412):
            raise
        raise RuntimeError("Another release was published first, so nothing was retired. Rerun to retire on top of it.") from e
    plan["written"] = True
    for bucket, key in buckets_and_keys:  # the release is committed: nothing lists these any more
        client.delete_object(Bucket=bucket, Key=key)
    hb.log(f"Retired {len(ref_paths)} datasets in release {release_id}.")
    if site_dir:
        if shutil.which("quarto"):
            write_base_data_index_pages(site_dir, base_data_dir, dry_run=False, client=client)
        else:
            hb.log("Quarto isn't installed, so the pages of https://data.teemlabs.org weren't rebuilt.")
    return plan

def check_publication_status(source_path, ref_path):
    """Gate one dataset (a POG, a GeoPackage, a table, or a POG tile set by its VRT) and describe it for the catalogue. 'problems' is empty when it passes.

    POG conformance (variable class, nodata convention, overviews and their rule, exact statistics, COG layout) is entirely
    hb.is_path_pog's job. Only the store's own rules are checked here: how ref paths are named, and what publishing supports.
    A vector or table is taken as it is: it gets files and hashes but no lattice or semantics. A tile set is gated by
    hb.is_path_pog_tileset; its files are its VRT, then its tiles, and its lattice says how many tiles it has and whether it
    is partial (its VRT is named <stem>_partial.vrt)."""
    extension = os.path.splitext(ref_path)[1].lower()
    d = {"ref_path": ref_path, "source_path": source_path, "problems": [], "kind": KINDS_BY_EXTENSION.get(extension, "other"), "depends_on": [],
         "lattice": None, "semantics": None}
    components = ref_path.split("/")
    if ref_path.startswith(("/", "_")) or "\\" in ref_path or any(not re.fullmatch(r"[a-z0-9][a-z0-9_.\-]*", c) for c in components):
        d["problems"].append("ref path must be relative, lowercase, forward-slashed, and must not start with '_'")
    if components[0] == ARCHIVE_FOLDER:
        d["problems"].append(f"ref paths must not start with '{ARCHIVE_FOLDER}/', which holds archived versions")
    if any(t in REVISION_TOKENS or re.fullmatch(r"v\d+", t) for t in os.path.splitext(components[-1])[0].split("_")):
        d["problems"].append("file names carry meaning, never revisions such as _v2 or _final")
    if extension not in CONTENT_TYPES:
        d["problems"].append(f"publishing supports .tif POGs, .gpkg vectors, .csv or .xlsx tables and .vrt tile sets, not {extension or 'no extension'}")
        return d
    if os.path.splitext(source_path)[1].lower() != extension or not os.path.isfile(source_path):
        d["problems"].append(f"need an existing {extension} source for a {extension} ref path: {source_path}")
        return d
    if extension == ".tif":
        if not hb.is_path_pog(source_path, full_check=True):
            d["problems"].append("fails hb.is_path_pog(full_check=True); run it with verbose=True to see why")
            return d
        pog = hb.get_pog_info(source_path)
        if pog["observed_area"]:
            d["problems"].append("POGs with an observed-area companion can't be published yet")
        if pog["denominator"] == "ha_per_cell":
            d["depends_on"] = [hb.pyramid_ha_per_cell_ref_paths[pog["arcseconds"]].replace(os.sep, "/")]
        else:
            d["depends_on"] = [posixpath.normpath(posixpath.join(posixpath.dirname(ref_path), pog["denominator"]))] if pog["denominator"] else []
        d["lattice"] = {"rung": pog["rung"], "storage_form": "pog", "extent": pog["bounding_box"]}
        d["semantics"] = {k: pog[k] for k in ("variable_class", "intensive_weighting", "denominator", "stats")}
    files = [(source_path, ref_path)]
    if extension == ".vrt":
        if not hb.is_path_pog_tileset(source_path):
            d["problems"].append("fails hb.is_path_pog_tileset; run it with verbose=True to see why")
            return d
        files = _get_tileset_files(source_path, ref_path)
        if any(tile_ref_path.startswith("../") for _, tile_ref_path in files):
            d["problems"].append("a tile set's tiles must be in or below its VRT's folder")
            return d
        pog = hb.get_pog_info(files[1][0])  # what every tile declares
        if pog["observed_area"]:
            d["problems"].append("tile sets with an observed-area companion can't be published yet")
        d["depends_on"] = [hb.pyramid_ha_per_cell_ref_paths[pog["arcseconds"]].replace(os.sep, "/")] if pog["denominator"] == "ha_per_cell" else []
        d["lattice"] = {"rung": pog["rung"], "storage_form": "tileset", "extent": [-180.0, -90.0, 180.0, 90.0], "tile_degrees": hb.parse_tile_filename(files[1][0])[3],
                        "n_tiles": len(files) - 1, "partial": ref_path.endswith(PARTIAL_SUFFIX)}
        d["semantics"] = dict({k: pog[k] for k in ("variable_class", "intensive_weighting", "denominator")}, stats=None)  # each tile's header has its own
    d["source_paths"] = [path for path, _ in files]
    d["files"] = _run_each(lambda f: {"ref_path": f[1], "size": os.path.getsize(f[0]), "sha256": hb.hash_file_path(f[0]), "md5": hb.hash_file_path(f[0], "md5")}, files)
    d["size"] = sum(f["size"] for f in d["files"])
    d["dataset_sha256"] = _get_tileset_sha256([(f["ref_path"], f["sha256"]) for f in d["files"]]) if extension == ".vrt" else _get_dataset_sha256(ref_path, d["files"][0]["sha256"])
    return d

def _is_publishable(row):
    """Whether a manifest row is of a kind and tier publishing supports: a public or internal single file of a known extension, or tile set's VRT."""
    return row["tier"] in BUCKETS and row["kind"] in ("pog", "vector", "table", "tileset") and os.path.splitext(row["ref_path"])[1].lower() in CONTENT_TYPES

def _get_content_type(ref_path):
    return CONTENT_TYPES[os.path.splitext(ref_path)[1].lower()]

def _read_latest_release(client):
    """The latest release and the ETag of _release/latest.json, or (None, None) before the first release or without a client."""
    latest, etag = cloud_utils.read_r2_json(client, BUCKET, LATEST_KEY) if client else (None, None)
    if latest is None:
        return None, None
    return cloud_utils.read_r2_json(client, BUCKET, f"_release/{latest['release']}.json")[0], etag

def _get_archive_key(ref_path, release_id):
    """Where an archived version lives: static/<ref path without extension>/v<release that published it, dots as underscores><extension>."""
    stem, extension = os.path.splitext(ref_path)
    return f"{ARCHIVE_FOLDER}/{stem}/v{release_id.replace('.', '_')}{extension}"

def _get_staging_key(ref_path, sha256):
    """Where a file's new bytes wait until their release is committed."""
    return f"_staging/{ref_path}/{sha256[:16]}{os.path.splitext(ref_path)[1]}"

def _get_dataset_sha256(ref_path, sha256):
    """A single-file dataset's content version: the sha256 of its one 'ref_path<TAB>sha256' line."""
    return hashlib.sha256(f"{ref_path}\t{sha256}\n".encode("utf-8")).hexdigest()

def _get_tileset_sha256(files):
    """A tile set's content version: the sha256 of the 'ref_path<TAB>sha256' lines of its VRT and tiles, sorted. files is (ref path, sha256) pairs."""
    return hashlib.sha256("".join(f"{ref_path}\t{sha256}\n" for ref_path, sha256 in sorted(files)).encode("utf-8")).hexdigest()

def _get_tileset_files(vrt_path, ref_path):
    """A tile set's files as (local path, ref path) pairs: its VRT, then the tiles the VRT lists, sorted, each at its place relative to the VRT."""
    from osgeo import gdal
    ds = gdal.Open(vrt_path)
    tile_paths = sorted(ds.GetFileList()[1:]) if ds is not None else []
    ds = None
    folder = os.path.dirname(os.path.abspath(vrt_path))
    return [(vrt_path, ref_path)] + [(t, posixpath.normpath(posixpath.join(posixpath.dirname(ref_path), os.path.relpath(os.path.abspath(t), folder).replace(os.sep, "/")))) for t in tile_paths]

def _read_manifest(manifest_path):
    """A dataset manifest as a DataFrame of strings, checked for the expected columns."""
    df = pd.read_csv(manifest_path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    missing = [c for c in MANIFEST_COLUMNS if c not in df.columns and c not in OPTIONAL_MANIFEST_COLUMNS]
    if missing:
        raise ValueError(f"The manifest {manifest_path} lacks the columns {missing}.")
    for column in OPTIONAL_MANIFEST_COLUMNS:
        if column not in df.columns:
            df[column] = ""
    return df[list(MANIFEST_COLUMNS)]

def _run_each(function, items, parallel=True, n_workers=None):
    """function(item) for every item, results in item order: on threads when parallel, otherwise one at a time.

    Threads rather than processes: the work here is GDAL, numpy and hashing, which release Python's lock, and spawned
    processes would re-run a flat ingestion or publishing script. Exceptions propagate."""
    if not parallel or len(items) < 2:
        return [function(item) for item in items]
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(n_workers or max(1, hb.available_cpu_count() - 1), len(items))) as pool:
        return list(pool.map(function, items))

def _run_each_collecting_failures(function, items, parallel=True, n_workers=None, label=str):
    """Like _run_each, but every item runs even if some fail. Returns one 'label: error' line per failed item."""
    def attempt(item):
        try:
            function(item)
        except Exception as e:
            return f"{label(item)}: {type(e).__name__}: {e}"
    return [failure for failure in _run_each(attempt, items, parallel, n_workers) if failure]

def _get_dataset_table_html(rows):
    """A folder's published datasets as HTML: the metadata every row shares, once, then a table with one row per file (the Resolution
    cell of a vector or table names its kind instead). An internal file is listed like any other, marked as requiring credentials, its links going to
    the address behind the login. The last column links each file's geometamaker yml sidecar (<its URL>.yml,
    written by linneabean.metadata at publish time)."""
    shared = [(k, label) for k, label in PAGE_FIELDS if len({row[k] for row in rows}) == 1]
    varying = [(k, label) for k, label in PAGE_FIELDS if (k, label) not in shared]
    lines = ['<dl class="shared">' + "".join(f"<dt>{label}</dt><dd>{_linkify(rows[0][k])}</dd>" for k, label in shared if rows[0][k]) + "</dl>",
             '<div class="table-wrap"><table class="datasets"><thead><tr>'
             + "".join(f"<th>{h}</th>" for h in ["File", "Version", "Release", "Size", "Resolution"] + [label for _, label in varying] + ["Earlier versions", "Metadata"])
             + "</tr></thead><tbody>"]
    for row in rows:
        tier = row.get("tier", "public")
        url = URLS[tier]  # an internal file's links go to the address behind the login
        archives = "".join(f'<a class="archive" href="{url}/{k}">{posixpath.splitext(posixpath.basename(k))[0][1:].replace("_", ".")}</a>'
                           for k in row["archive_keys"])
        lines.append(f'<tr><td class="file"><a href="{url}/{row["ref_path"]}" download>{posixpath.basename(row["ref_path"])}</a>'
                     + (' <span class="pill credentials" title="Not a free download: sign in at internal.teemlabs.org, or read it with an access token.">requires credentials</span>' if tier == "internal" else "")
                     + (f' <span class="pill">{"partial tile set" if row["tiles"]["partial"] else "tile set"}: {row["tiles"]["n_tiles"]} tiles</span>' if row.get("tiles") else "") + "</td>"
                     f'<td><span class="pill">v{row["version"]}</span></td><td class="num">{row["release"]}</td><td class="num">{_format_size(row["size"])}</td>'
                     f'<td class="num">{_format_resolution(hb.token_to_arcseconds(row["rung"])) if row.get("rung") else row["kind"]}</td>'  # a vector or table: its kind
                     + "".join(f'<td class="meta">{_linkify(row[k])}</td>' for k, _ in varying) + f"<td>{archives or '&ndash;'}</td>"
                     f'<td class="yml"><a class="sidecar" href="https://data.teemlabs.org/{row["ref_path"]}.yml">yml</a></td></tr>')
    return "\n".join(lines + ["</tbody></table></div>"])

def _has_color_table(raster_path):
    """Whether the first band of a raster carries a colour table in its header."""
    from osgeo import gdal
    ds = gdal.Open(raster_path)
    has = ds is not None and ds.GetRasterBand(1).GetColorTable() is not None
    ds = None
    return has

def _get_header_colors_note(raster_path):
    """One sentence for a legend's readers on whether the rasters show its colours by themselves, judged by the header of one of them."""
    if os.path.exists(raster_path) and _has_color_table(raster_path):
        return "The same colours are in each raster's header, so a viewer shows them unasked."
    return "These rasters were built before the legend was written, so their headers carry no colour table: load the colour map below to see the classes in their colours."

def _get_legend_html(legend_path, file_names, header_colors_note=""):
    """A legend for a folder page: which files it describes, a row per class with a swatch of its colour, and the QGIS colour map to copy."""
    legend = read_base_data_legend(legend_path)
    files = ", ".join(f"<code>{html.escape(name)}</code>" for name in file_names[:5]) + (f" and {len(file_names) - 5} more files" if len(file_names) > 5 else "")
    lines = [f'<p class="legend-note">The classes of {files}. {html.escape(header_colors_note)}</p>',
             '<div class="table-wrap"><table class="datasets legend"><thead><tr><th></th><th>Value</th><th>Label</th><th>Name</th><th>Colour</th><th>Description</th></tr></thead><tbody>']
    lines += [f'<tr><td><span style="display:inline-block;width:1.1em;height:1.1em;border:1px solid #888;background:{r["color"]}"></span></td><td class="num">{r["id"]}</td>'
              f'<td><code>{html.escape(r["label"])}</code></td><td>{html.escape(r["name"])}</td><td><code>{r["color"]}</code></td><td class="meta">{_linkify(r["description"])}</td></tr>'
              for r in legend.to_dict("records")]
    lines += ["</tbody></table></div>", "<details><summary>QGIS colour map (save as a .txt file; Layer Properties, Symbology, Paletted/Unique values, Load Color Map from File)</summary>"
              f"<pre>{html.escape(get_qgis_color_map(legend_path))}</pre></details>"]
    return "\n".join(lines)

def _read_module_docstring(script_path):
    """The module docstring of a Python file, or None when the file is missing or has none."""
    if not os.path.exists(script_path):
        return None
    return ast.get_docstring(ast.parse(open(script_path, encoding="utf-8").read()))

def _get_docstring_texts(docstring):
    """Card text for a folder _collections.yml doesn't list: the docstring's first paragraph as 'about', and its first sentence as
    'tagline' ('about' is left empty when the paragraph is that one sentence, so a card doesn't say it twice)."""
    paragraph = " ".join(line.strip() for line in re.split(r"\n\s*\n", docstring.strip())[0].split("\n"))
    match = re.match(r"(.+?[.!?])(?:\s|$)", paragraph)
    tagline = match.group(1) if match else paragraph
    return {"tagline": tagline, "about": paragraph if len(paragraph) > len(tagline) else ""}

def _get_folder_tree_html(folders, texts, n_files, root=""):
    """The published folders under root ("" for all of them, on the landing page; a folder, on its own page) as nested lists: each
    links to its page and shows its title (when _collections.yml gives one), how many files sit under it, and its tagline. Empty
    when root has no subfolders. The levels are collections (top-level folders), their datasets, and the datasets' derived products;
    the rows of the manifests are the files."""
    def items(parent):
        children = [f for f in folders if posixpath.dirname(f) == parent]
        if not children:
            return ""
        html_items = []
        for folder in children:
            name, text, n = folder.rsplit("/", 1)[-1], texts.get(folder, {}), n_files[folder]
            label = f'<code>{name}/</code>' + (f' <span class="title">{html.escape(text["title"])}</span>' if text.get("title") else "")
            html_items.append(f'<li><a href="/{folder}/">{label}</a><span class="count">{n} file{"s" if n != 1 else ""}</span>'
                              + (f'<span class="tagline">{html.escape(text["tagline"])}</span>' if text.get("tagline") else "") + items(folder) + "</li>")
        return "<ul>" + "".join(html_items) + "</ul>"
    inner = items(root)
    return f'<div class="tree">{inner}</div>' if inner else ""

def _get_docstring_markdown(docstring):
    """A docstring as Markdown for Quarto: a blank line before a list that follows a paragraph line and after a list's last item
    (Pandoc needs the first, and would otherwise read the unindented line after a list as part of its last item), '<' and
    '>' escaped so a name like lulc_esa_<year>.tif stays text instead of becoming an HTML tag, and URLs and DOIs made links
    (Quarto doesn't link bare URLs)."""
    def linkify(line):
        line = re.sub(r"[<>]", lambda m: "\\" + m.group(), line)
        line = re.sub(r"https?://[^\s<>\"]+[^\s<>\".,;:)]", lambda m: f"<{m.group(0)}>", line)
        return re.sub(r"\bdoi:(10\.\d+/[^\s<>\"]*[^\s<>\".,;:)])", lambda m: f"[{m.group(0)}](https://doi.org/{m.group(1)})", line)
    out, in_list = [], False
    for line in docstring.strip().split("\n"):
        is_item = bool(re.match(r"\s*(\d+\.|[-*])\s", line))
        if not line.strip():
            in_list = False
        elif (is_item and not in_list or in_list and not is_item and not line[:1].isspace()) and out and out[-1].strip():
            out.append("")  # a list starts after a paragraph line, or a paragraph line follows a list's last item
        in_list = is_item or (in_list and line[:1].isspace())
        out.append(linkify(line))
    return "\n".join(out)

def _first_sentences(text, n=3):
    """The first n sentences of text (all of it when it has no more): what a card shows of a folder's text."""
    return " ".join(re.split(r"(?<=[.!?])\s+", text.strip())[:n])

def _linkify(text):
    """text, HTML-escaped, with its URLs and DOIs made links."""
    text = re.sub(r"https?://[^\s<>\"]+[^\s<>\".,;:)]", lambda m: f'<a href="{m.group(0)}">{m.group(0)}</a>', html.escape(text, quote=False))
    return re.sub(r"\bdoi:(10\.\d+/[^\s<>\"]*[^\s<>\".,;:)])", lambda m: f'<a href="https://doi.org/{m.group(1)}">{m.group(0)}</a>', text)

def _format_size(n_bytes):
    """A file size for people: 1.2 GB, 340.5 MB, 12.0 KB."""
    for unit, scale in (("GB", 1e9), ("MB", 1e6), ("KB", 1e3)):
        if n_bytes >= scale:
            return f"{n_bytes / scale:.1f} {unit}"
    return f"{n_bytes} B"

def _format_resolution(arcseconds):
    """A rung for people: 10″ (≈0.31 km), 5′ (≈9.3 km), 1°. The distance is a cell's width at the equator."""
    if arcseconds >= 3600:
        return f"{arcseconds / 3600:g}°"
    label = f"{arcseconds / 60:g}′" if arcseconds >= 60 else f"{arcseconds:g}″"
    return f"{label} (≈{arcseconds / 3600 * 111.32:.2g} km)"

def _natural_sort_key(text):
    """Sorts numbers inside text by value, so ha_per_cell_15sec comes before ha_per_cell_150sec."""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", text)]

def _fill_placeholders(template, **values):
    """template with each %%NAME%% replaced by values['name']. A placeholder left unfilled is an error."""
    for name, value in values.items():
        template = template.replace(f"%%{name.upper()}%%", str(value))
    unfilled = sorted(set(re.findall(r"%%[A-Z_]+%%", template)))
    if unfilled:
        raise ValueError(f"These placeholders have no value: {unfilled}")
    return template
