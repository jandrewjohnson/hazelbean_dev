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
    """A globe-covering tile set of subpogs holding random classes 1..3 (categorical), counts 0..9 (extensive) or proportions (intensive); returns the VRT path."""
    res = hb.pyramid_compatible_resolutions[ARCSECONDS]
    cells = int(round(TILE_DEGREES / res))
    rng = np.random.default_rng(seed)
    tile_paths = []
    for lat in range(90, -90, -TILE_DEGREES):
        for lon in range(-180, 180, TILE_DEGREES):
            bb = [lon, lat - TILE_DEGREES, lon + TILE_DEGREES, lat]
            raw_path = os.path.join(folder, hb.get_tile_filename_from_bb(stem + "_raw", ARCSECONDS, bb))
            ds = gdal.GetDriverByName("GTiff").Create(raw_path, cells, cells, 1, gdal.GDT_Float32 if variable_class == "intensive" else gdal.GDT_Byte)
            ds.SetGeoTransform((bb[0], res, 0, bb[3], 0, -res))
            ds.SetProjection(hb.wgs_84_wkt)
            if variable_class == "intensive":
                ds.GetRasterBand(1).WriteArray(rng.random((cells, cells)).astype(np.float32))
            else:
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

    def test_intensive_matches_make_path_pog(self):
        folder = hb.temporary_dir(dir_name="tileset_intensive", remove_at_exit=True)
        vrt_path = write_tileset(folder, "shares", "intensive")
        fast_path = os.path.join(folder, "shares_fast.tif")
        slow_path = os.path.join(folder, "shares_slow.tif")
        hb.write_pog_from_pog_tileset(vrt_path, fast_path, intermediate_dir=folder)
        hb.make_path_pog(vrt_path, output_raster_path=slow_path, output_arcseconds=ARCSECONDS, variable_class="intensive", intermediate_dir=folder)
        assert hb.is_path_pog(fast_path, full_check=True) and hb.is_path_pog_overview_conformant(fast_path, verbose=True)
        assert hb.get_pog_metadata(fast_path) == hb.get_pog_metadata(slow_path)
        base, levels, stats, _ = read_levels(fast_path)
        slow_base, slow_levels, slow_stats, _ = read_levels(slow_path)
        assert np.array_equal(base, slow_base) and len(levels) == len(slow_levels)
        for level, slow_level in zip(levels, slow_levels):  # the area-weighted means, to float32 storage
            assert np.allclose(level, slow_level, rtol=1e-5, atol=1e-6)
        for key, value in slow_stats.items():
            assert stats[key] == pytest.approx(value, rel=1e-6), key

    def test_tiles_outside_the_extent_may_be_absent_and_are_zero(self):
        folder = hb.temporary_dir(dir_name="tileset_extent", remove_at_exit=True)
        vrt_path = write_tileset(folder, "counts", "extensive")
        ds = gdal.Open(vrt_path); tile_paths = ds.GetFileList()[1:]; ds = None
        kept = [i for i in tile_paths if hb.get_tile_bb_from_corner_string(*hb.parse_tile_filename(i)[2:4])[3] <= 30]  # drop the northern row
        res = hb.pyramid_compatible_resolutions[ARCSECONDS]
        gdal.BuildVRT(vrt_path, kept, options=gdal.BuildVRTOptions(outputBounds=(-180, -90, 180, 90), xRes=res, yRes=res, VRTNodata="None")).FlushCache()
        assert len(kept) == 12 and hb.is_path_pog_tileset(vrt_path)  # a partial set is still a tile set
        fast_path = os.path.join(folder, "counts_fast.tif")
        with pytest.raises(ValueError, match="needed to cover"):
            hb.write_pog_from_pog_tileset(vrt_path, fast_path, intermediate_dir=folder, extent_bb=[-180, -90, 180, 31])
        hb.write_pog_from_pog_tileset(vrt_path, fast_path, intermediate_dir=folder, extent_bb=[-180, -90, 180, 30])
        slow_path = os.path.join(folder, "counts_slow.tif")
        hb.make_path_pog(vrt_path, output_raster_path=slow_path, output_arcseconds=ARCSECONDS, variable_class="extensive", intermediate_dir=folder)
        assert hb.is_path_pog(fast_path, full_check=True) and hb.is_path_pog_overview_conformant(fast_path)
        base, levels, stats, _ = read_levels(fast_path)
        slow_base, slow_levels, slow_stats, _ = read_levels(slow_path)
        assert np.array_equal(base, slow_base) and not base[:720].any()
        for level, slow_level in zip(levels, slow_levels):
            assert np.array_equal(level, slow_level)
        for key, value in slow_stats.items():
            assert stats[key] == pytest.approx(value, rel=1e-9), key


