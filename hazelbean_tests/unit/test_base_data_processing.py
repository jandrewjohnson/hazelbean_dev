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
    """The few boto3 S3 client methods publishing uses. objects maps each key of the public bucket to (bytes, user metadata);
    internal is the same for the internal bucket."""
    def __init__(self):
        self.objects, self.internal = {}, {}
        self.before_put = None  # called with the key before each put, to simulate another curator

    def bucket(self, name):
        return self.internal if name == store.BUCKETS["internal"] else self.objects

    def put_object(self, Bucket, Key, Body, IfMatch=None, IfNoneMatch=None, Metadata=None, **kwargs):
        if self.before_put:
            self.before_put(Key)
        existing = self.bucket(Bucket).get(Key)
        if (IfNoneMatch == "*" and existing is not None) or (IfMatch is not None and (existing is None or self.etag(existing[0]) != IfMatch)):
            raise FakeClientError(412)
        self.bucket(Bucket)[Key] = (Body, Metadata or {})

    def get_object(self, Bucket, Key):
        if Key not in self.bucket(Bucket):
            raise FakeClientError(404)
        return {"Body": io.BytesIO(self.bucket(Bucket)[Key][0]), "ETag": self.etag(self.bucket(Bucket)[Key][0])}

    def head_object(self, Bucket, Key):
        if Key not in self.bucket(Bucket):
            raise FakeClientError(404)
        return {"ContentLength": len(self.bucket(Bucket)[Key][0]), "Metadata": dict(self.bucket(Bucket)[Key][1])}

    def upload_file(self, Filename, Bucket, Key, ExtraArgs=None, Callback=None):
        with open(Filename, "rb") as f:
            self.bucket(Bucket)[Key] = (f.read(), dict((ExtraArgs or {}).get("Metadata", {})))
        if Callback:
            Callback(len(self.bucket(Bucket)[Key][0]))

    def copy(self, CopySource, Bucket, Key, ExtraArgs=None, Callback=None):
        body, metadata = self.bucket(CopySource["Bucket"])[CopySource["Key"]]
        self.bucket(Bucket)[Key] = (body, dict((ExtraArgs or {}).get("Metadata", metadata)))
        if Callback:
            Callback(len(body))

    def delete_object(self, Bucket, Key):
        self.bucket(Bucket).pop(Key, None)

    def list_objects_v2(self, Bucket, Prefix=""):
        return {"Contents": [{"Key": k} for k in sorted(self.bucket(Bucket)) if k.startswith(Prefix)], "IsTruncated": False}

    def etag(self, body):
        return '"' + hashlib.md5(body).hexdigest() + '"'

    def json(self, key):
        return json.loads(self.objects[key][0])

    def body(self, key):
        return self.objects[key][0]

def read(path):
    with open(path, "rb") as f:
        return f.read()

@pytest.fixture(autouse=True)
def no_site_templates(tmp_path, monkeypatch):
    """Writing a readme renders its page from the devstack's templates when they are on the machine: not in a test, unless it names them."""
    monkeypatch.setattr(store, "SITE_DIR", str(tmp_path / "no_site_templates"))

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
    row = dict(kind="pog", tier="public", variable_class="extensive", code="test", legend="", color_ramp="", **METADATA)
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

def test_retiring_a_dataset_drops_it_from_a_new_release_and_deletes_its_files(pogs):
    r2 = FakeR2()
    first = store.publish_base_data(list(pogs.values()), REFS, "Initial.", client=r2, **METADATA)
    r2.objects[REFS[0] + ".yml"] = r2.objects["pyramids/index.html"] = (b"", {})
    before = dict(r2.objects)
    plan = store.retire_base_data(REFS[0], "Withdrawn.", client=r2)  # a dry run by default
    assert plan["deleted"] == [REFS[0], REFS[0] + ".yml"] and not plan["written"] and r2.objects == before
    plan = store.retire_base_data(REFS[0], "Withdrawn.", dry_run=False, client=r2)
    release = r2.json(f"_release/{plan['release']}.json")
    assert r2.json("_release/latest.json") == {"release": plan["release"]} and release["parent"] == first["release"]
    assert set(release["datasets"]) == {REFS[1]} and release["retired"] == [REFS[0]]
    assert REFS[0] not in r2.objects and REFS[0] + ".yml" not in r2.objects and REFS[1] in r2.objects and "pyramids/index.html" in r2.objects
    assert f"_catalogue/{REFS[0]}/{first['release']}.json" in r2.objects  # the record of what was published stays
    with pytest.raises(ValueError, match="not in the latest release"):
        store.retire_base_data(REFS[0], "Again.", dry_run=False, client=r2)
    assert store.retire_base_data(REFS[1], "The last one.", dry_run=False, client=r2)["deleted"] == [REFS[1], REFS[1] + ".yml", "pyramids/index.html"]

