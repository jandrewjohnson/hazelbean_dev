"""Subpog tile scheme: corner naming, OGC Tile Matrix Set addressing and compliance, tiling a POG, and the VRT index.

The tile pipeline tests build their own 900-second POG (1440 x 720, a few MB) so they need no base_data.
"""
import glob
import os

import numpy as np
import pytest
from osgeo import gdal

import hazelbean as hb


def test_corner_string_round_trip():
    assert hb.get_tile_corner_string(-130, 40) == '40N_130W'
    assert hb.get_tile_corner_string(10, -5) == '5S_10E'
    assert hb.get_tile_corner_string(-180, -90) == '90S_180W'
    assert hb.parse_tile_corner_string('40N_130W') == (-130, 40)
    assert hb.get_tile_bb_from_corner_string('40N_130W', 10) == [-130, 40, -120, 50]
    assert hb.get_tile_bb_from_corner_string('20N_30E', 30, 60) == [30, 20, 90, 50]  # height then width
    with pytest.raises(ValueError):
        hb.parse_tile_corner_string('N40W130')  # the pre-2026-09-24 form


def test_tile_filename_round_trip():
    """Corner in whole degrees, latitude first, then the HEIGHT and WIDTH of the extent (the paper's Section 4.2.2 and A.6)."""
    name = hb.get_tile_filename('lulc_esa_2020', 10, '40N_130W')
    assert name == 'lulc_esa_2020_10sec_40N_130W_10_10.tif'
    assert hb.parse_tile_filename('/anywhere/' + name) == ('lulc_esa_2020', 10.0, '40N_130W', 10, 10)
    assert hb.get_tile_filename_from_bb('lulc_esa_2020', 10, [30, 20, 90, 50]) == 'lulc_esa_2020_10sec_20N_30E_30_60.tif'  # a subpog, 20N-50N x 30E-90E
    assert hb.parse_tile_filename('lulc_esa_2020_10sec_20N_30E_30_60.tif') == ('lulc_esa_2020', 10.0, '20N_30E', 30, 60)
    assert hb.parse_tile_filename('lulc-esa_1-3sec_40N_130W_1_1.tif') == ('lulc-esa', pytest.approx(1 / 3), '40N_130W', 1, 1)  # fractional rung, hyphenated stem
    with pytest.raises(ValueError):
        hb.get_tile_filename('x', 300, '40N_130W')  # 300 sec is not a tiled resolution
    with pytest.raises(ValueError):
        hb.parse_tile_filename('lulc_esa_2020_10sec.tif')
    with pytest.raises(ValueError):
        hb.get_tile_filename_from_bb('x', 10, [30.5, 20, 90, 50])  # names carry whole degrees


def test_every_corner_addresses_through_the_ogc_tile_matrix():
    """A subpog tile set is addressable through the tile matrix set: corner <-> (tileMatrix, row, col) is a bijection."""
    corners = hb.list_tile_corner_strings(10)
    assert len(corners) == 36 * 18
    assert corners[0] == '80N_180W' and corners[-1] == '90S_170E'  # OGC row order: north to south, west to east
    seen = set()
    for corner in corners:
        matrix_id, row, col = hb.tile_corner_string_to_tile_matrix_index(corner, 10)
        assert matrix_id == '10sec' and 0 <= row < 18 and 0 <= col < 36
        seen.add((row, col))
        assert hb.tile_matrix_index_to_tile_corner_string(10, row, col) == corner
    assert len(seen) == len(corners)
    assert hb.tile_corner_string_to_tile_matrix_index('80N_180W', 10) == ('10sec', 0, 0)


