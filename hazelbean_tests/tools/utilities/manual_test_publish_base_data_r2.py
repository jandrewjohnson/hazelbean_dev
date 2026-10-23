"""Manual check of base data publishing against real Cloudflare R2, using a throwaway bucket. Never collected by pytest.

The unit tests use an in-memory stand-in for R2; this runs the same code against the real service, to confirm what the
stand-in can't: R2's conditional writes through boto3, boto3's upload checksums, and multipart upload of a large file.

Before running: create TEST_BUCKET (empty) in the Cloudflare dashboard, give the curator token Object Read & Write on it
and on the real bucket, and put HB_R2_ACCOUNT_ID, HB_R2_ACCESS_KEY_ID and HB_R2_SECRET_ACCESS_KEY in machine.env.
Step 1 only READS the real bucket; every write goes to TEST_BUCKET. Afterwards, empty and delete TEST_BUCKET.
"""
import hashlib
import os

import hazelbean as hb
from hazelbean import base_data_processing, cloud_utils

TEST_BUCKET = "teems-public-data-test"
pyramids_dir = os.path.join(os.path.expanduser("~"), "Files", "base_data", "pyramids")
manifest_path = os.path.join(pyramids_dir, "pyramids_base_data_manifest.csv")
metadata = dict(license="CC-BY-4.0", units="ha", data_source="Computed from the WGS84 ellipsoid (hb.ha_per_cell_rows).",
                description="Throwaway test publication.", code="hazelbean_tests/tools/utilities/manual_test_publish_base_data_r2.py")
small = ["ha_per_cell_648000sec.tif", "ha_per_cell_324000sec.tif"]

client = cloud_utils.get_r2_client()
assert client is not None, "No R2 credentials in machine.env (HB_R2_ACCOUNT_ID, HB_R2_ACCESS_KEY_ID, HB_R2_SECRET_ACCESS_KEY)."

# 1. A credentialed dry run against the REAL bucket: proves the endpoint and token work and can read. Writes nothing.
plan = hb.publish_base_data(os.path.join(pyramids_dir, small[0]), "pyramids/" + small[0], "Dry run.", dry_run=True, client=client, **metadata)
assert plan["problems"] == [], plan["problems"]
print(f"1. OK  real bucket {base_data_processing.BUCKET} is readable; its latest release is {plan['parent']}.")

# From here on, every read and write goes to the throwaway bucket.
base_data_processing.BUCKET = TEST_BUCKET
assert client.list_objects_v2(Bucket=TEST_BUCKET).get("KeyCount", 0) == 0, f"Start from an empty {TEST_BUCKET}."

# 2. The first release: two tiny files. Exercises uploads, If-None-Match claims, and the first write of latest.json.
first = hb.publish_base_data([os.path.join(pyramids_dir, n) for n in small], ["pyramids/" + n for n in small], "Test release 1.", client=client, **metadata)
assert cloud_utils.read_r2_json(client, TEST_BUCKET, base_data_processing.LATEST_KEY)[0] == {"release": first["release"]}
entry = cloud_utils.read_r2_json(client, TEST_BUCKET, f"_catalogue/pyramids/{small[0]}/{first['release']}.json")[0]
assert entry["provenance"]["promoted_from"] is None
uploaded = client.get_object(Bucket=TEST_BUCKET, Key="pyramids/" + small[0])["Body"].read()
assert hashlib.sha256(uploaded).hexdigest() == entry["files"][0]["sha256"], "The uploaded bytes differ from the local file."
n_objects = client.list_objects_v2(Bucket=TEST_BUCKET)["KeyCount"]
print(f"2. OK  release {first['release']} published, {n_objects} objects; downloaded bytes match the local file's sha256.")

# 3. Publishing identical bytes again is refused, and writes nothing.
try:
    hb.publish_base_data(os.path.join(pyramids_dir, small[0]), "pyramids/" + small[0], "Again.", client=client, **metadata)
    raise AssertionError("An identical publication was accepted.")
except ValueError as e:
    assert "identical to the current version" in str(e), e
assert client.list_objects_v2(Bucket=TEST_BUCKET)["KeyCount"] == n_objects
print("3. OK  an identical publication is refused and writes nothing.")

# 4. R2 itself enforces the compare-and-swap: a stale If-Match and an If-None-Match on an existing key are both refused with 412.
for conditions in ({"IfMatch": '"00000000000000000000000000000000"'}, {"IfNoneMatch": "*"}):
    try:
        cloud_utils.write_r2_json(client, TEST_BUCKET, base_data_processing.LATEST_KEY, {"release": "must-not-land"}, cache_control="no-cache", **conditions)
        raise AssertionError(f"R2 accepted a conditional write it should have refused: {conditions}")
    except Exception as e:
        if cloud_utils.get_r2_error_status(e) != 412:
            raise
assert cloud_utils.read_r2_json(client, TEST_BUCKET, base_data_processing.LATEST_KEY)[0] == {"release": first["release"]}
print("4. OK  R2 refused both conditional writes with 412, and latest.json is unchanged.")

# 5. A second release on top of the first, with the 261 MB 10-second raster: exercises multipart upload.
large_path = os.path.join(pyramids_dir, "ha_per_cell_10sec.tif")
second = hb.publish_base_data(large_path, "pyramids/ha_per_cell_10sec.tif", "Test release 2.", client=client, **metadata)
assert second["parent"] == first["release"]
large_entry = cloud_utils.read_r2_json(client, TEST_BUCKET, f"_catalogue/pyramids/ha_per_cell_10sec.tif/{second['release']}.json")[0]
head = client.head_object(Bucket=TEST_BUCKET, Key="pyramids/ha_per_cell_10sec.tif")
assert head["ContentLength"] == os.path.getsize(large_path) and head["Metadata"]["sha256"] == large_entry["files"][0]["sha256"]
print(f"5. OK  release {second['release']} (parent {first['release']}) uploaded the 10 s raster; size and recorded sha256 match.")

# 6. The manifest command reads the published state: the three published rows are unchanged, the other 14 new.
result = hb.publish_base_data_from_manifests(manifest_paths=[manifest_path], client=client)
statuses = list(result["statuses"].values())
assert statuses.count("unchanged") == 3 and statuses.count("new") == 14, result["statuses"]
print("6. OK  the manifest dry run sees 3 unchanged and 14 new rows.")

print(f"All checks passed. Now empty and delete {TEST_BUCKET} in the Cloudflare dashboard.")