def set_tier(manifest_path, ref_path, tier):
    df = pd.read_csv(manifest_path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    df.loc[df["ref_path"] == ref_path, "tier"] = tier
    df.to_csv(manifest_path, index=False, encoding="utf-8-sig")

def test_an_internal_row_is_published_to_the_internal_bucket_and_recorded_in_the_one_release(manifest, pogs):
    r2 = FakeR2()
    set_tier(manifest[0], REFS[1], "internal")
    result = store.publish_base_data_from_manifests(base_data_dir=manifest[1], note="First.", dry_run=False, client=r2)
    release = result["plan"]["release"]
    assert r2.internal[REFS[1]][0] == read(pogs[648000]) and set(r2.internal) == {REFS[1]}  # its bytes, and nothing else, behind the login
    assert REFS[1] not in r2.objects and r2.body(REFS[0]) == read(pogs[324000])
    assert {r: d["tier"] for r, d in r2.json(f"_release/{release}.json")["datasets"].items()} == {REFS[0]: "public", REFS[1]: "internal"}
    assert r2.json(f"_catalogue/{REFS[1]}/{release}.json")["tier"] == "internal"  # listed and described in the public bucket
    rerun = store.publish_base_data_from_manifests(base_data_dir=manifest[1], client=r2)
    assert rerun["statuses"][REFS[1]] == "unchanged" and rerun["plan"] is None

    shutil.copy(pogs[324000], os.path.join(manifest[1], *REFS[1].split("/")))  # a second version: the first is archived beside it, in the internal bucket
    second = store.publish_base_data_from_manifests(base_data_dir=manifest[1], note="Second.", dry_run=False, client=r2)
    assert r2.internal[f"static/pyramids/ha_per_cell_648000sec/v{release.replace('.', '_')}.tif"][0] == read(pogs[648000])
    assert not any(k.startswith("static/") for k in r2.objects) and second["plan"]["datasets"][0]["version"] == 2

    set_tier(manifest[0], REFS[0], "internal")  # a published dataset doesn't change tier by itself: it is reported, and nothing moves
    moved = store.publish_base_data_from_manifests(base_data_dir=manifest[1], note="Third.", dry_run=False, client=r2)
    assert moved["statuses"][REFS[0]] == "tier_changed" and moved["plan"] is None and REFS[0] in r2.objects and REFS[0] not in r2.internal
    set_tier(manifest[0], REFS[1], "unpublished")
    assert store.publish_base_data_from_manifests(base_data_dir=manifest[1], client=r2)["statuses"][REFS[1]] == "tier_changed"

    plan = store.retire_base_data(REFS[1], "Withdrawn.", dry_run=False, client=r2)  # its file leaves the internal bucket; the archived version stays
    assert REFS[1] not in r2.internal and REFS[1] in plan["deleted"] and any(k.startswith("static/") for k in r2.internal)

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
    (source_dir / "sub" / "cropland_900sec.tif.yml").write_text("title: a geometamaker sidecar\n")
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
    assert set(result["skipped"]) == {".DS_Store", "make_it.py", "sub/cropland_900sec.tif.aux.xml", "sub/cropland_900sec.tif.yml", "area_324000sec_displaced_20261020_120000.tif",
                                      "old_base_data_manifest.csv", "raw/ (raw input, never added)"}
    assert len(result["problems"]) == 1 and "sub/cropland_900sec.tif: declare its variable class" in result["problems"][0]
    assert os.listdir(base_data_dir) == [] and not os.path.exists(manifest_path)

def test_add_directory_converts_copies_lists_and_dry_runs_publishing(incoming):
    source_dir, base_data_dir, manifest_path = incoming
    overrides = {"sub/*": {"variable_class": "intensive", "units": "proportion", "description": "Cropland share."}, "table.csv": {"tier": "unpublished"}}
    wrong = store.add_directory_to_base_data(source_dir, "crops", manifest_path, base_data_dir=base_data_dir, overrides=dict(overrides, **{"table.csv": {"tier": "private"}}), client=FakeR2(), **METADATA)
    assert wrong["problems"] == ["table.csv: its tier is 'private', which is not one of public, internal, unpublished"]
    result = store.add_directory_to_base_data(source_dir, "crops", manifest_path, base_data_dir=base_data_dir, overrides=overrides, dry_run=False, client=FakeR2(), **METADATA)
    cropland = os.path.join(base_data_dir, "crops", "sub", "cropland_900sec.tif")
    assert hb.is_path_pog(cropland) and hb.get_pog_metadata(cropland)["POG_VARIABLE_CLASS"] == "intensive"
    assert read(os.path.join(base_data_dir, "crops", "area_324000sec.tif")) == read(os.path.join(source_dir, "area_324000sec.tif"))
    manifest = pd.read_csv(manifest_path, encoding="utf-8-sig", dtype=str, keep_default_na=False).set_index("ref_path")
    assert manifest["kind"].to_dict() == {"crops/area_324000sec.tif": "pog", "crops/sub/cropland_900sec.tif": "pog", "crops/table.csv": "table"}
    assert manifest["variable_class"].to_dict() == {"crops/area_324000sec.tif": "extensive", "crops/sub/cropland_900sec.tif": "intensive", "crops/table.csv": ""}
    assert manifest.loc["crops/sub/cropland_900sec.tif", "units"] == "proportion"
    assert manifest["tier"].to_dict() == {"crops/area_324000sec.tif": "public", "crops/sub/cropland_900sec.tif": "public", "crops/table.csv": "unpublished"}
    assert result["publish"]["statuses"] == {"crops/area_324000sec.tif": "new", "crops/sub/cropland_900sec.tif": "new", "crops/table.csv": "unpublished"}  # listed, and hosted nowhere
    assert any("depends on datasets that are not published: ['pyramids/ha_per_cell_900sec.tif']" in p for p in result["publish"]["plan"]["problems"])
    again = store.add_directory_to_base_data(source_dir, "crops", manifest_path, base_data_dir=base_data_dir, overrides=overrides, client=FakeR2(), **METADATA)
    assert set(again["actions"].values()) == {"already there"} and again["problems"] == []  # rerunning the same folder is a no-op
    df = pd.read_csv(manifest_path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    df.loc[df["ref_path"] == "crops/table.csv", "tier"] = "internal"
    df.to_csv(manifest_path, index=False, encoding="utf-8-sig")
    internal = store.publish_base_data_from_manifests(base_data_dir=base_data_dir, manifest_paths=[manifest_path], client=FakeR2())
    assert internal["statuses"]["crops/table.csv"] == "new"  # an internal row is published like a public one, to the other bucket
    df.loc[df["ref_path"] == "crops/table.csv", "tier"] = "private"
    df.to_csv(manifest_path, index=False, encoding="utf-8-sig")
    with pytest.raises(ValueError, match="tier is one of public, internal, unpublished"):
        store.publish_base_data_from_manifests(base_data_dir=base_data_dir, manifest_paths=[manifest_path], client=FakeR2())

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
        f.write('"""Made by the test ingestion script.\n\n  1. first step\n  2. second step,\n     continued\nFrom https://example.org/x and doi:10.1/y.\n"""\n')
    r2 = FakeR2()
    store.publish_base_data_from_manifests(base_data_dir=manifest[1], note="First.", dry_run=False, client=r2, site_dir=site)
    assert {"index.html", "pyramids/index.html", "teems_logo.png"} <= set(r2.objects)
    landing, page = r2.body("index.html").decode("utf-8"), r2.body("pyramids/index.html").decode("utf-8")
    assert "2 datasets in 1, release" in landing and 'href="/pyramids/"' in landing and "The grids" in landing
    assert all(posixpath.basename(r) in page for r in REFS) and "ha_per_cell_36000sec" not in page  # published rows only
    assert "Made by the test ingestion script." in page and "<ol" in page and "second step," in page  # the docstring, rendered as Markdown
    assert "Processing steps</h2>" in page and "About</h2>" not in page and 'class="about"' not in page
    assert '<a href="https://example.org/x"' in page and '<a href="https://doi.org/10.1/y"' in page and "</ol>\n<p>From" in page  # linked; the list closed before the line
    assert page.index("Metadata</h2>") < page.index("Processing steps</h2>") and "Files</h2>" not in page  # the metadata and table first, the steps last
    assert f'href="https://data.teemlabs.org/{REFS[0]}.yml" class="sidecar">yml</a>' in page  # Quarto re-emits the table with the attributes reordered

@needs_quarto
def test_an_internal_file_is_listed_on_the_public_page_as_requiring_credentials(manifest, site):
    r2 = FakeR2()
    set_tier(manifest[0], REFS[1], "internal")
    store.publish_base_data_from_manifests(base_data_dir=manifest[1], note="First.", dry_run=False, client=r2, site_dir=site)
    page = r2.body("pyramids/index.html").decode("utf-8")
    assert f'href="https://internal.teemlabs.org/{REFS[1]}"' in page and f'href="https://data.teemlabs.org/{REFS[1]}"' not in page
    assert page.count("requires credentials") == 1 and f'href="https://data.teemlabs.org/{REFS[0]}"' in page
    assert not any(k.endswith("index.html") for k in r2.internal)  # the pages are public

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
    row = dict(ref_path="lulc/esa/seals7/ha_per_cell_324000sec.tif", kind="pog", tier="public", variable_class="extensive", code="test", legend="", color_ramp="", **METADATA)
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
    assert "A second sentence." in page and "Maintainer notes." in page  # the lede (first paragraph) and the Processing steps (all of it)
    assert "Metadata</h2>" in page and "Datasets</h2>" not in page  # a folder's rows are headed Metadata; Datasets are the folders of a collection
    assert "lulc_esa_seals7_&lt;year&gt;.tif" in page and "<year>" not in page  # the docstring's <year> stays text in the Markdown too

def test_cards_show_the_first_sentences_and_docstrings_become_markdown():
    about = "One. Two! Three? Four. Five."
    assert store._first_sentences(about) == "One. Two! Three?" and store._first_sentences("Only one.") == "Only one."
    assert store._first_sentences(about, n=2) == "One. Two!"
    docstring = "Lead sentence, lulc_esa_<year>.tif.\n\nSteps, in order:\n  1. first\n     continued\n  2. second\n- a bullet\nAfter.\n\nLast."
    markdown = store._get_docstring_markdown(docstring)
    assert "Steps, in order:\n\n  1. first\n     continued\n  2. second\n- a bullet\n\nAfter.\n\nLast." in markdown  # blank lines open and close the list, none inside it
    assert "lulc_esa_\\<year\\>.tif" in markdown
    assert store._get_docstring_markdown("See https://zenodo.org/records/1 and doi:10.5281/zenodo.1, done.") == \
        "See <https://zenodo.org/records/1> and [doi:10.5281/zenodo.1](https://doi.org/10.5281/zenodo.1), done."  # Quarto links neither by itself

@needs_quarto
def test_long_card_text_is_cut_but_the_page_keeps_it(manifest, site):
    about = "First sentence. Second sentence. Third sentence. Fourth sentence, only on the page."
    with open(os.path.join(site, "_collections.yml"), "a") as f:
        f.write(f"  about: {about}\n")
    r2 = FakeR2()
    store.publish_base_data_from_manifests(base_data_dir=manifest[1], note="First.", dry_run=False, client=r2, site_dir=site)
    landing, page = r2.body("index.html").decode("utf-8"), r2.body("pyramids/index.html").decode("utf-8")
    assert "Third sentence.</p>" in landing and "Fourth sentence" not in landing  # the card: three sentences
    assert "Fourth sentence, only on the page." in page

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
    assert table.endswith("</tbody></table></div>") and "<th>Metadata</th></tr>" in table  # the yml sidecar: the last column
    assert table.count('class="sidecar"') == 2 and 'href="https://data.teemlabs.org/pyramids/a.tif.yml">yml</a></td></tr>' in table
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

@pytest.fixture
def mixed_manifest(manifest):
    """The pyramids manifest plus a cartographic folder holding a tiny GeoPackage, its CSV twin and a shapefile row (unsupported: several files)."""
    from osgeo import ogr, osr
    base_data_dir = manifest[1]
    folder = os.path.join(base_data_dir, "cartographic", "ee")
    os.makedirs(folder)
    ds = ogr.GetDriverByName("GPKG").CreateDataSource(os.path.join(folder, "regions.gpkg"))
    srs = osr.SpatialReference(); srs.ImportFromEPSG(4326)
    layer = ds.CreateLayer("regions", srs, ogr.wkbPolygon)
    layer.CreateField(ogr.FieldDefn("id", ogr.OFTInteger))
    feature = ogr.Feature(layer.GetLayerDefn()); feature.SetField("id", 1); feature.SetGeometry(ogr.CreateGeometryFromWkt("POLYGON((0 0,1 0,1 1,0 1,0 0))"))
    layer.CreateFeature(feature); ds = None
    pd.DataFrame({"id": [1], "label": ["one"]}).to_csv(os.path.join(folder, "regions.csv"), index=False, encoding="utf-8-sig")
    with open(os.path.join(folder, "old.shp"), "wb") as f:
        f.write(b"not a shapefile")
    row = dict(kind="vector", tier="public", variable_class="", code="test", legend="", color_ramp="", license="ODbL-1.0", units="polygons", data_source="drawn", description="Regions.")
    rows = [dict(row, ref_path="cartographic/ee/regions.gpkg"), dict(row, ref_path="cartographic/ee/regions.csv", kind="table", units="rows"),
            dict(row, ref_path="cartographic/ee/old.shp")]
    pd.DataFrame(rows)[list(store.MANIFEST_COLUMNS)].to_csv(os.path.join(folder, "cartographic_ee_base_data_manifest.csv"), index=False, encoding="utf-8-sig")
    return base_data_dir

def test_vectors_and_tables_publish_as_plain_files_and_shapefiles_stay_unsupported(mixed_manifest, pogs):
    r2 = FakeR2()
    dry = store.publish_base_data_from_manifests(base_data_dir=mixed_manifest, client=r2)
    assert dry["statuses"]["cartographic/ee/regions.gpkg"] == dry["statuses"]["cartographic/ee/regions.csv"] == "new"
    assert dry["statuses"]["cartographic/ee/old.shp"] == "unsupported" and dry["plan"]["problems"] == [] and r2.objects == {}
    result = store.publish_base_data_from_manifests(base_data_dir=mixed_manifest, note="Regions.", dry_run=False, client=r2)
    release = r2.json(f"_release/{result['plan']['release']}.json")
    assert {"cartographic/ee/regions.gpkg", "cartographic/ee/regions.csv"} <= set(release["datasets"]) and "cartographic/ee/old.shp" not in release["datasets"]
    gpkg_path = os.path.join(mixed_manifest, "cartographic", "ee", "regions.gpkg")
    assert r2.body("cartographic/ee/regions.gpkg") == read(gpkg_path) and r2.objects["cartographic/ee/regions.gpkg"][1]["sha256"] == hb.hash_file_path(gpkg_path)
    entry = r2.json(f"_catalogue/cartographic/ee/regions.gpkg/{result['plan']['release']}.json")
    assert entry["kind"] == "vector" and entry["lattice"] is None and entry["semantics"] == {"units": "polygons"} and entry["depends_on"] == []
    assert r2.json(f"_catalogue/cartographic/ee/regions.csv/{result['plan']['release']}.json")["kind"] == "table"
    assert r2.json(f"_catalogue/{REFS[0]}/{result['plan']['release']}.json")["lattice"]["rung"] == "324000"  # POGs unchanged
    again = store.publish_base_data_from_manifests(base_data_dir=mixed_manifest, client=r2)
    assert again["statuses"]["cartographic/ee/regions.gpkg"] == "unchanged" and again["plan"] is None

def test_gate_refuses_an_unsupported_extension_and_a_mismatched_source(tmp_path, pogs):
    txt = tmp_path / "notes.txt"; txt.write_text("x")
    assert "publishing supports .tif POGs" in store.check_publication_status(str(txt), "cartographic/notes.txt")["problems"][0]
    assert "need an existing .gpkg source" in store.check_publication_status(pogs[324000], "cartographic/regions.gpkg")["problems"][0]

@needs_quarto
def test_pages_show_vectors_and_tables_by_kind(mixed_manifest, site):
    r2 = FakeR2()
    store.publish_base_data_from_manifests(base_data_dir=mixed_manifest, note="Regions.", dry_run=False, client=r2, site_dir=site)
    page = r2.body("cartographic/ee/index.html").decode("utf-8")
    assert "regions.gpkg" in page and "regions.csv" in page and "old.shp" not in page
    assert ">vector<" in page and ">table<" in page  # the Resolution cell names the kind
    landing = r2.body("index.html").decode("utf-8")
    assert "4 datasets in 2, release" in landing and 'href="/cartographic/"' in landing

@pytest.fixture
def tileset(tmp_path):
    """A local base_data whose dataset folder cover/demo holds a partial tile set: two 60-degree tiles of a 1-degree extensive raster in
    subpogs/, indexed by counts_partial.vrt in the dataset folder. Returns (dataset folder, base_data, manifest path, a function adding a tile)."""
    import numpy as np
    from osgeo import gdal
    base_data_dir = tmp_path / "base_data"
    folder = base_data_dir / "cover" / "demo"
    tile_dir = folder / "subpogs" / "counts_3600sec_60deg"
    tile_dir.mkdir(parents=True)
    def add_tile(bb):
        source_path = str(tmp_path / f"source_{bb[0]}_{bb[1]}.tif")
        ds = gdal.GetDriverByName("GTiff").Create(source_path, 60, 60, 1, gdal.GDT_Byte)
        ds.SetGeoTransform((bb[0], 1.0, 0, bb[3], 0, -1.0))
        ds.SetProjection(hb.wgs_84_wkt)
        ds.GetRasterBand(1).WriteArray(np.full((60, 60), 1 + abs(bb[0]) // 60, dtype=np.uint8))
        ds = None
        hb.make_paths_pog_tiles([source_path], [str(tile_dir / hb.get_tile_filename_from_bb("counts", 3600, bb))], num_workers=1, variable_class="extensive",
                                remove_intermediate_files=True)
        return hb.build_pog_tileset_vrt(str(tile_dir), str(folder / "counts_partial.vrt"))
    add_tile([-60, -30, 0, 30])
    add_tile([0, -30, 60, 30])
    return str(folder), str(base_data_dir), str(folder / "demo_base_data_manifest.csv"), add_tile

def test_partial_tile_set_is_listed_by_its_vrt_published_with_its_tiles_and_promoted(tileset):
    folder, base_data_dir, manifest_path, add_tile = tileset
    r2, ref, tile_folder = FakeR2(), "cover/demo/counts_partial.vrt", "cover/demo/subpogs/counts_3600sec_60deg/"
    metadata = dict(METADATA, units="count", description="Counts; a partial tile set.")
    added = store.add_directory_to_base_data(folder, "cover/demo", manifest_path, base_data_dir=base_data_dir, dry_run=False, client=r2, **metadata)
    assert added["actions"] == {ref: "already there"} and any(s.startswith("subpogs/") for s in added["skipped"])  # the tiles are never listed one by one
    rows = store._read_manifest(manifest_path).to_dict("records")
    assert [(r["ref_path"], r["kind"], r["variable_class"]) for r in rows] == [(ref, "tileset", "extensive")]
    assert added["publish"]["statuses"] == {ref: "new"} and r2.objects == {}

    first = store.publish_base_data_from_manifests(base_data_dir=base_data_dir, note="Two tiles.", dry_run=False, client=r2)
    tiles = sorted(k for k in r2.objects if k.startswith(tile_folder))
    assert tiles == [tile_folder + "counts_3600sec_30S_0E_60_60.tif", tile_folder + "counts_3600sec_30S_60W_60_60.tif"]
    assert r2.body(ref) == read(os.path.join(folder, "counts_partial.vrt")) and r2.body(tiles[0]) == read(os.path.join(base_data_dir, *tiles[0].split("/")))
    entry = r2.json(f"_catalogue/{ref}/{first['plan']['release']}.json")
    assert entry["kind"] == "tileset" and [f["ref_path"] for f in entry["files"]] == [ref] + tiles
    assert entry["lattice"] == {"rung": "3600", "storage_form": "tileset", "extent": [-180.0, -90.0, 180.0, 90.0], "tile_degrees": 60, "n_tiles": 2, "partial": True}
    assert store.publish_base_data_from_manifests(base_data_dir=base_data_dir, client=r2)["statuses"] == {ref: "unchanged"}

    # A third tile: the set is a new version, only the new tile goes up, and the earlier VRT isn't archived.
    add_tile([60, -30, 120, 30])
    uploaded = []
    upload_file = r2.upload_file
    r2.upload_file = lambda Filename, Bucket, Key, **kwargs: (uploaded.append(Key), upload_file(Filename, Bucket, Key, **kwargs))[1]
    assert store.publish_base_data_from_manifests(base_data_dir=base_data_dir, client=r2)["statuses"] == {ref: "changed"}
    second = store.publish_base_data_from_manifests(base_data_dir=base_data_dir, note="Three tiles.", dry_run=False, client=r2)
    assert [k for k in uploaded if k.startswith(tile_folder)] == [tile_folder + "counts_3600sec_30S_60E_60_60.tif"]
    entry = r2.json(f"_catalogue/{ref}/{second['plan']['release']}.json")
    assert entry["version"] == 2 and entry["lattice"]["n_tiles"] == 3 and entry["previous"]["archive_key"] is None
    assert not [k for k in r2.objects if k.startswith("static/")]

    # Promoted: the partial VRT gives way to the complete one, and its manifest row with it.
    os.remove(os.path.join(folder, "counts_partial.vrt"))
    hb.build_pog_tileset_vrt(os.path.join(folder, "subpogs", "counts_3600sec_60deg"), os.path.join(folder, "counts.vrt"))
    store.add_directory_to_base_data(folder, "cover/demo", manifest_path, base_data_dir=base_data_dir, dry_run=False, client=r2, **metadata)
    assert list(store._read_manifest(manifest_path)["ref_path"]) == ["cover/demo/counts.vrt"]
    third = store.publish_base_data_from_manifests(base_data_dir=base_data_dir, note="Complete.", dry_run=False, client=r2)
    assert third["statuses"] == {"cover/demo/counts.vrt": "new", ref: "not_in_manifest"}
    assert r2.json(f"_catalogue/cover/demo/counts.vrt/{third['plan']['release']}.json")["lattice"]["partial"] is False

def test_dataset_table_marks_a_partial_tile_set():
    row = dict(ref_path="cover/demo/counts_partial.vrt", version=1, release="2026.11.17.1", size=10, rung="3600", kind="tileset", archive_keys=[],
               tiles={"partial": True, "n_tiles": 2}, variable_class="extensive", code="", **METADATA)
    assert '<span class="pill">partial tile set: 2 tiles</span>' in store._get_dataset_table_html([row])


@pytest.fixture
def categorical(tmp_path):
    """A dataset folder in a local base_data: a plain Byte class raster (values 0, 1, 2), its legend, its ingestion script, and the manifest's path."""
    from osgeo import gdal
    import numpy as np
    base_data_dir = tmp_path / "base_data"
    folder = base_data_dir / "lulc" / "toy"
    folder.mkdir(parents=True)
    ds = gdal.GetDriverByName("GTiff").Create(str(folder / "lulc_toy_2020.tif"), 4, 2, 1, gdal.GDT_Byte)
    ds.SetGeoTransform((-180.0, 90.0, 0.0, 90.0, 0.0, -90.0))
    ds.SetProjection(hb.wgs_84_wkt)
    ds.GetRasterBand(1).WriteArray(np.array([[0, 1, 2, 1], [2, 2, 0, 1]], dtype=np.uint8))
    ds = None
    (folder / "lulc_toy_base_data_legend.csv").write_text("id,label,name,description,color\n2,forest,Forest,\"Tree cover, above 10 percent\",#006400\n"
                                                          "0,none,No data,Nothing mapped,#000000\n1,cropland,\"Cropland, rainfed\",Herbaceous crops | rainfed,#ffff64\n", encoding="utf-8-sig")
    (folder / "lulc_toy_base_data_ingestion.py").write_text('"""A toy land cover map. It has three classes.\n\n  1. made by hand\n  2. listed\n"""\n')
    return str(folder), str(base_data_dir), str(folder / "lulc_toy_base_data_manifest.csv")

def test_legend_is_read_sorted_and_gives_colours_and_a_qgis_colour_map(categorical):
    legend_path = os.path.join(categorical[0], "lulc_toy_base_data_legend.csv")
    assert list(store.read_base_data_legend(legend_path)["label"]) == ["none", "cropland", "forest"]
    assert store.get_legend_color_table(legend_path) == {0: (0, 0, 0), 1: (255, 255, 100), 2: (0, 100, 0)}
    assert store.get_qgis_color_map(legend_path) == ("# QGIS Generated Color Map Export File\nINTERPOLATION:EXACT\n0,0,0,0,255,No data\n"
                                                    "1,255,255,100,255,Cropland; rainfed\n2,0,100,0,255,Forest\n")

@pytest.mark.parametrize("text, message", [("id,label,name,color\n1,a,A,#ffffff\n", "lacks the columns"), ("id,label,name,description,color\n1,a,A,x,red\n", "not #rrggbb"),
                                           ("id,label,name,description,color\n1,a,A,x,#ffffff\n1,b,B,y,#000000\n", "more than once"),
                                           ("id,label,name,description,color\n1,a,A,,#ffffff\n", "description is empty"), ("id,label,name,description,color\n", "no rows")])
def test_legend_refuses(tmp_path, text, message):
    path = tmp_path / "x_base_data_legend.csv"
    path.write_text(text)
    with pytest.raises(ValueError, match=message):
        store.read_base_data_legend(str(path))

def test_add_directory_gives_a_categorical_raster_its_legend_colours_and_writes_the_readme(categorical):
    from osgeo import gdal
    folder, base_data_dir, manifest_path = categorical
    kwargs = dict(base_data_dir=base_data_dir, variable_class="categorical", client=FakeR2(), **METADATA)
    plan = store.add_directory_to_base_data(folder, "lulc/toy", manifest_path, **kwargs)
    assert plan["actions"] == {"lulc/toy/lulc_toy_2020.tif": "make POG in place"} and len(plan["warnings"]) == 1 and "no legend" in plan["warnings"][0]  # the legend and script aren't data
    missing = store.add_directory_to_base_data(folder, "lulc/toy", manifest_path, legend="absent_base_data_legend.csv", **kwargs)
    assert len(missing["problems"]) == 1 and "its legend can't be used" in missing["problems"][0]
    result = store.add_directory_to_base_data(folder, "lulc/toy", manifest_path, legend="lulc_toy_base_data_legend.csv", dry_run=False, **kwargs)
    assert result["warnings"] == [] and not os.path.exists(os.path.join(folder, "absent"))
    pog = os.path.join(folder, "lulc_toy_2020.tif")
    ds = gdal.Open(pog)
    assert hb.is_path_pog(pog) and ds.GetRasterBand(1).GetColorTable().GetColorEntry(1) == (255, 255, 100, 255)
    ds = None
    assert store._read_manifest(manifest_path)["legend"].tolist() == ["lulc_toy_base_data_legend.csv"]
    readme = open(os.path.join(folder, "readme.md"), encoding="utf-8").read()
    assert readme.startswith("# lulc/toy\n\nA toy land cover map. It has three classes.\n") and "## Metadata" in readme and "`lulc_toy_2020.tif`" in readme
    assert "| 1 | `cropland` | Cropland, rainfed | `#ffff64` | 255, 255, 100 | Herbaceous crops \\| rainfed |" in readme
    assert "```text\n# QGIS Generated Color Map Export File\nINTERPOLATION:EXACT\n0,0,0,0,255,No data\n" in readme and "## Processing steps" in readme and "\n2. listed" in readme
    assert readme.rstrip().endswith("Part of the TEEMs base data, https://data.teemlabs.org.*") and "This file is generated" not in readme.split("## Metadata")[0]  # the note on how it was made comes last
    again = store.add_directory_to_base_data(folder, "lulc/toy", manifest_path, legend="lulc_toy_base_data_legend.csv", **kwargs)
    assert set(again["actions"].values()) == {"already there"} and again["warnings"] == [] and again["problems"] == []

@needs_quarto
def test_writing_the_readme_writes_its_page(categorical, site, monkeypatch):
    folder, base_data_dir, manifest_path = categorical
    monkeypatch.setattr(store, "SITE_DIR", site)
    store.add_directory_to_base_data(folder, "lulc/toy", manifest_path, legend="lulc_toy_base_data_legend.csv", dry_run=False, base_data_dir=base_data_dir,
                                     variable_class="categorical", client=FakeR2(), **METADATA)
    assert "A toy land cover map." in open(os.path.join(folder, "readme.html"), encoding="utf-8").read()

@needs_quarto
def test_the_readme_is_rendered_as_a_page_beside_it(categorical, site):
    folder, base_data_dir, manifest_path = categorical
    kwargs = dict(base_data_dir=base_data_dir, variable_class="categorical", client=FakeR2(), **METADATA)
    store.add_directory_to_base_data(folder, "lulc/toy", manifest_path, legend="lulc_toy_base_data_legend.csv", dry_run=False, **kwargs)
    with open(os.path.join(site, "_folder_page.qmd"), "a", encoding="utf-8") as f:
        f.write('\n```{=html}\n<a class="brand" href="/">Base Data</a>\n```\n')
    assert store.write_base_data_readme_html(site, manifest_paths=[manifest_path]) == [os.path.join(folder, "readme.html")]
    page = open(os.path.join(folder, "readme.html"), encoding="utf-8").read()
    assert "lulc/toy · TEEMs Base Data" in page and "A toy land cover map." in page and "Processing steps" in page
    assert "body { color: black; }" in page and 'href="https://data.teemlabs.org/"' in page and 'href="/"' not in page  # one file, readable from disk
    assert "background:#ffff64" in page  # a class's colour as a swatch
    again = store.add_directory_to_base_data(folder, "lulc/toy", manifest_path, legend="lulc_toy_base_data_legend.csv", **kwargs)
    assert set(again["actions"].values()) == {"already there"} and again["problems"] == []  # the page isn't data

def test_a_manifest_without_the_legend_column_still_reads(manifest):
    df = pd.read_csv(manifest[0], encoding="utf-8-sig", dtype=str, keep_default_na=False).drop(columns=["legend", "color_ramp"])
    df.to_csv(manifest[0], index=False, encoding="utf-8-sig")
    assert store._read_manifest(manifest[0])["legend"].tolist() == [""] * len(df)
    assert "## Metadata" in open(store.write_base_data_readme(manifest[0]), encoding="utf-8").read()  # and a readme needs neither a legend nor a script

@needs_quarto
def test_a_folder_page_shows_its_legend(categorical, site):
    folder, base_data_dir, manifest_path = categorical
    store.add_directory_to_base_data(folder, "lulc/toy", manifest_path, legend="lulc_toy_base_data_legend.csv", base_data_dir=base_data_dir, variable_class="categorical",
                                     dry_run=False, client=FakeR2(), **METADATA)
    r2 = FakeR2()
    store.publish_base_data_from_manifests(base_data_dir=base_data_dir, note="First.", dry_run=False, client=r2, site_dir=site)
    page = r2.body("lulc/toy/index.html").decode("utf-8")
    assert "Legend</h2>" in page and "background:#ffff64" in page and "Cropland, rainfed" in page and "1,255,255,100,255,Cropland; rainfed" in page
    assert page.index("Metadata</h2>") < page.index("Legend</h2>") < page.index("Processing steps</h2>")

def test_set_legend_names_it_on_the_categorical_rows_already_listed_and_touches_no_raster(categorical):
    folder, base_data_dir, manifest_path = categorical
    store.add_directory_to_base_data(folder, "lulc/toy", manifest_path, base_data_dir=base_data_dir, variable_class="categorical", dry_run=False, client=FakeR2(), **METADATA)
    pog = os.path.join(folder, "lulc_toy_2020.tif")
    before = read(pog)
    assert store._read_manifest(manifest_path)["legend"].tolist() == [""]
    assert store.set_base_data_legend(manifest_path, "lulc_toy_base_data_legend.csv", include=["*_1999.tif"]) == []
    assert store.set_base_data_legend(manifest_path, "lulc_toy_base_data_legend.csv") == ["lulc/toy/lulc_toy_2020.tif"]
    assert store._read_manifest(manifest_path)["legend"].tolist() == ["lulc_toy_base_data_legend.csv"] and read(pog) == before
    assert "## Legend: lulc_toy_base_data_legend.csv" in open(os.path.join(folder, "readme.md"), encoding="utf-8").read()
    assert store.set_base_data_legend(manifest_path, "lulc_toy_base_data_legend.csv") == []  # a rerun changes nothing
    with pytest.raises(OSError):
        store.set_base_data_legend(manifest_path, "absent_base_data_legend.csv")

def test_a_proportion_ramp_is_transparent_at_zero_faint_just_above_and_strong_at_one():
    assert store.read_color_ramp("proportion #006400") == ("proportion", [(0, 100, 0)], [])
    stops = store.get_color_ramp_stops("proportion #006400", minimum=0.2, maximum=0.4)  # the raster's own range is not the ramp's
    assert [(value, alpha) for value, _, alpha in stops] == [(0.0, 0), (1e-6, 255), (1.0, 255)]
    assert stops[1][1] == (224, 236, 224) and stops[2][1] == (0, 100, 0)  # faint but not white, then the colour itself
    assert store.get_qgis_color_ramp("proportion #006400") == ("# QGIS Generated Color Map Export File\nINTERPOLATION:INTERPOLATED\n0,224,236,224,0,0\n"
                                                              "1e-06,224,236,224,255,1e-06\n1,0,100,0,255,1\n")

def test_a_divergent_ramp_is_symmetric_about_a_transparent_zero():
    stops = store.get_color_ramp_stops("divergent #b2182b #2166ac", minimum=-2.0, maximum=8.0)
    assert [value for value, _, _ in stops] == [-8.0, -8e-6, 0.0, 8e-6, 8.0]  # the larger extreme, both ways
    assert [alpha for _, _, alpha in stops] == [255, 255, 0, 255, 255] and stops[0][1] == (178, 24, 43) and stops[4][1] == (33, 102, 172)
    assert [value for value, _, _ in store.get_color_ramp_stops("divergent #b2182b #2166ac", minimum=-5, maximum=3)] == pytest.approx([-5.0, -5e-6, 0.0, 5e-6, 5.0])
    assert "plus and minus 8" in store.describe_color_ramp("divergent #b2182b #2166ac", -2, 8) and "transparent at exactly 0" in store.describe_color_ramp("proportion #006400")
    with pytest.raises(ValueError, match="needs the raster's minimum and maximum"):
        store.get_color_ramp_stops("divergent #b2182b #2166ac")

@pytest.mark.parametrize("color_ramp", ["proportion", "proportion green", "divergent #b2182b", "rainbow #000000", "proportion #006400 #000000", "", "amount #08306b 5",
                                        "amount #08306b x y", "measure jet 0 1", "measure #440154 0 1", "proportion #006400 0 1"])
def test_color_ramp_refuses(color_ramp):
    with pytest.raises(ValueError, match="is none of 'proportion"):
        store.read_color_ramp(color_ramp)

def test_add_directory_records_a_colour_ramp_and_the_readme_gives_it(incoming):
    source_dir, base_data_dir, manifest_path = incoming
    overrides = {"sub/*": {"variable_class": "intensive", "units": "proportion", "description": "Cropland share."}}
    plan = store.add_directory_to_base_data(source_dir, "crops", manifest_path, base_data_dir=base_data_dir, overrides=overrides, client=FakeR2(), **METADATA)
    assert len(plan["warnings"]) == 2 and "sub/cropland_900sec.tif: a continuous raster with no colour ramp" in plan["warnings"][1]
    overrides["sub/*"]["color_ramp"] = "proportion #ffff64"
    bad = store.add_directory_to_base_data(source_dir, "crops", manifest_path, base_data_dir=base_data_dir, overrides={"sub/*": dict(overrides["sub/*"], color_ramp="yellow")}, client=FakeR2(), **METADATA)
    assert any("color_ramp 'yellow' is none of" in problem for problem in bad["problems"])
    overrides["area_*"] = {"color_ramp": "amount #08306b"}  # its numbers come from the raster when it is listed
    result = store.add_directory_to_base_data(source_dir, "crops", manifest_path, base_data_dir=base_data_dir, overrides=overrides, dry_run=False, client=FakeR2(), **METADATA)
    assert result["warnings"] == []
    ramps = store._read_manifest(manifest_path).set_index("ref_path")["color_ramp"].to_dict()
    assert ramps["crops/sub/cropland_900sec.tif"] == "proportion #ffff64" and ramps["crops/table.csv"] == ""
    assert ramps["crops/area_324000sec.tif"] == "amount #08306b"  # eight cells too alike to give two numbers: kept as given, with a warning in the log
    readme = open(os.path.join(os.path.dirname(manifest_path), "readme.md"), encoding="utf-8").read()
    assert "## Colour ramp: amount #08306b" in readme and "whose range has not been taken from the raster yet" in readme
    assert "## Colour ramp: proportion #ffff64" in readme and "INTERPOLATION:INTERPOLATED\n0,255,255,236,0,0" in readme
    assert store.get_raster_range(os.path.join(base_data_dir, "crops", "sub", "cropland_900sec.tif")) == (0.5, 0.5)

def test_an_amount_is_transparent_at_zero_and_split_at_its_median_and_a_measure_is_opaque_throughout():
    stops = store.get_color_ramp_stops("amount #08306b 30 800")
    assert [value for value, _, _ in stops] == pytest.approx([0.0, 8e-4, 30.0, 800.0]) and [alpha for _, _, alpha in stops] == [0, 255, 255, 255]
    assert stops[3][1] == (8, 48, 107) and stops[1][1][2] > stops[2][1][2] > stops[3][1][2]  # faint, halfway, strong
    assert store.get_color_ramp_stops("amount #08306b 1e-9 800")[1][0] == pytest.approx(5e-10)  # the faint stop stays below a tiny median
    measure = store.get_color_ramp_stops("measure viridis -50 3000")
    assert [value for value, _, _ in measure] == pytest.approx([-50, 712.5, 1475, 2237.5, 3000]) and {alpha for _, _, alpha in measure} == {255}
    assert measure[0][1] == (68, 1, 84) and measure[-1][1] == (253, 231, 37)
    assert "opaque throughout, zero included" in store.describe_color_ramp("measure viridis -50 3000") and "98th percentile" in store.describe_color_ramp("amount #08306b 30 800")
    with pytest.raises(ValueError, match="has no numbers yet"):
        store.get_color_ramp_stops("amount #08306b")
    with pytest.raises(ValueError, match="must rise"):
        store.read_color_ramp("measure viridis 10 5")

def test_quantiles_leave_out_nodata_and_zeros_and_complete_a_ramp(tmp_path):
    from osgeo import gdal
    import numpy as np
    path = str(tmp_path / "skewed.tif")
    values = np.zeros((600, 1100), dtype=np.float32)
    values[:100, :100] = np.arange(1, 10001, dtype=np.float32).reshape(100, 100)
    values[599, 1099] = -9999
    ds = gdal.GetDriverByName("GTiff").Create(path, 1100, 600, 1, gdal.GDT_Float32)
    ds.GetRasterBand(1).SetNoDataValue(-9999)
    ds.GetRasterBand(1).WriteArray(values)
    ds = None
    assert store.get_raster_quantiles(path, [50, 98], exclude_zero=True) == pytest.approx([5000.5, 9800.02])
    assert store.get_raster_quantiles(path, [0, 100]) == [0.0, 10000.0]  # nodata is never a value
    assert store.complete_color_ramp("amount #08306b", path) == "amount #08306b 5000 9800"
    with pytest.raises(ValueError, match="gives no range"):  # nearly every cell is 0, so the 2nd and 98th percentiles are both 0
        store.complete_color_ramp("measure viridis", path)
    assert store.complete_color_ramp("amount #08306b 1 2", path) == "amount #08306b 1 2" and store.complete_color_ramp("proportion #006400", path) == "proportion #006400"

def test_set_color_ramp_names_it_on_the_continuous_rows_already_listed_and_touches_no_raster(manifest):
    manifest_path, base_data_dir = manifest
    rasters = {ref: read(os.path.join(base_data_dir, *ref.split("/"))) for ref in REFS}
    changed = store.set_base_data_color_ramp(manifest_path, "measure cividis 0 100", include=["*_324000sec.tif"], base_data_dir=base_data_dir)
    assert changed == {REFS[0]: "measure cividis 0 100"}
    assert store._read_manifest(manifest_path).set_index("ref_path")["color_ramp"].to_dict()[REFS[1]] == ""
    assert store.set_base_data_color_ramp(manifest_path, "measure cividis 0 100", include=["*_324000sec.tif"], base_data_dir=base_data_dir) == {}  # a rerun changes nothing
    assert {ref: read(os.path.join(base_data_dir, *ref.split("/"))) for ref in REFS} == rasters
    assert "## Colour ramp: measure cividis 0 100" in open(os.path.join(os.path.dirname(manifest_path), "readme.md"), encoding="utf-8").read()
    with pytest.raises(ValueError, match="is none of"):
        store.set_base_data_color_ramp(manifest_path, "rainbow", base_data_dir=base_data_dir)
