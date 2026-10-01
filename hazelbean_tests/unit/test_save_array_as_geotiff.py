"""save_array_as_geotiff takes its nodata from the match raster, and a match that declares none (as an extensive,
intensive or categorical POG may) gives an output that declares none, rather than an error."""
import numpy as np
import pytest
from osgeo import gdal

import hazelbean as hb


def _match(path, ndv):
    ds = gdal.GetDriverByName('GTiff').Create(path, 40, 20, 1, gdal.GDT_Float64)
    ds.SetGeoTransform((0.0, 0.25, 0.0, 10.0, 0.0, -0.25))
    ds.SetProjection(hb.wgs_84_wkt)
    if ndv is not None:
        ds.GetRasterBand(1).SetNoDataValue(ndv)
    ds = None
    return path


@pytest.mark.parametrize('match_ndv', [None, -9999.0])
def test_output_follows_the_match_nodata(tmp_path, match_ndv):
    match = _match(str(tmp_path / 'match.tif'), match_ndv)
    out = str(tmp_path / 'out.tif')
    arr = np.arange(800, dtype=np.float64).reshape(20, 40)
    hb.save_array_as_geotiff(arr, out, match)
    ds = gdal.Open(out)
    assert ds.GetRasterBand(1).GetNoDataValue() == match_ndv
    assert np.array_equal(ds.ReadAsArray(), arr) and ds.GetGeoTransform() == (0.0, 0.25, 0.0, 10.0, 0.0, -0.25)
    ds = None


def test_explicit_ndv_still_wins_and_inf_needs_one(tmp_path):
    match = _match(str(tmp_path / 'match.tif'), None)
    hb.save_array_as_geotiff(np.ones((20, 40)), str(tmp_path / 'a.tif'), match, ndv=-1.0)
    ds = gdal.Open(str(tmp_path / 'a.tif')); assert ds.GetRasterBand(1).GetNoDataValue() == -1.0; ds = None
    with pytest.raises(ValueError):
        hb.save_array_as_geotiff(np.ones((20, 40)), str(tmp_path / 'b.tif'), match, set_inf_to_no_data_value=True)
    with pytest.raises(NameError):  # no match and no ndv: an error, as before (it used to crash on an undefined name)
        hb.save_array_as_geotiff(np.ones((20, 40)), str(tmp_path / 'c.tif'), data_type=7)
