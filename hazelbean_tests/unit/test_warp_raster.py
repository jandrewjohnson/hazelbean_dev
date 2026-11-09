"""hb.warp_raster_hb (through hb.resample_to_match): the output's nodata comes from the input or the caller, never invented."""
import numpy as np
import pytest
from osgeo import gdal

import hazelbean as hb


def write_byte_raster(path, array, ndv=None):
    """A WGS84 raster of 1-degree cells at the origin holding array, declaring ndv only when given."""
    ds = gdal.GetDriverByName("GTiff").Create(path, array.shape[1], array.shape[0], 1, gdal.GDT_Byte)
    ds.SetGeoTransform((0, 1, 0, array.shape[0], 0, -1))
    ds.SetProjection(hb.wgs_84_wkt)
    ds.GetRasterBand(1).WriteArray(array)
    if ndv is not None:
        ds.GetRasterBand(1).SetNoDataValue(ndv)
    ds = None


@pytest.mark.unit
class TestWarpRasterNodata:
    def test_no_nodata_declared_keeps_every_value(self):
        """A value equal to what GDAL would otherwise be told is nodata (255 for Byte) survives a warp when no raster declares one."""
        input_path = hb.temp(".tif", "warp_input", remove_at_exit=True)
        match_path = hb.temp(".tif", "warp_match", remove_at_exit=True)
        output_path = hb.temp(".tif", "warp_output", remove_at_exit=True, tag_along_file_extensions=[".aux.xml"])
        array = np.full((4, 4), 255, dtype=np.uint8)
        array[0, 0] = 0
        write_byte_raster(input_path, array)
        write_byte_raster(match_path, np.zeros((4, 4), dtype=np.uint8))
        hb.resample_to_match(input_path, match_path, output_path, resample_method="near", output_data_type=1, compress=True, verbose=False)
        ds = gdal.Open(output_path); band = ds.GetRasterBand(1)  # the dataset must outlive the band
        assert band.GetNoDataValue() is None
        assert np.array_equal(band.ReadAsArray(), array)

    def test_declared_nodata_carries_over(self):
        """The input's own nodata is declared on the output and left in place."""
        input_path = hb.temp(".tif", "warp_input", remove_at_exit=True)
        match_path = hb.temp(".tif", "warp_match", remove_at_exit=True)
        output_path = hb.temp(".tif", "warp_output", remove_at_exit=True, tag_along_file_extensions=[".aux.xml"])
        array = np.full((4, 4), 7, dtype=np.uint8)
        array[1, 1] = 255
        write_byte_raster(input_path, array, ndv=255)
        write_byte_raster(match_path, np.zeros((4, 4), dtype=np.uint8))
        hb.resample_to_match(input_path, match_path, output_path, resample_method="near", output_data_type=1, compress=True, verbose=False)
        ds = gdal.Open(output_path); band = ds.GetRasterBand(1)
        assert band.GetNoDataValue() == 255
        assert np.array_equal(band.ReadAsArray(), array)
