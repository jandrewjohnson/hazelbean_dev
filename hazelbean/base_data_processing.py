"""Publishing into the canonical base data store on Cloudflare R2.

Spec: earth_economy_devstack/docs/proposal_base_data_store.qmd. Publishing is the only write to R2. The current version of
a dataset lives at its plain ref path (pyramids/ha_per_cell_10sec.tif); a version it replaces is archived, unless asked
not to, at static/<ref path without extension>/v<release that published it, dots as underscores>.<extension>.

Publishing gates each dataset, stages its new bytes under _staging/, archives the versions being replaced, claims the next
release ID, writes one catalogue entry per dataset, and commits by compare-and-swap on _release/latest.json. Only then are
the plain paths overwritten from staging. If another curator's release commits first, the release and entries this one wrote are
deleted and it stops: rerun it. If overwriting a plain path fails after the commit, rerunning the manifest command finishes it.

Single-file POG datasets in the public bucket only. The R2 calls are in hazelbean.cloud_utils; credentials come from
~/.config/hazelbean/machine.env (see cloud_utils.get_r2_client).

Each dataset folder in base_data carries its own manifest, <name>_base_data_manifest.csv, written by the ingestion script
beside it (<name>_base_data_ingestion.py, usually a call to add_directory_to_base_data). publish_base_data_from_manifests
finds every manifest under base_data, combines them, converts any listed raster that isn't a POG yet, compares the
result with the latest release, and publishes what is new or changed.
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

__all__ = ["publish_base_data", "publish_base_data_from_manifests", "add_directory_to_base_data", "find_base_data_manifests",
           "write_base_data_index_pages", "resolve_dry_run"]

BUCKET = "teems-public-data"
LATEST_KEY = "_release/latest.json"
ARCHIVE_FOLDER = "static"
CURRENT_CACHE_CONTROL = "public, max-age=3600"  # a plain path is overwritten by each new version, so caches must not keep it long
REVISION_TOKENS = {"final", "new", "old", "copy", "bak", "backup", "temp", "tmp", "draft"}
MANIFEST_COLUMNS = ("ref_path", "kind", "tier", "variable_class", "license", "units", "data_source", "description", "code")
MANIFEST_SUFFIX = "_base_data_manifest.csv"
RAW_FOLDER = "raw"  # a dataset folder's raw downloads, exactly as provided: read by its ingestion script, never listed or uploaded
KINDS_BY_EXTENSION = {".tif": "pog", ".tiff": "pog", ".csv": "table", ".xlsx": "table", ".gpkg": "vector", ".shp": "vector"}
SHAPEFILE_SIDECARS = (".shx", ".dbf", ".prj", ".cpg", ".sbn", ".sbx", ".qix")  # copied with their .shp, but not datasets of their own
NOT_DATA = (".py", ".pyc", ".ipynb", ".r", ".sh", ".aux.xml", MANIFEST_SUFFIX)  # ingestion scripts, manifests and GDAL sidecars aren't datasets
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
                               overrides=None, include=None, include_subdirectories=True, make_pogs=True, overwrite=False, base_data_dir=None,
                               parallel=True, n_workers=None, dry_run=True, client=None):
    """Add a directory's files to the local base_data and list them in a dataset manifest, ready to publish.

    This is what a dataset's ingestion script (<name>_base_data_ingestion.py, beside its data) calls. Each file goes to
    <base_data_dir>/<ref_folder>/<its path relative to source_dir>; with source_dir already that folder, files stay where
    they are. GeoTIFFs that are already POGs are kept or copied as they are; the rest are converted with hb.make_path_pog
    using their declared variable class (in place, the original is deleted once its POG is written), or, with
    make_pogs=False, left for publishing to convert. Tables and vectors are kept or copied as they are. Hidden files,
    code, manifests, GDAL sidecars, displaced or temporary files and raw/ folders (raw downloads) are skipped. Every new dataset gets a row in
    manifest_path, which is created if missing; rows already there are left alone. Nothing is written to R2: the run
    ends with the publishing dry run.

    Args:
        source_dir (str): The directory to add: usually the dataset's own folder in base_data, or anywhere on disk.
        ref_folder (str): Its folder in base_data, e.g. 'lulc/esa'.
        manifest_path (str): The dataset's manifest, <name>_base_data_manifest.csv beside its ingestion script.
        license, units, data_source, description, code (str): Manifest metadata for every file, unless overridden.
        variable_class (str): For rasters that don't declare one: 'extensive', 'intensive', 'categorical' or 'covariate'.
            Never guessed: a raster with no class declared anywhere is refused.
        overrides (dict): Per-file changes, keyed by a pattern matched against each file's path relative to source_dir,
            e.g. {'*_yield_*.tif': {'units': 't/ha', 'variable_class': 'intensive'}}. Later patterns win.
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

    Returns:
        dict: 'actions' (ref path -> what was or would be done), 'skipped', 'problems', and 'publish' (the publishing
        dry run's report, or None in a dry run).
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
    defaults = dict(license=license, units=units, data_source=data_source, description=description, code=code, variable_class=variable_class)
    listed = set(_read_manifest(manifest_path)["ref_path"]) if os.path.exists(manifest_path) else set()

    n_workers = n_workers or max(1, hb.available_cpu_count() - 1)

    # Find the files (cheap, in order).
    items, skipped, n_not_included = [], [], 0
    for root, dirs, files in os.walk(source_dir):
        skipped += [os.path.relpath(os.path.join(root, d), source_dir).replace(os.sep, "/") + "/ (raw input, never added)" for d in dirs if d == RAW_FOLDER]
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in ("__pycache__", RAW_FOLDER))
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
        return problems

    problems = [p for item_problems in _run_each(plan, items, parallel, n_workers) for p in item_problems]

    hb.log(f"{'Dry run: ' if dry_run else ''}adding {source_dir} to base_data as {ref_folder}/: {len(items)} files, {len(skipped)} skipped"
           + (f", {n_not_included} not matching include" if include else "")
           + "".join(f"\n  {i['action']:33s} {i['manifest']:15s} {i['ref_path']}" for i in items)
           + "".join(f"\n  skipped                           {s}" for s in skipped) + "".join(f"\n  PROBLEM {p}" for p in problems))
    result = {"actions": {i["ref_path"]: i["action"] for i in items}, "skipped": skipped, "problems": problems, "publish": None}
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
                             remove_displaced_files=in_place)
        hb.log(f"Done {n}/{len(to_do)}: {item['ref_path']}")

    failures = _run_each_collecting_failures(put_in_place, list(enumerate(to_do, 1)), parallel, n_workers, label=lambda numbered: numbered[1]["ref_path"])
    if failures:
        raise RuntimeError("These files couldn't be put in place, so the manifest wasn't updated; the others are done, and a rerun "
                           "skips them:\n  " + "\n  ".join(failures))
    rows = [dict({k: i["settings"][k] or "" for k in ("variable_class", "license", "units", "data_source", "description", "code")}, ref_path=i["ref_path"],
                 kind=i["kind"], tier="public") for i in items if i["manifest"] == "new row"]
    if rows:
        existing = [_read_manifest(manifest_path)] if os.path.exists(manifest_path) else []
        pd.concat(existing + [pd.DataFrame(rows)[list(MANIFEST_COLUMNS)]]).to_csv(manifest_path, index=False, encoding="utf-8-sig")
    hb.log(f"Added {len(items)} files to base_data and {len(rows)} rows to {manifest_path}. Publishing dry run:")
    manifest_paths = sorted(set(find_base_data_manifests(base_data_dir)) | {os.path.abspath(manifest_path)})
    result["publish"] = publish_base_data_from_manifests(base_data_dir=base_data_dir, manifest_paths=manifest_paths, dry_run=True, client=client)
    return result

