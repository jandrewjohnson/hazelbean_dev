"""hb.write_pog_from_pog_tileset: the POG of a globe-covering tile set equals make_path_pog's up to the tile edge, in two passes."""
import os

import numpy as np
import pytest
from osgeo import gdal

import hazelbean as hb

ARCSECONDS = 300  # 4320 x 2160 globally; 60-degree tiles of 720 x 720 cells, 18 of them, with overview levels [3, 6, 12, 60, 120, 360]
TILE_DEGREES = 60
COLORS = {1: (255, 255, 100), 2: (0, 70, 200), 3: (0, 100, 0)}


def write_tileset(folder, stem, variable_class, seed=0):
    """A globe-covering tile set of subpogs holding random classes 1..3 (categorical) or counts 0..9 (extensive); returns the VRT path."""
    res = hb.pyramid_compatible_resolutions[ARCSECONDS]
    cells = int(round(TILE_DEGREES / res))
    rng = np.random.default_rng(seed)
    tile_paths = []
    for lat in range(90, -90, -TILE_DEGREES):
        for lon in range(-180, 180, TILE_DEGREES):
            bb = [lon, lat - TILE_DEGREES, lon + TILE_DEGREES, lat]
            raw_path = os.path.join(folder, hb.get_tile_filename_from_bb(stem + "_raw", ARCSECONDS, bb))
            ds = gdal.GetDriverByName("GTiff").Create(raw_path, cells, cells, 1, gdal.GDT_Byte)
            ds.SetGeoTransform((bb[0], res, 0, bb[3], 0, -res))
            ds.SetProjection(hb.wgs_84_wkt)
            ds.GetRasterBand(1).WriteArray(rng.integers(1, 4, (cells, cells)).astype(np.uint8) if variable_class == "categorical" else rng.integers(0, 10, (cells, cells)).astype(np.uint8))
            ds = None
            tile_path = os.path.join(folder, hb.get_tile_filename_from_bb(stem, ARCSECONDS, bb))
            hb.make_path_pog(raw_path, output_raster_path=tile_path, output_arcseconds=ARCSECONDS, variable_class=variable_class, expand_to_global_extent=False)
            os.remove(raw_path)
            tile_paths.append(tile_path)
    vrt_path = os.path.join(folder, stem + ".vrt")
    gdal.BuildVRT(vrt_path, tile_paths, options=gdal.BuildVRTOptions(outputBounds=(-180, -90, 180, 90), xRes=res, yRes=res, VRTNodata="None")).FlushCache()
    assert hb.is_path_pog_tileset(vrt_path, verbose=True)
    return vrt_path


def read_levels(path):
    ds = gdal.Open(path); band = ds.GetRasterBand(1)  # the dataset must outlive the band
    stats = {k: float(v) for k, v in band.GetMetadata().items() if k in ("STATISTICS_MINIMUM", "STATISTICS_MAXIMUM", "STATISTICS_MEAN", "STATISTICS_STDDEV")}
    color_table = band.GetRasterColorTable()  # read while the dataset is open: the table dies with it
    return band.ReadAsArray(), [band.GetOverview(i).ReadAsArray() for i in range(band.GetOverviewCount())], stats, None if color_table is None else {v: color_table.GetColorEntry(v)[:3] for v in COLORS}


@pytest.mark.unit
class TestWritePogFromPogTileset:
    def test_categorical_matches_make_path_pog(self):
        folder = hb.temporary_dir(dir_name="tileset_categorical", remove_at_exit=True)
        vrt_path = write_tileset(folder, "classes", "categorical")
        fast_path = os.path.join(folder, "classes_fast.tif")
        slow_path = os.path.join(folder, "classes_slow.tif")
        hb.write_pog_from_pog_tileset(vrt_path, fast_path, color_table=COLORS, intermediate_dir=folder)
        hb.make_path_pog(vrt_path, output_raster_path=slow_path, output_arcseconds=ARCSECONDS, variable_class="categorical", intermediate_dir=folder)
        assert hb.is_path_pog(fast_path, full_check=True)
        base, levels, stats, colors = read_levels(fast_path)
        slow_base, slow_levels, slow_stats, _ = read_levels(slow_path)
        assert np.array_equal(base, slow_base)
        assert len(levels) == len(slow_levels) == len(hb.pyramid_compatible_overview_levels[float(ARCSECONDS)])
        # The six levels the tiles hold are copied from them exactly...
        ds = gdal.Open(vrt_path); tile_paths = ds.GetFileList()[1:]; ds = None
        for tile_path in tile_paths:
            tile_ds = gdal.Open(tile_path); tile_band = tile_ds.GetRasterBand(1)
            tile_gt = tile_ds.GetGeoTransform()
            for k, factor in enumerate([3, 6, 12, 60, 120, 360]):
                tile_level = tile_band.GetOverview(k).ReadAsArray()
                row, col = int(round((90 - tile_gt[3]) / (tile_gt[1] * factor))), int(round((tile_gt[0] + 180) / (tile_gt[1] * factor)))
                assert np.array_equal(levels[k][row: row + tile_level.shape[0], col: col + tile_level.shape[1]], tile_level), (tile_path, k)
        # ...and the first is the level GDAL computes on the assembled raster, up to how it breaks a tie in the mode: at the
        # chunk boundaries of its pass over the global base it picks the other tied class on a few cells (0.03% here). Those
        # cells carry into the coarser levels, where random classes tie often, so only the first is compared.
        assert (levels[0] != slow_levels[0]).mean() < 1e-3
        for row, col in zip(*np.where(levels[0] != slow_levels[0])):
            block = base[3 * row: 3 * row + 3, 3 * col: 3 * col + 3]
            assert (block == levels[0][row, col]).sum() == (block == slow_levels[0][row, col]).sum()
        for level, slow_level in list(zip(levels, slow_levels))[6:]:  # the aggregated levels: the same shape and classes
            assert level.shape == slow_level.shape and set(np.unique(level)) <= {1, 2, 3}
        for key, value in slow_stats.items():
            assert stats[key] == pytest.approx(value, rel=1e-9), key
        assert colors == COLORS
        assert not os.path.exists(os.path.join(folder, "classes_fast_translate.tif"))

    def test_extensive_sums_are_exact(self):
        folder = hb.temporary_dir(dir_name="tileset_extensive", remove_at_exit=True)
        vrt_path = write_tileset(folder, "counts", "extensive")
        fast_path = os.path.join(folder, "counts_fast.tif")
        hb.write_pog_from_pog_tileset(vrt_path, fast_path, intermediate_dir=folder)
        assert hb.is_path_pog(fast_path, full_check=True)
        base, levels, _, _ = read_levels(fast_path)
        for level in levels:
            assert level.sum() == base.sum()  # every level of an extensive POG sums to the base
        assert hb.is_path_pog_overview_conformant(fast_path)

    def test_refuses_a_set_with_a_gap(self):
        folder = hb.temporary_dir(dir_name="tileset_gap", remove_at_exit=True)
        vrt_path = write_tileset(folder, "classes", "categorical")
        ds = gdal.Open(vrt_path); tile_paths = ds.GetFileList()[1:]; ds = None
        res = hb.pyramid_compatible_resolutions[ARCSECONDS]
        gdal.BuildVRT(vrt_path, tile_paths[1:], options=gdal.BuildVRTOptions(outputBounds=(-180, -90, 180, 90), xRes=res, yRes=res, VRTNodata="None")).FlushCache()
        with pytest.raises(ValueError, match="cover the globe"):
            hb.write_pog_from_pog_tileset(vrt_path, os.path.join(folder, "classes_fast.tif"))
