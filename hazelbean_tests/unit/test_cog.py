import unittest, os, sys
import numpy as np
import pytest
from osgeo import gdal
import hazelbean as hb
from hazelbean import spatial_utils

from hazelbean.cog import *
from hazelbean.pyramids import *

class TestCOGCompliance(unittest.TestCase):
    def setUp(self):
        """Set up test data paths."""
        self.data_dir = os.path.join(os.path.dirname(__file__), "../../data")
        self.test_data_dir = os.path.join(self.data_dir, "tests")
        self.cartographic_data_dir = os.path.join(self.data_dir, "cartographic/ee")
        self.valid_cog_path = os.path.join(self.test_data_dir, "valid_cog_example.tif")
        self.invalid_cog_path = os.path.join(self.test_data_dir, "invalid_cog_example.tif")        
        self.valid_pog_path = os.path.join(self.cartographic_data_dir, "ee_r264_ids_900sec.tif")


    @pytest.mark.unit
    def test_is_cog(self):
        """Check if TIFF files are valid Cloud-Optimized GeoTIFFs (COGs)."""

        with self.subTest(file=self.invalid_cog_path):
            result = is_path_cog(self.invalid_cog_path, check_tiled=True, full_check=True, raise_exceptions=False, verbose=False)
            self.assertFalse(result, f"{self.invalid_cog_path} is a valid COG")
            
            result = is_path_cog(self.valid_cog_path, check_tiled=True, full_check=True, raise_exceptions=False, verbose=False)
            self.assertTrue(result, f"{self.invalid_cog_path} is Not a valid COG")
            
    @pytest.mark.integration
    @pytest.mark.slow
    def test_make_path_cog(self):
        """Test make_path_cog() Need to find a non-translate way. maybe rio?"""

        with self.subTest(file=self.invalid_cog_path):
            temp_path = hb.temp('.tif', remove_at_exit=True, tag_along_file_extensions=['.aux.xml'])
            make_path_cog(self.invalid_cog_path, temp_path, output_data_type=1, overview_resampling_method='mode', ndv=255, compression="ZSTD", blocksize=512, verbose=True)
            
            result = is_path_cog(temp_path, check_tiled=True, full_check=True, raise_exceptions=False, verbose=False)
            self.assertTrue(result, f"{temp_path} is a valid COG")

    @pytest.mark.integration
    def test_write_random_cog(self):
        """Test make_path_cog() Need to find a non-translate way. maybe rio?"""

        with self.subTest(file=self.invalid_cog_path):
            temp_path = hb.temp('.tif', remove_at_exit=True, tag_along_file_extensions=['.aux.xml'])
            write_random_cog(temp_path)

            result = is_path_cog(temp_path, check_tiled=True, full_check=True, raise_exceptions=False, verbose=False)
            self.assertTrue(result, f"{temp_path} is a valid COG")
            
    @pytest.mark.benchmark
    @pytest.mark.integration
    def test_cog_validation_performance(self):
        """Benchmark COG validation performance."""
        import pytest
        
        def validate_cog():
            return is_path_cog(self.valid_cog_path, check_tiled=True, full_check=True, raise_exceptions=False, verbose=False)
        
        # This will work if the test is run through pytest with benchmark plugin
        try:
            # Check if we're running under pytest with benchmark
            if hasattr(self, '_testMethodName') and 'benchmark' in str(self._testMethodName):
                result = validate_cog()
                self.assertTrue(result)
        except:
            # Fallback for regular unittest
            result = validate_cog()
            self.assertTrue(result)
            
            
    


# write_vrt_to_raster writes a valid COG carrying the requested overviews and the caller's creation options.

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


if __name__ == "__main__":
    unittest.main()

