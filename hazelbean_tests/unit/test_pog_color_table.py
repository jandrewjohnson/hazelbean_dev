"""hb.make_path_pog's color_table and intermediate_dir arguments, and the color-table header helpers."""
import glob
import os

import numpy as np
import pytest
from osgeo import gdal

import hazelbean as hb

COLORS = {10: (255, 255, 100), 210: (0, 70, 200)}


def write_global_byte_raster(path, arcseconds=36000):
    """A global Byte raster at arcseconds (36000 = 10 degrees: 36 x 18 cells) of class 10 north and 210 south, no nodata."""
    res = hb.pyramid_compatible_resolutions[arcseconds]
    cols, rows = int(round(360 / res)), int(round(180 / res))
    ds = gdal.GetDriverByName("GTiff").Create(path, cols, rows, 1, gdal.GDT_Byte)
    ds.SetGeoTransform((-180, res, 0, 90, 0, -res))
    ds.SetProjection(hb.wgs_84_wkt)
    array = np.full((rows, cols), 210, dtype=np.uint8)
    array[: rows // 2] = 10
    ds.GetRasterBand(1).WriteArray(array)
    ds = None
    return array


def color_entries(path):
    ds = gdal.Open(path); band = ds.GetRasterBand(1)  # the dataset must outlive the band
    color_table = band.GetRasterColorTable()
    return gdal.GetColorInterpretationName(band.GetColorInterpretation()), None if color_table is None else {v: color_table.GetColorEntry(v)[:3] for v in COLORS}


@pytest.mark.unit
class TestPogColorTable:
    def test_make_path_pog_writes_the_palette(self):
        input_path = hb.temp(".tif", "palette_input", remove_at_exit=True)
        output_path = hb.temp(".tif", "palette_pog", remove_at_exit=True, tag_along_file_extensions=[".aux.xml"])
        array = write_global_byte_raster(input_path)
        hb.make_path_pog(input_path, output_raster_path=output_path, output_arcseconds=36000, output_data_type=1, variable_class="categorical", color_table=COLORS)
        assert hb.is_path_pog(output_path, full_check=True)
        assert color_entries(output_path) == ("Palette", COLORS)
        ds = gdal.Open(output_path); band = ds.GetRasterBand(1)
        assert np.array_equal(band.ReadAsArray(), array)  # a palette changes how the values are drawn, not the values

    def test_set_color_table_in_raster_header(self):
        path = hb.temp(".tif", "palette_header", remove_at_exit=True)
        array = write_global_byte_raster(path)
        assert color_entries(path)[1] is None
        hb.set_color_table_in_raster_header(path, COLORS)
        assert color_entries(path) == ("Palette", COLORS)
        ds = gdal.Open(path); band = ds.GetRasterBand(1)
        assert np.array_equal(band.ReadAsArray(), array)

    def test_intermediate_dir_holds_the_steps(self):
        input_path = hb.temp(".tif", "steps_input", remove_at_exit=True)
        output_path = hb.temp(".tif", "steps_pog", remove_at_exit=True, tag_along_file_extensions=[".aux.xml"])
        intermediate_dir = hb.temporary_dir(dir_name="steps_intermediate", remove_at_exit=True)
        write_global_byte_raster(input_path)
        hb.make_path_pog(input_path, output_raster_path=output_path, output_arcseconds=36000, output_data_type=1, variable_class="categorical",
                         intermediate_dir=intermediate_dir, remove_intermediate_files=False)
        steps = sorted(os.path.basename(path) for path in glob.glob(os.path.join(intermediate_dir, "*.tif")))
        assert any("_copy_" in step for step in steps) and any("_nodata_" in step for step in steps), steps
        assert hb.is_path_pog(output_path, full_check=True)
