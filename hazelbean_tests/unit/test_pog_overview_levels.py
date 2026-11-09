"""Every overview level of a POG is written: GTiff's BuildOverviews leaves the smallest levels nodata, hazelbean regenerates them in cascade."""
import os

import numpy as np
import pytest
from osgeo import gdal

import hazelbean as hb


def write_classes(path, bb, arcseconds, seed=0):
    res = hb.pyramid_compatible_resolutions[arcseconds]
    cols, rows = int(round((bb[2] - bb[0]) / res)), int(round((bb[3] - bb[1]) / res))
    ds = gdal.GetDriverByName("GTiff").Create(path, cols, rows, 1, gdal.GDT_Byte)
    ds.SetGeoTransform((bb[0], res, 0, bb[3], 0, -res))
    ds.SetProjection(hb.wgs_84_wkt)
    ds.GetRasterBand(1).WriteArray(np.random.default_rng(seed).integers(1, 4, (rows, cols)).astype(np.uint8))
    ds = None


def levels_holding(path, value):
    ds = gdal.Open(path); band = ds.GetRasterBand(1)  # the dataset must outlive the band
    return [(band.GetOverview(i).XSize, band.GetOverview(i).YSize) for i in range(band.GetOverviewCount()) if (band.GetOverview(i).ReadAsArray() == value).any()]


@pytest.mark.unit
class TestPogOverviewLevels:
    def test_subpog_top_levels_are_written(self):
        """A 60-degree tile at 300 arcseconds (720 cells, levels up to factor 360) once came out with its last three levels all 255."""
        folder = hb.temporary_dir(dir_name="overview_levels", remove_at_exit=True)
        input_path, output_path = os.path.join(folder, "classes_input.tif"), os.path.join(folder, "classes_subpog.tif")
        write_classes(input_path, [0, 0, 60, 60], 300)
        hb.make_path_pog(input_path, output_raster_path=output_path, output_arcseconds=300, variable_class="categorical", expand_to_global_extent=False)
        assert hb.is_path_subpog(output_path, full_check=True)
        assert levels_holding(output_path, 255) == []

    def test_global_pog_top_levels_are_written(self):
        """A global 300-arcsecond POG (4320 x 2160, levels down to 2 x 1) once came out with its 4 x 2 and 2 x 1 levels all 255."""
        folder = hb.temporary_dir(dir_name="overview_levels_global", remove_at_exit=True)
        input_path, output_path = os.path.join(folder, "classes_input.tif"), os.path.join(folder, "classes_pog.tif")
        write_classes(input_path, [-180, -90, 180, 90], 300)
        hb.make_path_pog(input_path, output_raster_path=output_path, output_arcseconds=300, variable_class="categorical")
        assert hb.is_path_pog(output_path, full_check=True)
        assert levels_holding(output_path, 255) == []