def find_base_data_manifests(base_data_dir=None):
    """Every dataset manifest (<name>_base_data_manifest.csv) under base_data, sorted."""
    base_data_dir = base_data_dir or os.path.join(os.path.expanduser("~"), "Files", "base_data")
    found = []
    for root, dirs, files in os.walk(base_data_dir):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in ("__pycache__", RAW_FOLDER))
        found += [os.path.join(root, f) for f in files if f.endswith(MANIFEST_SUFFIX)]
    return sorted(found)

def publish_base_data_from_manifests(base_data_dir=None, manifest_paths=None, note=None, archive_previous=True, parallel=True, n_workers=None, dry_run=True,
                                     client=None, site_dir=None):
    """Combine every dataset manifest under base_data, compare it with the local files and the latest release, and publish what is new or changed.

    The manifests (<name>_base_data_manifest.csv, each beside its dataset's ingestion script) are combined into one
    list; a ref path listed by two manifests is an error. A listed raster that isn't a POG yet is converted in place with
    its row's variable_class before anything else, on a real run only: a dry run reports it as 'needs_pog'. Every row then
    gets a status: 'new' (not yet published), 'changed' (the local bytes differ from the published version), 'unchanged',
    'unfinished' (published, but its plain path doesn't hold those bytes yet, because an earlier run stopped after its
    commit), 'missing_locally', or 'unsupported' (a kind or tier publishing can't handle yet). Published datasets that no
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
    client = client or cloud_utils.get_r2_client()
    current = (_read_latest_release(client)[0] or {}).get("datasets", {})

    rows = df.to_dict("records")
    for row in rows:
        row["path"] = os.path.join(base_data_dir, *row["ref_path"].split("/"))
    publishable = [row for row in rows if row["kind"] == "pog" and row["tier"] == "public" and os.path.isfile(row["path"])]

    # Rasters an ingestion script listed without converting: convert them now (real runs only).
    is_pog = _run_each(lambda row: hb.is_path_pog(row["path"]), publishable, parallel, n_workers)
    needs_pog = [row for row, pog in zip(publishable, is_pog) if not pog]
    unclassed = [row["ref_path"] for row in needs_pog if not row["variable_class"]]
    if unclassed and not dry_run:
        raise ValueError(f"These rasters aren't POGs yet and their manifest rows declare no variable_class: {unclassed}")
    if not dry_run and needs_pog:
        def make_pog(numbered):
            n, row = numbered
            hb.log(f"Making POG {n}/{len(needs_pog)}: {row['ref_path']} ({row['variable_class']})")
            hb.make_path_pog(row["path"], variable_class=row["variable_class"], remove_displaced_files=True)
            hb.log(f"Made POG {n}/{len(needs_pog)}: {row['ref_path']}")
        failures = _run_each_collecting_failures(make_pog, list(enumerate(needs_pog, 1)), parallel, n_workers, label=lambda numbered: numbered[1]["ref_path"])
        if failures:
            raise RuntimeError("These rasters couldn't be made POGs, so nothing was published; the others are converted, and a rerun skips them:\n  "
                               + "\n  ".join(failures))
        needs_pog = []
    skip = {row["ref_path"] for row in needs_pog}

    # Hash every file that could be published (the slow part of every run).
    to_hash = [row["path"] for row in publishable if row["ref_path"] not in skip]
    hashes = dict(zip(to_hash, _run_each(hb.hash_file_path, to_hash, parallel, n_workers)))

    statuses, rows_to_publish, unfinished = {}, [], []
    for row in rows:
        ref_path, path = row["ref_path"], row["path"]
        if ref_path in skip:
            statuses[ref_path] = "needs_pog"
        elif row["kind"] != "pog" or row["tier"] != "public":
            statuses[ref_path] = "unsupported"
        elif not os.path.isfile(path):
            statuses[ref_path] = "missing_locally"
        else:
            previous, sha256 = current.get(ref_path), hashes[path]
            if previous and previous["dataset_sha256"] == _get_dataset_sha256(ref_path, sha256):
                served = cloud_utils.read_r2_object_metadata(client, BUCKET, ref_path) or {}
                statuses[ref_path] = "unchanged" if served.get("sha256") == sha256 else "unfinished"
                if statuses[ref_path] == "unfinished":
                    unfinished.append((path, ref_path, sha256))
            else:
                statuses[ref_path] = "changed" if previous else "new"
                rows_to_publish.append(row)
    statuses.update({r: "not_in_manifest" for r in current if r not in statuses})

    counts = pd.Series(statuses, dtype=str).value_counts().to_dict()
    hb.log(f"{len(manifest_paths)} manifests, {len(df)} rows, against {BUCKET}: {counts}" + "".join(f"\n  {s:16s} {r}" for r, s in statuses.items() if s != "unchanged"))
    if unclassed:
        hb.log(f"PROBLEM: these rasters aren't POGs yet and their manifest rows declare no variable_class: {unclassed}")
    if not dry_run:
        for i, (path, ref_path, sha256) in enumerate(unfinished, 1):  # finish what an interrupted run committed but didn't move into place
            cloud_utils.upload_path_to_r2(client, BUCKET, path, ref_path, metadata={"sha256": sha256, "md5": hb.hash_file_path(path, "md5")}, content_type="image/tiff",
                                          cache_control=CURRENT_CACHE_CONTROL, skip_if_exists=False, progress_label=f"Finishing {i}/{len(unfinished)} {ref_path}")
            client.delete_object(Bucket=BUCKET, Key=_get_staging_key(ref_path, sha256))
    plan = None
    if rows_to_publish:
        if not dry_run and not note:
            raise ValueError("Give a one-line change note to publish.")
        plan = publish_base_data([r["path"] for r in rows_to_publish], [r["ref_path"] for r in rows_to_publish], note or "(dry run)",
                                 *([r[k] for r in rows_to_publish] for k in ("license", "units", "data_source", "description", "code")),
                                 archive_previous=archive_previous, parallel=parallel, n_workers=n_workers, dry_run=dry_run, client=client)
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
    table of its published files: their manifest rows, with each file's version, release, size, resolution and archived
    versions. Metadata every row shares is shown once above the table. Manifest rows not yet published are left out.

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
    archive_keys = cloud_utils.list_r2_keys(client, BUCKET, ARCHIVE_FOLDER + "/")
    for row, entry in zip(rows, entries):
        archive_folder = f"{ARCHIVE_FOLDER}/{os.path.splitext(row['ref_path'])[0]}/"
        row.update(size=entry["files"][0]["size"], rung=entry["lattice"]["rung"], archive_keys=[k for k in archive_keys if k.startswith(archive_folder)])
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
        arcseconds = sorted({hb.token_to_arcseconds(row["rung"]) for row in folder_rows})
        resolutions = _format_resolution(arcseconds[0]) + (f" to {_format_resolution(arcseconds[-1])}" if len(arcseconds) > 1 else "")
        return (f'<ul class="chips"><li><b>{len(folder_rows)}</b> file{"s" if len(folder_rows) != 1 else ""}</li>'
                f'<li><b>{_format_size(sum(row["size"] for row in folder_rows))}</b></li><li>{resolutions}</li></ul>')
    def card(folder, link_class="card"):
        text = texts.get(folder, {})
        return (f'<a class="{link_class}" href="/{folder}/"><span class="path">{folder}/</span><h3>{html.escape(text.get("title", folder.rsplit("/", 1)[-1]))}</h3>'
                + (f'<p class="tagline">{html.escape(text["tagline"])}</p>' if text.get("tagline") else "")
                + (f'<p>{html.escape(text["about"])}</p>' if text.get("about") else "") + chips(rows_under(folder)) + '<div class="go">Browse &rarr;</div></a>')

    def folder_body(folder):
        text, here = texts.get(folder, {}), rows_by_folder.get(folder, [])
        body = [f'```{{=html}}\n<h1><span class="path">{folder}/</span>{html.escape(text.get("title", folder.rsplit("/", 1)[-1]))}</h1>\n'
                + (f'<p class="tagline">{html.escape(text["tagline"])}</p>\n' if text.get("tagline") else "") + chips(rows_under(folder)) + "\n```"]
        if text.get("about"):
            body.append(f'::: {{.lede}}\n{html.escape(text["about"])}\n:::')
        children = [f for f in folders if posixpath.dirname(f) == folder]
        if children:
            # Three levels: a collection (top-level folder) holds datasets, and a dataset holds derived products. A card per direct
            # subfolder, then everything below this folder as a tree, as on the landing page but pared to this subtree.
            heading = "Datasets" if "/" not in folder else "Derived products"
            body.append(f"## {heading}\n\n```{{=html}}\n<div class=\"cards\">" + "".join(card(f) for f in children) + "</div>\n"
                        + _get_folder_tree_html(folders, texts, n_files, root=folder) + "\n```")
        if here:
            script_path, docstring = here[0]["script_path"], docstrings.get(folder)
            if docstring:
                script_ref = "base_data/" + os.path.relpath(script_path, base_data_dir).replace(os.sep, "/")
                body.append(f'## About\n\n```{{=html}}\n<div class="about">{_get_docstring_html(docstring)}</div>\n'
                            f'<p class="source-note">From the ingestion script that made these files, <code>{script_ref}</code>.</p>\n```')
            body.append("## Files\n\n```{=html}\n" + _get_dataset_table_html(here) + "\n```")
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
                      dry_run=False, client=None):
    """Publish single-file POG datasets into the public base data store as one release.

    Args:
        sources (str | list): Local POG paths, one per dataset.
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

    Returns:
        dict: The release ID, parent release, per-dataset plan, problems found, and whether anything was written.
    """
    dry_run = resolve_dry_run(dry_run)
    sources = [sources] if isinstance(sources, str) else list(sources)
    ref_paths = [ref_paths] if isinstance(ref_paths, str) else list(ref_paths)
    if len(sources) != len(ref_paths):
        raise ValueError("Give one ref path per source.")
    metadata = {k: list(v) if isinstance(v, (list, tuple)) else [v] * len(sources)
                for k, v in dict(license=license, units=units, data_source=data_source, description=description, code=code).items()}
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
    checked = _run_each(lambda pair: check_pog_publication_status(*pair), list(zip(sources, ref_paths)), parallel, n_workers)
    for i, (dataset, ref_path) in enumerate(zip(checked, ref_paths)):
        dataset["metadata"] = {k: v[i] for k, v in metadata.items()}
        absent = [k for k in ("license", "units", "data_source", "description") if not dataset["metadata"][k]]
        if absent:
            dataset["problems"].append(f"these are required: {absent}")
        previous = current.get(ref_path)
        if previous and previous["dataset_sha256"] == dataset.get("dataset_sha256"):
            dataset["problems"].append(f"identical to the current version {previous['version']}")
        missing = [r for r in dataset.get("depends_on", []) if r not in current and r not in ref_paths]
        if missing:
            dataset["problems"].append(f"depends on datasets that are not published: {missing}")
        dataset["version"] = previous["version"] + 1 if previous else 1
        dataset["previous"] = previous
        dataset["archive_key"] = _get_archive_key(ref_path, previous["release"]) if previous and archive_previous else None
        if dataset["archive_key"] and client:  # what gets archived is whatever the plain path serves, so it must be the published version
            served = cloud_utils.read_r2_object_metadata(client, BUCKET, ref_path) or {}
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
        cloud_utils.upload_path_to_r2(client, BUCKET, d["source_path"], _get_staging_key(d["ref_path"], f["sha256"]),
                                      metadata={"sha256": f["sha256"], "md5": f["md5"]}, content_type="image/tiff", progress_label=f"Uploading {i}/{len(datasets)} {d['ref_path']}")
        if d["archive_key"] and cloud_utils.read_r2_object_metadata(client, BUCKET, d["archive_key"]) is None:
            served = cloud_utils.read_r2_object_metadata(client, BUCKET, d["ref_path"])
            cloud_utils.copy_r2_object(client, BUCKET, d["ref_path"], d["archive_key"], metadata=served, content_type="image/tiff",
                                       progress_label=f"Archiving inside R2 {i}/{len(datasets)} {d['ref_path']} as {d['archive_key']}")

    # Claim the release ID, write the entries, then commit. Only the commit makes the release visible.
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    snapshot = {"release": release_id, "parent": plan["parent"], "created_at": now, "created_by": getpass.getuser(), "note": note,
                "datasets": dict(current, **{d["ref_path"]: {"dataset_sha256": d["dataset_sha256"], "version": d["version"], "release": release_id} for d in datasets})}
    written = []
    try:
        cloud_utils.write_r2_json(client, BUCKET, f"_release/{release_id}.json", snapshot, IfNoneMatch="*")
        written.append(f"_release/{release_id}.json")
        for d in datasets:
            m = d["metadata"]
            entry = {"dataset": d["ref_path"], "kind": "pog", "tier": "public", "version": d["version"], "dataset_sha256": d["dataset_sha256"], "release": release_id,
                     "previous": dict(d["previous"], archive_key=d["archive_key"]) if d["previous"] else None,  # archive_key None: not archived
                     "lattice": d["lattice"], "semantics": dict(d["semantics"], units=m["units"]), "files": d["files"],
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
            cloud_utils.copy_r2_object(client, BUCKET, _get_staging_key(d["ref_path"], f["sha256"]), d["ref_path"], metadata={"sha256": f["sha256"], "md5": f["md5"]},
                                       content_type="image/tiff", cache_control=CURRENT_CACHE_CONTROL, progress_label=f"Moving into place inside R2 {i}/{len(datasets)} {d['ref_path']}")
            client.delete_object(Bucket=BUCKET, Key=_get_staging_key(d["ref_path"], f["sha256"]))
        except Exception as e:
            unfinished.append(f"{d['ref_path']} ({e})")
    if unfinished:
        raise RuntimeError(f"Release {release_id} is committed, but these plain paths still serve their previous bytes: {unfinished}. "
                           "Run the manifest command again to finish them.")
    hb.log(f"Published release {release_id}.")
    return plan

def check_pog_publication_status(source_path, ref_path):
    """Gate one single-file POG and describe it for the catalogue. The returned 'problems' list is empty when it passes.

    POG conformance (variable class, nodata convention, overviews and their rule, exact statistics, COG layout) is entirely
    hb.is_path_pog's job. Only the store's own rules are checked here: how ref paths are named, and what publishing supports."""
    d = {"ref_path": ref_path, "source_path": source_path, "problems": []}
    components = ref_path.split("/")
    if ref_path.startswith(("/", "_")) or "\\" in ref_path or any(not re.fullmatch(r"[a-z0-9][a-z0-9_.\-]*", c) for c in components):
        d["problems"].append("ref path must be relative, lowercase, forward-slashed, and must not start with '_'")
    if components[0] == ARCHIVE_FOLDER:
        d["problems"].append(f"ref paths must not start with '{ARCHIVE_FOLDER}/', which holds archived versions")
    if any(t in REVISION_TOKENS or re.fullmatch(r"v\d+", t) for t in os.path.splitext(components[-1])[0].split("_")):
        d["problems"].append("file names carry meaning, never revisions such as _v2 or _final")
    if not ref_path.endswith(".tif") or not os.path.isfile(source_path):
        d["problems"].append(f"need an existing .tif source for a .tif ref path: {source_path}")
        return d
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
    sha256, md5 = hb.hash_file_path(source_path), hb.hash_file_path(source_path, "md5")
    d["size"] = os.path.getsize(source_path)
    d["files"] = [{"ref_path": ref_path, "size": d["size"], "sha256": sha256, "md5": md5}]
    d["dataset_sha256"] = _get_dataset_sha256(ref_path, sha256)
    d["lattice"] = {"rung": pog["rung"], "storage_form": "pog", "extent": pog["bounding_box"]}
    d["semantics"] = {k: pog[k] for k in ("variable_class", "intensive_weighting", "denominator", "stats")}
    return d

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

def _read_manifest(manifest_path):
    """A dataset manifest as a DataFrame of strings, checked for the expected columns."""
    df = pd.read_csv(manifest_path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    missing = [c for c in MANIFEST_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"The manifest {manifest_path} lacks the columns {missing}.")
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
    """A folder's published datasets as HTML: the metadata every row shares, once, then a table with one row per file."""
    shared = [(k, label) for k, label in PAGE_FIELDS if len({row[k] for row in rows}) == 1]
    varying = [(k, label) for k, label in PAGE_FIELDS if (k, label) not in shared]
    lines = ['<dl class="shared">' + "".join(f"<dt>{label}</dt><dd>{_linkify(rows[0][k])}</dd>" for k, label in shared if rows[0][k]) + "</dl>",
             '<div class="table-wrap"><table class="datasets"><thead><tr>'
             + "".join(f"<th>{h}</th>" for h in ["File", "Version", "Release", "Size", "Resolution"] + [label for _, label in varying] + ["Earlier versions"])
             + "</tr></thead><tbody>"]
    for row in rows:
        archives = "".join(f'<a class="archive" href="https://data.teemlabs.org/{k}">{posixpath.splitext(posixpath.basename(k))[0][1:].replace("_", ".")}</a>'
                           for k in row["archive_keys"])
        lines.append(f'<tr><td class="file"><a href="https://data.teemlabs.org/{row["ref_path"]}" download>{posixpath.basename(row["ref_path"])}</a></td>'
                     f'<td><span class="pill">v{row["version"]}</span></td><td class="num">{row["release"]}</td><td class="num">{_format_size(row["size"])}</td>'
                     f'<td class="num">{_format_resolution(hb.token_to_arcseconds(row["rung"]))}</td>'
                     + "".join(f'<td class="meta">{_linkify(row[k])}</td>' for k, _ in varying) + f"<td>{archives or '&ndash;'}</td></tr>")
    return "\n".join(lines + ["</tbody></table></div>"])

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

def _get_docstring_html(docstring):
    """A docstring as HTML paragraphs: its hard-wrapped lines rejoined, except where a line starts a numbered or bulleted item."""
    paragraphs = []
    for block in re.split(r"\n\s*\n", docstring.strip()):
        lines = []
        for line in block.split("\n"):
            if lines and not re.match(r"\s*(\d+\.|[-*])\s", line):
                lines[-1] += " " + line.strip()
            else:
                lines.append(line.strip())
        paragraphs.append("<p>" + "<br>".join(_linkify(line) for line in lines) + "</p>")
    return "".join(paragraphs)

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
