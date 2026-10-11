"""write_vrt_to_raster must produce a valid COG that carries the overviews it was asked for.

Before the fix the COG branch wrote the COG and then reopened it with GA_Update to build
overviews, which GDAL refuses on COG layout, so every call that reached it raised RuntimeError.
A second defect rebound translate_options to a hardcoded list, discarding compress, bigtiff and
the block size the caller passed, and specified OVERVIEWS twice with an invalid second value.
"""
import os
import numpy as np
import pytest
from osgeo import gdal

import hazelbean as hb
from hazelbean import spatial_utils


def _tile(path, value, x_origin, size=512):
    driver = gdal.GetDriverByName('GTiff')
    ds = driver.Create(path, size, size, 1, gdal.GDT_Byte)
    ds.SetGeoTransform([x_origin, 1.0 / size, 0, 1.0, 0, -1.0 / size])
    band = ds.GetRasterBand(1)
    band.WriteArray(np.full((size, size), value, dtype=np.uint8))
    band.SetNoDataValue(255)
    ds = None
    return path


@pytest.fixture
def two_tiles(tmp_path):
    return [_tile(str(tmp_path / 'a.tif'), 3, 0.0), _tile(str(tmp_path / 'b.tif'), 4, 1.0)]


def test_it_writes_a_cog_without_reopening_it_for_update(tmp_path, two_tiles):
    out = str(tmp_path / 'stitched.tif')
    spatial_utils.stitch_rasters_using_vrt(two_tiles, out)
    assert os.path.exists(out)
    # Cheapest possible proof the layout is a real COG: GDAL refuses GA_Update on one.
    gdal.UseExceptions()
    with pytest.raises(RuntimeError, match='C.loud. O.ptimized. G.eoTIFF.'):
        gdal.Open(out, gdal.GA_Update)


def test_the_overviews_are_present_and_built_by_the_requested_method(tmp_path, two_tiles):
    vrt = str(tmp_path / 'in.vrt')
    spatial_utils.create_gdal_vrt(two_tiles, vrt)
    out = str(tmp_path / 'mode.tif')
    spatial_utils.write_vrt_to_raster(vrt, out, overview_resampling_method='mode')
    ds = gdal.Open(out)
    assert ds.GetRasterBand(1).GetOverviewCount() > 0
    # MODE over a block of one class returns that class, so a class code survives downsampling.
    # An averaging method would also return it here, so this asserts only that the overview holds
    # a real class value rather than nodata -- the method name reaching GDAL is what the write
    # itself proves, since GDAL rejects an unknown resampling name outright.
    top = ds.GetRasterBand(1).GetOverview(ds.GetRasterBand(1).GetOverviewCount() - 1).ReadAsArray()
    assert set(np.unique(top)) <= {3, 4, 255}
    assert set(np.unique(top)) & {3, 4}
    ds = None


def test_near_is_translated_to_the_name_gdal_accepts():
    # 'near' is what gdalwarp and this module's own default use; BuildOverviews and the COG
    # driver's RESAMPLING option take NEAREST and reject NEAR.
    assert spatial_utils._gdal_overview_resample_name('near') == 'NEAREST'
    assert spatial_utils._gdal_overview_resample_name('NEAR') == 'NEAREST'
    assert spatial_utils._gdal_overview_resample_name('mode') == 'MODE'


def test_the_callers_creation_options_are_not_discarded(tmp_path, two_tiles):
    vrt = str(tmp_path / 'in.vrt')
    spatial_utils.create_gdal_vrt(two_tiles, vrt)
    out = str(tmp_path / 'lzw.tif')
    spatial_utils.write_vrt_to_raster(vrt, out, compress='lzw', blockxsize=128, blockysize=128)
    ds = gdal.Open(out)
    structure = ds.GetMetadata('IMAGE_STRUCTURE')
    assert structure.get('COMPRESSION') == 'LZW'
    assert ds.GetRasterBand(1).GetBlockSize() == [128, 128]
    ds = None