def write_source(path, bb, cell=0.07, seed=1):
    """A float raster of smooth values over bb on a grid that is not the lattice's."""
    cols, rows = int(round((bb[2] - bb[0]) / cell)), int(round((bb[3] - bb[1]) / cell))
    y, x = np.mgrid[0:rows, 0:cols]
    ds = gdal.GetDriverByName("GTiff").Create(path, cols, rows, 1, gdal.GDT_Float32)
    ds.SetGeoTransform((bb[0], cell, 0, bb[3], 0, -cell))
    ds.SetProjection(hb.wgs_84_wkt)
    ds.GetRasterBand(1).WriteArray((0.5 + 0.5 * np.sin(x / 37.0) * np.cos(y / 23.0)).astype(np.float32))
    ds = None
    return path


@pytest.mark.unit
class TestMakePathsPogTiles:
    def test_tiles_from_overlapping_pieces_join_as_the_window_of_one_resample(self):
        folder = hb.temporary_dir(dir_name="tiles_from_pieces", remove_at_exit=True)
        source_path = write_source(os.path.join(folder, "source.tif"), [-70.03, -40.01, 70.04, 40.02])
        tile_bbs = hb.list_tile_bbs_for_bb([-60, -30, 60, 30], TILE_DEGREES)
        assert tile_bbs == [[-60, -30, 0, 30], [0, -30, 60, 30]]
        piece_paths = []
        for c, bb in enumerate(tile_bbs):  # each tile's own piece of the source, with a margin of two source cells
            piece_paths.append(os.path.join(folder, f"piece_{c}.tif"))
            gdal.Translate(piece_paths[-1], source_path, projWin=[bb[0] - 0.2, bb[3] + 0.2, bb[2] + 0.2, bb[1] - 0.2])
        tile_dir = os.path.join(folder, "subpogs", f"shares_{ARCSECONDS}sec_{TILE_DEGREES}deg")
        tile_paths = [os.path.join(tile_dir, hb.get_tile_filename_from_bb("shares", ARCSECONDS, bb)) for bb in tile_bbs]
        assert hb.make_paths_pog_tiles(piece_paths, tile_paths, num_workers=2, variable_class="intensive", intermediate_dir=folder) == tile_paths
        whole_path = os.path.join(folder, "whole.tif")  # the same two boxes resampled from the uncut source in one go
        hb.make_path_pog(source_path, output_raster_path=whole_path, output_arcseconds=ARCSECONDS, variable_class="intensive", output_bb=[-60, -30, 60, 30], intermediate_dir=folder)
        whole = gdal.Open(whole_path).ReadAsArray()
        assert whole.shape == (720, 1440)
        for c, tile_path in enumerate(tile_paths):
            assert hb.is_path_subpog(tile_path, full_check=True) and not os.path.exists(os.path.splitext(tile_path)[0] + "_building.tif")
            tile = gdal.Open(tile_path).ReadAsArray()
            assert tile.shape == (720, 720) and np.allclose(tile, whole[:, 720 * c: 720 * (c + 1)], atol=1e-5)
        # The set so far, indexed from the dataset folder as the global raster: absent tiles are zero.
        vrt_path = hb.build_pog_tileset_vrt(tile_dir, os.path.join(folder, "shares_partial.vrt"))
        assert hb.is_path_pog_tileset(vrt_path, verbose=True) and 'relativeToVRT="1"' in open(vrt_path).read()
        ds = gdal.Open(vrt_path)
        assert (ds.RasterXSize, ds.RasterYSize) == (4320, 2160) and not ds.ReadAsArray(0, 0, 4320, 720).any()
        assert np.array_equal(ds.ReadAsArray(1440, 720, 1440, 720), np.hstack([gdal.Open(t).ReadAsArray() for t in tile_paths]))
        # A tile that exists is kept.
        stamp = os.path.getmtime(tile_paths[0])
        hb.make_paths_pog_tiles(piece_paths, tile_paths, num_workers=1, variable_class="intensive")
        assert os.path.getmtime(tile_paths[0]) == stamp

    def test_output_bb_must_be_aligned(self):
        folder = hb.temporary_dir(dir_name="tiles_unaligned", remove_at_exit=True)
        source_path = write_source(os.path.join(folder, "source.tif"), [-10, -10, 10, 10])
        with pytest.raises(ValueError, match="not aligned"):
            hb.make_path_pog(source_path, output_raster_path=os.path.join(folder, "out.tif"), output_arcseconds=ARCSECONDS, variable_class="intensive", output_bb=[-5.01, -5, 5, 5])