def test_tile_matrix_set_is_valid_ogc_tms_2_0(tmp_path):
    """The compliance test: the published document validates against the OGC TMS 2.0 schema shipped in hazelbean."""
    tms = hb.get_pyramid_tile_matrix_set()
    ids = [m['id'] for m in tms['tileMatrices']]
    assert ids == [f'{s}sec' for s in ('1-9', '3-10', '1-3', '9-10', 1, 2, 3, 9, 10, 15, 30, 90, 150, 180, 300, 360, 600, 900, 1800, 3600, 18000, 36000, 108000, 324000, 648000)]
    assert len(ids) == 25  # sixteen main rungs, nine side rungs
    assert tms['tileMatrices'][-1]['tileWidth'] == 2 and tms['tileMatrices'][-1]['tileHeight'] == 1  # the 2 x 1 top rung
    ten = tms['tileMatrices'][ids.index('10sec')]
    assert (ten['tileWidth'], ten['matrixWidth'], ten['matrixHeight']) == (3600, 36, 18)
    assert tms['tileMatrices'][ids.index('300sec')]['matrixWidth'] == 1  # 300 sec: one global tile
    for m in tms['tileMatrices']:  # every matrix covers the globe exactly
        assert m['tileWidth'] * m['matrixWidth'] * m['cellSize'] == pytest.approx(360)
        assert m['tileHeight'] * m['matrixHeight'] * m['cellSize'] == pytest.approx(180)
    assert hb.validate_tile_matrix_set_json(tms) is True
    path = hb.write_pyramid_tile_matrix_set_json(str(tmp_path / 'tms.json'))
    assert hb.validate_tile_matrix_set_json(path) is True
    bad = dict(tms, tileMatrices=[dict(tms['tileMatrices'][0], tileWidth='oops')])
    with pytest.raises(Exception):
        hb.validate_tile_matrix_set_json(bad)


def test_overview_levels_truncate_to_the_extent():
    assert hb.get_pyramid_overview_levels_for_bb(1, [0, 0, 1, 1]) == [2, 10, 30, 150, 300, 900, 1800, 3600]  # main rungs only, to the 1-degree level
    assert hb.get_pyramid_overview_levels_for_bb(10, [0, 0, 10, 10]) == [3, 15, 30, 90, 180, 360, 1800, 3600]  # up to the 10-degree level
    assert hb.get_pyramid_overview_levels_for_bb(0.9, [0, 0, 1, 1]) == [10, 100, 200, 1000, 2000, 4000]  # side chain 9, 90, 180 s, then 900 s to 1 degree
    assert hb.get_pyramid_overview_levels_for_bb(10, [-180, -90, 180, 90]) == hb.pyramid_compatible_overview_levels[10]


