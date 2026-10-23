"""Publishing to the base data store (hazelbean/base_data_processing.py), against an in-memory stand-in for R2.

The stand-in enforces If-Match and If-None-Match the way R2 does (failing with 412), so the compare-and-swap commit
is exercised without credentials or network. The POGs are tiny ha_per_cell rasters at the coarsest rungs.
"""
import hashlib
import io
import json
import os
import posixpath
import shutil

import pandas as pd
import pytest

import hazelbean as hb
from hazelbean import base_data_processing as store

METADATA = dict(license="CC-BY-4.0", units="ha", data_source="computed from the WGS84 ellipsoid", description="Hectares per cell.")

class FakeClientError(Exception):
    """Shaped like botocore's ClientError, which is all the module inspects."""
    def __init__(self, status):
        super().__init__(status)
        self.response = {"ResponseMetadata": {"HTTPStatusCode": status}}

class FakeR2:
    """The few boto3 S3 client methods publishing uses. objects maps each key to (bytes, user metadata)."""
    def __init__(self):
        self.objects = {}
        self.before_put = None  # called with the key before each put, to simulate another curator

    def put_object(self, Bucket, Key, Body, IfMatch=None, IfNoneMatch=None, Metadata=None, **kwargs):
        if self.before_put:
            self.before_put(Key)
        existing = self.objects.get(Key)
        if (IfNoneMatch == "*" and existing is not None) or (IfMatch is not None and (existing is None or self.etag(existing[0]) != IfMatch)):
            raise FakeClientError(412)
        self.objects[Key] = (Body, Metadata or {})

    def get_object(self, Bucket, Key):
        if Key not in self.objects:
            raise FakeClientError(404)
        return {"Body": io.BytesIO(self.objects[Key][0]), "ETag": self.etag(self.objects[Key][0])}

    def head_object(self, Bucket, Key):
        if Key not in self.objects:
            raise FakeClientError(404)
        return {"ContentLength": len(self.objects[Key][0]), "Metadata": dict(self.objects[Key][1])}

    def upload_file(self, Filename, Bucket, Key, ExtraArgs=None, Callback=None):
        with open(Filename, "rb") as f:
            self.objects[Key] = (f.read(), dict((ExtraArgs or {}).get("Metadata", {})))
        if Callback:
            Callback(len(self.objects[Key][0]))

    def copy(self, CopySource, Bucket, Key, ExtraArgs=None, Callback=None):
        body, metadata = self.objects[CopySource["Key"]]
        self.objects[Key] = (body, dict((ExtraArgs or {}).get("Metadata", metadata)))
        if Callback:
            Callback(len(body))

    def delete_object(self, Bucket, Key):
        self.objects.pop(Key, None)

    def list_objects_v2(self, Bucket, Prefix=""):
        return {"Contents": [{"Key": k} for k in sorted(self.objects) if k.startswith(Prefix)], "IsTruncated": False}

    def etag(self, body):
        return '"' + hashlib.md5(body).hexdigest() + '"'

    def json(self, key):
        return json.loads(self.objects[key][0])

    def body(self, key):
        return self.objects[key][0]

def read(path):
    with open(path, "rb") as f:
        return f.read()

@pytest.fixture
def pogs(tmp_path):
    """Two tiny global POGs: ha_per_cell at 324000 s (4 x 2 cells) and 648000 s (2 x 1)."""
    return {a: hb.write_ha_per_cell_pog(str(tmp_path / f"ha_per_cell_{a}sec.tif"), a) for a in (324000, 648000)}

REFS = ["pyramids/ha_per_cell_324000sec.tif", "pyramids/ha_per_cell_648000sec.tif"]

def test_transfer_progress_logs_at_intervals_and_always_at_the_end(capsys):
    from hazelbean import cloud_utils
    quiet = cloud_utils.R2TransferProgress("Uploading quiet", 3_000_000, every_seconds=1e9)
    quiet(1_000_000)
    quiet(2_000_000)
    lines = [l for l in capsys.readouterr().out.splitlines() if "Uploading quiet" in l]
    assert len(lines) == 1 and "3.0 of 3.0 MB (100%)" in lines[0] and "done" in lines[0]  # only the final line inside the interval
    chatty = cloud_utils.R2TransferProgress("Uploading chatty", 3_000_000, every_seconds=0)
    chatty(1_000_000)
    chatty(2_000_000)
    lines = [l for l in capsys.readouterr().out.splitlines() if "Uploading chatty" in l]
    assert len(lines) == 2 and "(33%)" in lines[0]