@pytest.fixture
def half_empty_pog(tmp_path):
    """A 900-second categorical Byte POG whose west half was nodata (now the none class, 0)."""
    raw, pog = str(tmp_path / 'raw.tif'), str(tmp_path / 'gradient.tif')
    W, H = 1440, 720
    ds = gdal.GetDriverByName('GTiff').Create(raw, W, H, 1, gdal.GDT_Byte, options=['TILED=YES', 'COMPRESS=DEFLATE'])
    ds.SetGeoTransform(hb.pyramid_compatible_geotransforms[900.0])
    arr = np.full((H, W), 255, dtype=np.uint8)
    arr[:, W // 2:] = (np.arange(W // 2) % 200).astype(np.uint8)
    ds.GetRasterBand(1).WriteArray(arr)
    ds.GetRasterBand(1).SetNoDataValue(255)
    ds = None
    hb.make_path_pog(raw, pog, variable_class='categorical')
    assert hb.is_path_pog(pog, verbose=True)
    return pog


def test_tile_pog_to_tileset_and_vrt(half_empty_pog):
    vrt = hb.tile_pog_to_tileset(half_empty_pog, tile_degrees=90)
    tile_dir = os.path.join(os.path.dirname(half_empty_pog), 'gradient_900sec_90deg')
    tiles = sorted(os.path.basename(t) for t in glob.glob(os.path.join(tile_dir, '*.tif')))
    assert tiles == ['gradient_900sec_0N_0E_90_90.tif', 'gradient_900sec_0N_90E_90_90.tif',
                     'gradient_900sec_90S_0E_90_90.tif', 'gradient_900sec_90S_90E_90_90.tif'], 'only the non-empty east half is written'
    assert all(hb.is_path_subpog(os.path.join(tile_dir, t)) for t in tiles)
    assert not hb.is_path_pog(os.path.join(tile_dir, tiles[0]))
    assert hb.is_path_pog_tileset(vrt)
    xml = open(vrt).read()
    assert 'relativeToVRT="1"' in xml and tile_dir not in xml

    src = gdal.Open(half_empty_pog); vds = gdal.Open(vrt)
    assert vds.GetGeoTransform() == hb.pyramid_compatible_geotransforms[900.0]
    assert np.array_equal(src.ReadAsArray(), vds.ReadAsArray())
    original = src.ReadAsArray(); src = vds = None

    # Sparse tile sets are legitimate: a missing tile reads as zero (a POG carries no nodata), everything else is unchanged.
    os.remove(os.path.join(tile_dir, 'gradient_900sec_0N_90E_90_90.tif'))
    vds = gdal.Open(hb.build_pog_tileset_vrt(tile_dir)); sparse = vds.ReadAsArray(); vds = None
    assert np.all(sparse[0:360, 1080:1440] == 0)
    assert np.array_equal(sparse[360:], original[360:])


def test_tile_pog_refuses_non_pog_and_untiled_resolution(half_empty_pog, tmp_path):
    with pytest.raises(ValueError):
        hb.tile_pog_to_tileset(half_empty_pog)  # 900 sec is not a tiled resolution without an explicit tile_degrees
    with pytest.raises(ValueError):
        hb.tile_pog_to_tileset(str(tmp_path / 'raw.tif'), tile_degrees=90)  # not a POG


def test_make_path_pog_expand_to_global_extent_false_makes_a_subpog(half_empty_pog, tmp_path):
    """A non-aligned regional raster becomes a subpog on the snapped box; the default still makes a global POG."""
    box = [10.3, -20.7, 45.2, 12.1]
    regional = str(tmp_path / 'regional.tif')
    gdal.Translate(regional, half_empty_pog, projWin=[box[0], box[3], box[2], box[1]])
    assert not hb.is_path_subpog(regional), 'the unsnapped clip is not aligned'

    sub = str(tmp_path / 'regional_sub.tif')
    hb.make_path_pog(regional, sub, expand_to_global_extent=False)
    assert hb.is_path_subpog(sub) and not hb.is_path_pog(sub)
    gt = hb.get_geotransform_path(sub); shape = hb.get_shape_from_dataset_path(sub)
    got = [gt[0], gt[3] + shape[0] * gt[5], gt[0] + shape[1] * gt[1], gt[3]]
    assert hb.snap_bb_to_pyramid(box, 900) == pytest.approx([10.25, -20.75, 45.25, 12.25])
    assert got == pytest.approx([10.25, -20.75, 45.25, 12.25])
    sds = gdal.Open(sub)
    assert sds.GetRasterBand(1).GetOverviewCount() == len(hb.get_pyramid_overview_levels_for_bb(900, got))
    sds = None

    before = os.path.getmtime(sub)
    hb.make_path_pog(sub, expand_to_global_extent=False)  # already a subpog: no-op
    assert os.path.getmtime(sub) == before

    glob_out = str(tmp_path / 'regional_global.tif')
    hb.make_path_pog(regional, glob_out)  # default expands
    assert hb.is_path_pog(glob_out)


def test_main_and_side_rungs_match_table_e1():
    """The ladder of the paper's Table E1: main rungs in integer ratio to each other, side rungs joining at the finest
    main rung they divide, and the asymmetric overview derivation (main bases carry main rungs only)."""
    main = hb.pyramid_main_arcseconds
    assert [hb.arcseconds_to_token(a) for a in main] == ['1-9', '1-3', '1', '2', '10', '30', '150', '300', '900', '1800', '3600', '18000', '36000', '108000', '324000', '648000']
    assert [int(round(b / a)) for a, b in zip(main, main[1:])] == [3, 3, 2, 5, 3, 5, 2, 3, 2, 2, 5, 2, 3, 3, 2]
    assert [hb.arcseconds_to_token(a) for a in hb.pyramid_side_arcseconds] == ['3-10', '9-10', '3', '9', '15', '90', '180', '360', '600']
    assert {hb.arcseconds_to_token(k): v for k, v in hb.pyramid_side_rung_join_arcseconds.items()} == \
        {'3-10': 30, '9-10': 900, '3': 30, '9': 900, '15': 30, '90': 900, '180': 900, '360': 1800, '600': 1800}
    levels = hb.pyramid_compatible_overview_levels
    assert levels[1.0] == [2, 10, 30, 150, 300, 900, 1800, 3600, 18000, 36000, 108000, 324000, 648000]  # no 3 or 15 s side levels
    assert levels[0.3] == [10, 50, 100, 500, 1000, 3000, 6000, 12000, 60000, 120000, 360000, 1080000, 2160000]  # 3, 15, 30 s, then up; not 9/10 s
    assert levels[0.9] == [10, 100, 200, 1000, 2000, 4000, 20000, 40000, 120000, 360000, 720000]  # 9, 90, 180 s, then 900 s up
    assert levels[600.0] == [3, 6, 30, 60, 180, 540, 1080] and levels[648000.0] == []
    overhead = {k: round(100 * sum(1 / f ** 2 for f in v), 1) for k, v in levels.items() if isinstance(k, float)}
    assert (overhead[1.0], overhead[10.0], overhead[30.0], overhead[0.3]) == (26.1, 11.7, 5.1, 1.1)  # Table E1's overhead column
    assert 0 not in hb.pyramid_compatible_resolutions  # no int(0.3) alias collision
    assert hb.arcseconds_to_token(0.3) == '3-10' and hb.arcseconds_to_token(15) == '15' and hb.token_to_arcseconds('9-10') == 0.9
    assert hb.get_tile_filename('cover', 0.3, '40N_130W') == 'cover_3-10sec_40N_130W_1_1.tif'
    assert hb.tile_corner_string_to_tile_matrix_index('40N_130W', 0.3)[0] == '3-10sec'
    assert (hb.pyramid_tile_degrees[3.0], hb.pyramid_tile_degrees[2.0], hb.pyramid_tile_degrees[9.0], hb.pyramid_tile_degrees[90.0]) == (5, 1, 10, None)
    for arcseconds in hb.pyramid_main_arcseconds + hb.pyramid_side_arcseconds:  # the canonical cell is the double nearest a/3600 degrees
        from fractions import Fraction
        assert hb.pyramid_compatible_resolutions[arcseconds] == float(Fraction(arcseconds).limit_denominator(1000000) / 3600)


def test_side_rung_subpog_needs_no_match_raster(tmp_path):
    """A 3-arcsecond (90 m family) window becomes a subpog: the frame is synthesized from the tables, so no
    ha_per_cell raster at the rung is fetched, and the overview chain goes by way of 15 s to its join at 30 s."""
    res = 1 / 1200
    raw, sub = str(tmp_path / 'raw.tif'), str(tmp_path / 'sub.tif')
    ds = gdal.GetDriverByName('GTiff').Create(raw, 1200, 1200, 1, gdal.GDT_Byte, options=['TILED=YES', 'COMPRESS=DEFLATE'])
    ds.SetGeoTransform((10, res, 0, 46, 0, -res))
    ds.GetRasterBand(1).WriteArray(np.tile((np.arange(1200) % 200).astype(np.uint8), (1200, 1)))
    ds.GetRasterBand(1).SetNoDataValue(255)
    ds = None
    assert hb.get_cell_size_from_path_in_arcseconds(raw, force_to_pyramid=True) == 3.0
    hb.make_path_pog(raw, sub, expand_to_global_extent=False)
    assert hb.is_path_subpog(sub)
    sds = gdal.Open(sub); b = sds.GetRasterBand(1)
    widths = [b.GetOverview(i).XSize for i in range(b.GetOverviewCount())]
    sds = None
    assert widths == [1200 // f for f in hb.get_pyramid_overview_levels_for_bb(3.0, [10, 45, 11, 46])] == [240, 120, 24, 12, 4, 2, 1]


def test_rung_with_no_levels_gets_no_driver_overviews(tmp_path):
    """The COG driver would add its own 2, 4, 8 overviews to a large source with none; a rung with no levels must get none."""
    top = str(tmp_path / 'top.tif')
    hb.write_pog_of_value_from_scratch(top, 1, 648000, 1)
    assert hb.is_path_pog(top)
    frame = str(tmp_path / 'frame.tif')
    hb.write_pyramid_frame_raster(frame, 0.3, None, gdal.GDT_Byte, 255)
    fds = gdal.Open(frame)
    assert (fds.RasterXSize, fds.RasterYSize) == (4320000, 2160000) and os.path.getsize(frame) < 5e6  # global 3/10-sec frame, sparse
    fds = None