def test_publishing_logs_each_upload_and_move(pogs, capsys):
    store.publish_base_data(list(pogs.values()), REFS, "Initial.", client=FakeR2(), **METADATA)
    out = capsys.readouterr().out
    assert f"Uploading 1/2 {REFS[0]}" in out and f"Uploading 2/2 {REFS[1]}" in out and f"Moving into place inside R2 2/2 {REFS[1]}" in out

def test_dry_run_writes_nothing(pogs):
    r2 = FakeR2()
    plan = store.publish_base_data(list(pogs.values()), REFS, "Initial.", dry_run=True, client=r2, **METADATA)
    assert r2.objects == {} and plan["problems"] == [] and not plan["written"]

def test_dry_run_without_credentials(pogs, monkeypatch):
    for key in ("HB_R2_ACCOUNT_ID", "HB_R2_ACCESS_KEY_ID", "HB_R2_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(key, raising=False)
    assert store.publish_base_data(pogs[324000], REFS[0], "Initial.", dry_run=True, **METADATA)["problems"] == []

def test_first_release_serves_the_file_at_its_plain_path(pogs):
    r2 = FakeR2()
    plan = store.publish_base_data(list(pogs.values()), REFS, "Initial.", client=r2, **METADATA)
    assert r2.json("_release/latest.json") == {"release": plan["release"]}
    assert set(r2.json(f"_release/{plan['release']}.json")["datasets"]) == set(REFS)
    entry = r2.json(f"_catalogue/{REFS[0]}/{plan['release']}.json")
    assert entry["version"] == 1 and entry["previous"] is None and entry["semantics"]["variable_class"] == "extensive"
    assert r2.body(REFS[0]) == read(pogs[324000]) and r2.objects[REFS[0]][1]["sha256"] == entry["files"][0]["sha256"]
    assert not any(k.startswith(("_staging/", "static/")) for k in r2.objects)  # staging is cleared; nothing to archive yet

def test_second_version_archives_the_first(pogs):
    r2 = FakeR2()
    first = store.publish_base_data(pogs[324000], "pyramids/test_area.tif", "First.", client=r2, **METADATA)
    second = store.publish_base_data(pogs[648000], "pyramids/test_area.tif", "Second.", client=r2, **METADATA)
    archive_key = f"static/pyramids/test_area/v{first['release'].replace('.', '_')}.tif"
    assert r2.body("pyramids/test_area.tif") == read(pogs[648000]) and r2.body(archive_key) == read(pogs[324000])
    entry = r2.json(f"_catalogue/pyramids/test_area.tif/{second['release']}.json")
    assert entry["version"] == 2 and entry["previous"]["release"] == first["release"] and entry["previous"]["archive_key"] == archive_key

def test_second_version_without_archiving_keeps_only_the_new_one(pogs):
    r2 = FakeR2()
    store.publish_base_data(pogs[324000], "pyramids/test_area.tif", "First.", client=r2, **METADATA)
    second = store.publish_base_data(pogs[648000], "pyramids/test_area.tif", "Second.", archive_previous=False, client=r2, **METADATA)
    assert r2.body("pyramids/test_area.tif") == read(pogs[648000]) and not any(k.startswith("static/") for k in r2.objects)
    assert r2.json(f"_catalogue/pyramids/test_area.tif/{second['release']}.json")["previous"]["archive_key"] is None  # recorded as not archived

@pytest.mark.parametrize("ref_path, message", [("_v/x.tif", "must not start with '_'"), ("static/x.tif", "must not start with 'static/'"),
                                               ("pyramids/x_v2.tif", "never revisions"), ("Pyramids/x.tif", "lowercase")])
def test_gate_refuses(pogs, ref_path, message):
    with pytest.raises(ValueError, match=message):
        store.publish_base_data(pogs[324000], ref_path, "Bad.", client=FakeR2(), **METADATA)

def test_non_pog_refused(tmp_path):
    from osgeo import gdal
    path = str(tmp_path / "plain.tif")
    ds = gdal.GetDriverByName("GTiff").Create(path, 4, 2, 1, gdal.GDT_Float64)
    ds.SetGeoTransform((-180.0, 90.0, 0.0, 90.0, 0.0, -90.0))
    ds = None
    with pytest.raises(ValueError, match="fails hb.is_path_pog"):
        store.publish_base_data(path, "pyramids/plain.tif", "Bad.", client=FakeR2(), **METADATA)

def test_identical_publication_refused(pogs):
    r2 = FakeR2()
    store.publish_base_data(pogs[324000], REFS[0], "Initial.", client=r2, **METADATA)
    with pytest.raises(ValueError, match="identical to the current version"):
        store.publish_base_data(pogs[324000], REFS[0], "Again.", client=r2, **METADATA)

def test_missing_metadata_refused(pogs):
    with pytest.raises(ValueError, match=r"required: \[.description.\]"):
        store.publish_base_data(pogs[324000], REFS[0], "Initial.", client=FakeR2(), license="CC-BY-4.0", units="ha", data_source="x", description="")

def test_lost_commit_publishes_nothing(pogs):
    r2 = FakeR2()
    store.publish_base_data(pogs[324000], REFS[0], "Initial.", client=r2, **METADATA)
    before = dict(r2.objects)

    def another_curator_commits_first(key):
        if key == "_release/latest.json":
            r2.objects[key] = (b'{"release": "someone-else"}', {})

    r2.before_put = another_curator_commits_first
    with pytest.raises(RuntimeError, match="Another release was published first"):
        store.publish_base_data(pogs[648000], REFS[0], "Mine.", client=r2, **METADATA)  # a new version of the same dataset
    # The plain path still serves the published bytes; the release file and entry were deleted. Only staged bytes and the
    # archive copy remain, both harmless and reused by the rerun.
    assert r2.body(REFS[0]) == read(pogs[324000])
    assert {k for k in r2.objects if k not in before and not k.startswith(("_staging/", "static/"))} == {"_release/latest.json"} - set(before)

def test_archiving_refused_when_the_plain_path_is_out_of_date(pogs):
    r2 = FakeR2()
    store.publish_base_data(pogs[324000], REFS[0], "Initial.", client=r2, **METADATA)
    r2.objects[REFS[0]] = (b"something else", {"sha256": "0" * 64})  # as if a previous run stopped after its commit
    with pytest.raises(ValueError, match="doesn't hold the published version"):
        store.publish_base_data(pogs[648000], REFS[0], "Second.", client=r2, **METADATA)

@pytest.fixture
def manifest(tmp_path, pogs):
    """A local base_data holding the two POGs, with a dataset manifest beside them listing them, one row whose file is absent, and one unsupported row."""
    base_data_dir = tmp_path / "base_data"
    (base_data_dir / "pyramids").mkdir(parents=True)
    for path in pogs.values():
        shutil.copy(path, base_data_dir / "pyramids")
    row = dict(kind="pog", tier="public", variable_class="extensive", code="test", **METADATA)
    rows = [dict(row, ref_path=REFS[0], description="Hectares, 324000 s."), dict(row, ref_path=REFS[1], description="Hectares, 648000 s."),
            dict(row, ref_path="pyramids/ha_per_cell_36000sec.tif"), dict(row, ref_path="pyramids/ha_per_cell_1sec.vrt", kind="vrt", variable_class="")]
    manifest_path = base_data_dir / "pyramids" / "pyramids_base_data_manifest.csv"
    pd.DataFrame(rows)[list(store.MANIFEST_COLUMNS)].to_csv(manifest_path, index=False, encoding="utf-8-sig")
    return str(manifest_path), str(base_data_dir)

def test_manifest_dry_run_reports_every_row_and_writes_nothing(manifest):
    r2 = FakeR2()
    result = store.publish_base_data_from_manifests(base_data_dir=manifest[1], client=r2)
    assert result["manifests"] == [manifest[0]]  # found by searching base_data
    assert result["statuses"] == {REFS[0]: "new", REFS[1]: "new", "pyramids/ha_per_cell_36000sec.tif": "missing_locally", "pyramids/ha_per_cell_1sec.vrt": "unsupported"}
    assert result["plan"]["problems"] == [] and r2.objects == {}

def test_manifests_are_combined_and_a_ref_path_listed_twice_is_refused(manifest):
    other = os.path.join(manifest[1], "lulc", "lulc_base_data_manifest.csv")
    os.makedirs(os.path.dirname(other))
    pd.read_csv(manifest[0], encoding="utf-8-sig", dtype=str, keep_default_na=False).head(1).to_csv(other, index=False, encoding="utf-8-sig")
    os.makedirs(os.path.join(manifest[1], "lulc", "raw"))
    shutil.copy(other, os.path.join(manifest[1], "lulc", "raw", "downloaded_base_data_manifest.csv"))  # raw/ is never searched
    assert store.find_base_data_manifests(manifest[1]) == sorted([manifest[0], other])
    with pytest.raises(ValueError, match="listed more than once"):
        store.publish_base_data_from_manifests(base_data_dir=manifest[1], client=FakeR2())

def test_manifest_apply_then_rerun_is_unchanged(manifest):
    r2 = FakeR2()
    result = store.publish_base_data_from_manifests(base_data_dir=manifest[1], note="First.", dry_run=False, client=r2)
    entry = r2.json(f"_catalogue/{REFS[1]}/{result['plan']['release']}.json")
    assert entry["description"] == "Hectares, 648000 s." and entry["provenance"]["code"] == "test"  # each row's own metadata
    assert entry["provenance"]["promoted_from"] is None  # published straight from base_data, not promoted from a submission
    rerun = store.publish_base_data_from_manifests(base_data_dir=manifest[1], client=r2)
    assert rerun["plan"] is None and rerun["statuses"][REFS[0]] == rerun["statuses"][REFS[1]] == "unchanged"

def test_manifest_changed_file_and_unlisted_dataset(manifest, pogs):
    r2 = FakeR2()
    first = store.publish_base_data_from_manifests(base_data_dir=manifest[1], note="First.", dry_run=False, client=r2)
    shutil.copy(pogs[648000], os.path.join(manifest[1], *REFS[0].split("/")))  # new bytes under the first ref path
    df = pd.read_csv(manifest[0], encoding="utf-8-sig", dtype=str, keep_default_na=False)
    df[df["ref_path"] != REFS[1]].to_csv(manifest[0], index=False, encoding="utf-8-sig")  # drop the second row
    result = store.publish_base_data_from_manifests(base_data_dir=manifest[1], note="Second.", dry_run=False, client=r2)
    assert result["statuses"][REFS[0]] == "changed" and result["statuses"][REFS[1]] == "not_in_manifest"
    assert result["plan"]["datasets"][0]["version"] == 2
    assert r2.body(f"static/pyramids/ha_per_cell_324000sec/v{first['plan']['release'].replace('.', '_')}.tif") == read(pogs[324000])

def test_manifest_finishes_a_plain_path_left_unfinished(manifest, pogs):
    r2 = FakeR2()
    store.publish_base_data_from_manifests(base_data_dir=manifest[1], note="First.", dry_run=False, client=r2)
    r2.objects[REFS[0]] = (b"stale", {"sha256": "0" * 64})  # as if the run stopped after its commit, before moving this file into place
    report = store.publish_base_data_from_manifests(base_data_dir=manifest[1], client=r2)
    assert report["statuses"][REFS[0]] == "unfinished" and r2.body(REFS[0]) == b"stale"  # a dry run only reports
    store.publish_base_data_from_manifests(base_data_dir=manifest[1], note="Finish.", dry_run=False, client=r2)
    assert r2.body(REFS[0]) == read(pogs[324000])
    assert store.publish_base_data_from_manifests(base_data_dir=manifest[1], client=r2)["statuses"][REFS[0]] == "unchanged"

def test_manifest_apply_needs_a_note(manifest):
    with pytest.raises(ValueError, match="change note"):
        store.publish_base_data_from_manifests(base_data_dir=manifest[1], dry_run=False, client=FakeR2())

@pytest.fixture
def incoming(tmp_path, pogs):
    """A folder to add: a POG, a plain GeoTIFF (no variable class) in a subfolder, a table, and things that aren't data."""
    from osgeo import gdal
    import numpy as np
    source_dir = tmp_path / "incoming"
    (source_dir / "sub").mkdir(parents=True)
    shutil.copy(pogs[324000], source_dir / "area_324000sec.tif")
    ds = gdal.GetDriverByName("GTiff").Create(str(source_dir / "sub" / "cropland_900sec.tif"), 1440, 720, 1, gdal.GDT_Float32)
    ds.SetGeoTransform((-180.0, 0.25, 0.0, 90.0, 0.0, -0.25))
    ds.SetProjection(hb.wgs_84_wkt)
    ds.GetRasterBand(1).WriteArray(np.full((720, 1440), 0.5, dtype=np.float32))
    ds = None
    (source_dir / "table.csv").write_text("id,value\n1,2\n")
    (source_dir / "make_it.py").write_text("print('code')\n")
    (source_dir / ".DS_Store").write_bytes(b"x")
    (source_dir / "sub" / "cropland_900sec.tif.aux.xml").write_text("<PAMDataset/>")
    (source_dir / "area_324000sec_displaced_20261020_120000.tif").write_bytes(b"leftover original")
    (source_dir / "old_base_data_manifest.csv").write_text("ref_path\n")
    (source_dir / "raw").mkdir()
    (source_dir / "raw" / "download.nc").write_bytes(b"raw input")
    base_data_dir = tmp_path / "base_data"
    base_data_dir.mkdir()
    manifest_path = tmp_path / "crops_base_data_manifest.csv"  # created by the first real run
    return str(source_dir), str(base_data_dir), str(manifest_path)

def test_add_directory_dry_run_plans_and_writes_nothing(incoming):
    source_dir, base_data_dir, manifest_path = incoming
    result = store.add_directory_to_base_data(source_dir, "crops", manifest_path, base_data_dir=base_data_dir, client=FakeR2(), **METADATA)
    assert result["actions"] == {"crops/area_324000sec.tif": "copy", "crops/sub/cropland_900sec.tif": "make POG", "crops/table.csv": "copy"}
    assert set(result["skipped"]) == {".DS_Store", "make_it.py", "sub/cropland_900sec.tif.aux.xml", "area_324000sec_displaced_20261020_120000.tif",
                                      "old_base_data_manifest.csv", "raw/ (raw input, never added)"}
    assert len(result["problems"]) == 1 and "sub/cropland_900sec.tif: declare its variable class" in result["problems"][0]
    assert os.listdir(base_data_dir) == [] and not os.path.exists(manifest_path)

def test_add_directory_converts_copies_lists_and_dry_runs_publishing(incoming):
    source_dir, base_data_dir, manifest_path = incoming
    overrides = {"sub/*": {"variable_class": "intensive", "units": "proportion", "description": "Cropland share."}}
    result = store.add_directory_to_base_data(source_dir, "crops", manifest_path, base_data_dir=base_data_dir, overrides=overrides, dry_run=False, client=FakeR2(), **METADATA)
    cropland = os.path.join(base_data_dir, "crops", "sub", "cropland_900sec.tif")
    assert hb.is_path_pog(cropland) and hb.get_pog_metadata(cropland)["POG_VARIABLE_CLASS"] == "intensive"
    assert read(os.path.join(base_data_dir, "crops", "area_324000sec.tif")) == read(os.path.join(source_dir, "area_324000sec.tif"))
    manifest = pd.read_csv(manifest_path, encoding="utf-8-sig", dtype=str, keep_default_na=False).set_index("ref_path")
    assert manifest["kind"].to_dict() == {"crops/area_324000sec.tif": "pog", "crops/sub/cropland_900sec.tif": "pog", "crops/table.csv": "table"}
    assert manifest["variable_class"].to_dict() == {"crops/area_324000sec.tif": "extensive", "crops/sub/cropland_900sec.tif": "intensive", "crops/table.csv": ""}
    assert manifest.loc["crops/sub/cropland_900sec.tif", "units"] == "proportion"
    assert result["publish"]["statuses"] == {"crops/area_324000sec.tif": "new", "crops/sub/cropland_900sec.tif": "new", "crops/table.csv": "unsupported"}
    assert any("depends on datasets that are not published: ['pyramids/ha_per_cell_900sec.tif']" in p for p in result["publish"]["plan"]["problems"])
    again = store.add_directory_to_base_data(source_dir, "crops", manifest_path, base_data_dir=base_data_dir, overrides=overrides, client=FakeR2(), **METADATA)
    assert set(again["actions"].values()) == {"already there"} and again["problems"] == []  # rerunning the same folder is a no-op

@pytest.mark.parametrize("parallel", [True, False])
def test_publishing_converts_rasters_an_ingestion_script_left_unconverted(incoming, parallel):
    source_dir, base_data_dir, manifest_path = incoming
    r2 = FakeR2()
    overrides = {"sub/*": {"variable_class": "extensive"}}
    added = store.add_directory_to_base_data(source_dir, "crops", manifest_path, base_data_dir=base_data_dir, overrides=overrides, include=["sub/*"], make_pogs=False,
                                             dry_run=False, client=r2, **METADATA)
    cropland = os.path.join(base_data_dir, "crops", "sub", "cropland_900sec.tif")
    assert added["actions"] == {"crops/sub/cropland_900sec.tif": "copy; publishing makes POG"} and not hb.is_path_pog(cropland)
    assert added["publish"]["statuses"] == {"crops/sub/cropland_900sec.tif": "needs_pog"}  # a dry run reports it and converts nothing
    store.publish_base_data_from_manifests(base_data_dir=base_data_dir, manifest_paths=[manifest_path], note="First.", parallel=parallel, dry_run=False, client=r2)
    assert hb.is_path_pog(cropland) and hb.get_pog_metadata(cropland)["POG_VARIABLE_CLASS"] == "extensive"
    assert store.publish_base_data_from_manifests(base_data_dir=base_data_dir, manifest_paths=[manifest_path], client=r2)["statuses"] == {"crops/sub/cropland_900sec.tif": "unchanged"}

def test_add_directory_refuses_to_replace_a_different_file(incoming, pogs):
    source_dir, base_data_dir, manifest_path = incoming
    os.makedirs(os.path.join(base_data_dir, "crops"))
    shutil.copy(pogs[648000], os.path.join(base_data_dir, "crops", "area_324000sec.tif"))
    result = store.add_directory_to_base_data(source_dir, "crops", manifest_path, base_data_dir=base_data_dir, variable_class="intensive", client=FakeR2(), **METADATA)
    assert result["problems"] == ["area_324000sec.tif: crops/area_324000sec.tif already exists in base_data and differs; set overwrite to replace it"]

def test_add_directory_can_ignore_subdirectories_and_filter_files(incoming):
    source_dir, base_data_dir, manifest_path = incoming
    result = store.add_directory_to_base_data(source_dir, "crops", manifest_path, base_data_dir=base_data_dir, include_subdirectories=False, client=FakeR2(), **METADATA)
    assert result["actions"] == {"crops/area_324000sec.tif": "copy", "crops/table.csv": "copy"} and "sub/ (subdirectory)" in result["skipped"]
    assert result["problems"] == []  # the undeclared raster in sub/ isn't considered at all
    only_tables = store.add_directory_to_base_data(source_dir, "crops", manifest_path, base_data_dir=base_data_dir, include=["*.csv"], client=FakeR2(), **METADATA)
    assert only_tables["actions"] == {"crops/table.csv": "copy"}

def test_add_directory_needs_a_dataset_manifest_name(incoming):
    source_dir, base_data_dir, _ = incoming
    with pytest.raises(ValueError, match="_base_data_manifest.csv"):
        store.add_directory_to_base_data(source_dir, "crops", os.path.join(base_data_dir, "crops.csv"), base_data_dir=base_data_dir, **METADATA)

def test_add_directory_gives_the_same_plan_with_one_worker_or_several(incoming):
    source_dir, base_data_dir, manifest_path = incoming
    plans = [store.add_directory_to_base_data(source_dir, "crops", manifest_path, base_data_dir=base_data_dir, n_workers=n, client=FakeR2(), **METADATA)
             for n in (1, 4)]
    assert plans[0]["actions"] == plans[1]["actions"] and plans[0]["problems"] == plans[1]["problems"]
    assert list(plans[0]["actions"]) == list(plans[1]["actions"])  # reported in walk order, however the work was scheduled

def test_add_directory_reports_a_failed_file_without_stopping_the_others(incoming, monkeypatch):
    source_dir, base_data_dir, manifest_path = incoming
    real_copy = shutil.copy2

    def copy_that_fails_for_the_table(source, destination):
        if source.endswith("table.csv"):
            raise OSError("disk full")
        return real_copy(source, destination)

    monkeypatch.setattr(store.shutil, "copy2", copy_that_fails_for_the_table)
    with pytest.raises(RuntimeError, match=r"crops/table.csv: OSError: disk full"):
        store.add_directory_to_base_data(source_dir, "crops", manifest_path, base_data_dir=base_data_dir, include_subdirectories=False, n_workers=3,
                                         dry_run=False, client=FakeR2(), **METADATA)
    assert os.path.exists(os.path.join(base_data_dir, "crops", "area_324000sec.tif")) and not os.path.exists(manifest_path)

def test_publishing_gives_the_same_plan_in_parallel_or_one_at_a_time(manifest):
    reports = [store.publish_base_data_from_manifests(base_data_dir=manifest[1], parallel=parallel, n_workers=4, client=FakeR2()) for parallel in (True, False)]
    assert reports[0]["statuses"] == reports[1]["statuses"]
    assert reports[0]["plan"]["datasets"] == reports[1]["plan"]["datasets"] and reports[0]["plan"]["problems"] == reports[1]["plan"]["problems"]

def test_run_each_keeps_order_and_collects_every_failure():
    assert store._run_each(lambda x: x * x, list(range(20)), parallel=True, n_workers=5) == [x * x for x in range(20)]
    def fails_on_odd(x):
        if x % 2:
            raise ValueError(f"odd {x}")
    failures = store._run_each_collecting_failures(fails_on_odd, list(range(6)), parallel=True, n_workers=3)
    assert failures == ["1: ValueError: odd 1", "3: ValueError: odd 3", "5: ValueError: odd 5"]  # all of them, in order

@pytest.fixture
def site(tmp_path):
    """Minimal page templates, in the shape of earth_economy_devstack/docs/base_data."""
    site_dir = tmp_path / "site_templates"
    site_dir.mkdir()
    (site_dir / "_landing.html").write_text("<p>%%N_DATASETS%% datasets in %%N_COLLECTIONS%%, release %%RELEASE%%</p>%%COLLECTION_CARDS%%%%FOLDER_TREE%%",
                                            encoding="utf-8")
    (site_dir / "_folder_page.qmd").write_text("---\npagetitle: %%PAGE_TITLE%%\nformat:\n  html:\n    embed-resources: true\n    css: %%ROOT%%styles.css\n---\n\n%%BODY%%\n",
                                               encoding="utf-8")
    (site_dir / "_styles.css").write_text("body { color: black; }", encoding="utf-8")
    (site_dir / "_collections.yml").write_text("pyramids:\n  title: Pyramids\n  tagline: The grids\n", encoding="utf-8")
    (site_dir / "teems_logo.png").write_bytes(b"not really a png")
    return str(site_dir)

needs_quarto = pytest.mark.skipif(shutil.which("quarto") is None, reason="Quarto isn't installed")

@needs_quarto
def test_pages_are_rebuilt_after_a_real_publish(manifest, site):
    with open(os.path.join(manifest[1], "pyramids", "pyramids_base_data_ingestion.py"), "w") as f:
        f.write('"""Made by the test ingestion script.\n\n  1. first step\n  2. second step,\n     continued\n"""\n')
    r2 = FakeR2()
    store.publish_base_data_from_manifests(base_data_dir=manifest[1], note="First.", dry_run=False, client=r2, site_dir=site)
    assert {"index.html", "pyramids/index.html", "teems_logo.png"} <= set(r2.objects)
    landing, page = r2.body("index.html").decode("utf-8"), r2.body("pyramids/index.html").decode("utf-8")
    assert "2 datasets in 1, release" in landing and 'href="/pyramids/"' in landing and "The grids" in landing
    assert all(posixpath.basename(r) in page for r in REFS) and "ha_per_cell_36000sec" not in page  # published rows only
    assert "Made by the test ingestion script." in page and "2. second step, continued" in page  # the About section, reflowed

@needs_quarto
def test_page_dry_run_builds_locally_and_uploads_nothing(manifest, site, tmp_path):
    r2 = FakeR2()
    store.publish_base_data_from_manifests(base_data_dir=manifest[1], note="First.", dry_run=False, client=r2)
    before = dict(r2.objects)
    output_dir = store.write_base_data_index_pages(site, manifest[1], output_dir=str(tmp_path / "built"), client=r2)
    assert os.path.exists(os.path.join(output_dir, "index.html")) and os.path.exists(os.path.join(output_dir, "pyramids", "index.html"))
    assert r2.objects == before

@needs_quarto
def test_folder_without_yaml_gets_its_text_from_its_script_and_the_landing_lists_every_folder(manifest, site, pogs):
    base_data_dir = manifest[1]
    nested = os.path.join(base_data_dir, "lulc", "esa", "seals7")
    os.makedirs(nested)
    shutil.copy(pogs[324000], os.path.join(nested, "ha_per_cell_324000sec.tif"))
    row = dict(ref_path="lulc/esa/seals7/ha_per_cell_324000sec.tif", kind="pog", tier="public", variable_class="extensive", code="test", **METADATA)
    pd.DataFrame([row])[list(store.MANIFEST_COLUMNS)].to_csv(os.path.join(nested, "lulc_esa_seals7_base_data_manifest.csv"), index=False, encoding="utf-8-sig")
    with open(os.path.join(nested, "lulc_esa_seals7_base_data_ingestion.py"), "w") as f:
        f.write('"""Reclassify the maps to the seals7 legend, at lulc_esa_seals7_<year>.tif. A second sentence.\n\nMaintainer notes.\n"""\n')
    r2 = FakeR2()
    store.publish_base_data_from_manifests(base_data_dir=base_data_dir, note="First.", dry_run=False, client=r2, site_dir=site)
    landing = r2.body("index.html").decode("utf-8")
    assert all(f'href="/{f}/"' in landing for f in ("pyramids", "lulc", "lulc/esa", "lulc/esa/seals7"))  # the tree lists every folder
    assert "The grids" in landing and "Reclassify the maps to the seals7 legend, at lulc_esa_seals7&lt;year&gt;.tif." not in landing
    assert "Reclassify the maps to the seals7 legend, at lulc_esa_seals7_&lt;year&gt;.tif." in landing  # the first sentence, as the tagline
    assert {"lulc/index.html", "lulc/esa/index.html", "lulc/esa/seals7/index.html"} <= set(r2.objects)  # parents with no rows get pages too
    parent, page = r2.body("lulc/esa/index.html").decode("utf-8"), r2.body("lulc/esa/seals7/index.html").decode("utf-8")
    assert 'href="/lulc/esa/seals7/"' in parent and "seals7 legend" in parent and "<b>1</b> file<" in parent
    assert '<div class="tree">' not in landing[landing.index('<a class="card" href="/lulc/">'):].split("</a>")[0]  # cards carry no tree
    lulc_page = r2.body("lulc/index.html").decode("utf-8")
    assert lulc_page.index("Datasets</h2>") < lulc_page.index('<div class="cards">') < lulc_page.index('<div class="tree">')  # a collection: dataset cards, then its tree
    tree = lulc_page[lulc_page.index('<div class="tree">'):]
    assert 'href="/lulc/esa/"' in tree and 'href="/lulc/esa/seals7/"' in tree and 'href="/pyramids/"' not in tree  # pared to the collection
    assert parent.index("Derived products</h2>") < parent.index('<div class="cards">') < parent.index('<div class="tree">')  # a dataset: derived products
    assert "Folders</h2>" not in lulc_page + parent
    assert '<div class="tree">' not in r2.body("pyramids/index.html").decode("utf-8")  # no subfolders: no tree
    assert "A second sentence." in page and "Maintainer notes." in page  # the lede (first paragraph) and the About section (all of it)
    assert "Files</h2>" in page and "Datasets</h2>" not in page  # the table of a folder's rows is headed Files; Datasets are the folders of a collection

def test_docstring_texts_take_the_first_sentence_and_paragraph():
    assert store._get_docstring_texts("One sentence only.\n\nSecond paragraph.") == {"tagline": "One sentence only.", "about": ""}
    assert store._get_docstring_texts("First\nsentence. Then more\ntext.\n\nLater.") == {"tagline": "First sentence.", "about": "First sentence. Then more text."}

def test_dataset_table_shows_shared_metadata_once_and_archived_versions():
    row = dict(kind="pog", tier="public", variable_class="extensive", units="ha", license="CC-BY-4.0", data_source="doi:10.1/x", code="test",
               version=2, release="2026.10.20.1", size=2_500_000, rung="10")
    rows = [dict(row, ref_path="pyramids/a.tif", description="A.", archive_keys=["static/pyramids/a/v2026_10_06_1.tif"]),
            dict(row, ref_path="pyramids/b.tif", description="B.", archive_keys=[])]
    table = store._get_dataset_table_html(rows)
    assert table.count("CC-BY-4.0") == 1 and '<a href="https://doi.org/10.1/x">' in table  # shared, shown once, linked
    assert "<th>Description</th>" in table and ">A.<" in table and ">B.<" in table  # differs by row: a column
    assert '<a class="archive" href="https://data.teemlabs.org/static/pyramids/a/v2026_10_06_1.tif">2026.10.06.1</a>' in table
    assert "2.5 MB" in table and "10\u2033" in table

def test_resolve_dry_run_passes_bools_and_gates_on_the_date():
    import datetime
    today = datetime.date.today()
    assert store.resolve_dry_run(True) is True
    assert store.resolve_dry_run(False) is False
    assert store.resolve_dry_run(today - datetime.timedelta(days=1)) is True   # yesterday's date has gone stale
    assert store.resolve_dry_run(today) is False                               # armed for today
    assert store.resolve_dry_run((today + datetime.timedelta(days=1)).isoformat()) is False
    assert store.resolve_dry_run((today - datetime.timedelta(days=30)).isoformat()) is True
    with pytest.raises(ValueError):
        store.resolve_dry_run("yesterday")
    with pytest.raises(TypeError):
        store.resolve_dry_run(None)

def test_add_directory_accepts_a_stale_date_as_a_dry_run(incoming):
    source_dir, base_data_dir, manifest_path = incoming
    result = store.add_directory_to_base_data(source_dir, "crops", manifest_path, base_data_dir=base_data_dir, dry_run="2000-01-01", client=FakeR2(), **METADATA)
    assert result["publish"] is None and not os.path.exists(manifest_path) and not os.listdir(base_data_dir)
