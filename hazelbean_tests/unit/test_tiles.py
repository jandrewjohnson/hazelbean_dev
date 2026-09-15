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
    assert hb.get_tile_corner_string(-130, 40) == 'N40W130'
    assert hb.get_tile_corner_string(10, -5) == 'S05E010'
    assert hb.get_tile_corner_string(-180, -90) == 'S90W180'
    assert hb.parse_tile_corner_string('N40W130') == (-130, 40)
    assert hb.get_tile_bb_from_corner_string('N40W130', 10) == [-130, 40, -120, 50]
    with pytest.raises(ValueError):
        hb.parse_tile_corner_string('N4W130')


def test_tile_filename_round_trip():
    name = hb.get_tile_filename('lulc_esa_2020', 10, 'N40W130')
    assert name == 'lulc_esa_2020_10sec_10deg_N40W130.tif'
    assert hb.parse_tile_filename('/anywhere/' + name) == ('lulc_esa_2020', 10.0, 10, 'N40W130')
    with pytest.raises(ValueError):
        hb.get_tile_filename('x', 300, 'N40W130')  # 300 sec is not a tiled resolution
    with pytest.raises(ValueError):
        hb.parse_tile_filename('lulc_esa_2020_10sec.tif')


def test_every_corner_addresses_through_the_ogc_tile_matrix():
    """A subpog tile set is addressable through the tile matrix set: corner <-> (tileMatrix, row, col) is a bijection."""
    corners = hb.list_tile_corner_strings(10)
    assert len(corners) == 36 * 18
    assert corners[0] == 'N80W180' and corners[-1] == 'S90E170'  # OGC row order: north to south, west to east
    seen = set()
    for corner in corners:
        matrix_id, row, col = hb.tile_corner_string_to_tile_matrix_index(corner, 10)
        assert matrix_id == '10sec' and 0 <= row < 18 and 0 <= col < 36
        seen.add((row, col))
        assert hb.tile_matrix_index_to_tile_corner_string(10, row, col) == corner
    assert len(seen) == len(corners)
    assert hb.tile_corner_string_to_tile_matrix_index('N80W180', 10) == ('10sec', 0, 0)


def test_tile_matrix_set_is_valid_ogc_tms_2_0(tmp_path):
    """The compliance test: the published document validates against the OGC TMS 2.0 schema shipped in hazelbean."""
    tms = hb.get_pyramid_tile_matrix_set()
    assert [m['id'] for m in tms['tileMatrices']] == [f'{s}sec' for s in (1, 10, 30, 150, 300, 900, 1800, 3600, 7200, 14400, 36000)]
    ten = tms['tileMatrices'][1]
    assert (ten['tileWidth'], ten['matrixWidth'], ten['matrixHeight']) == (3600, 36, 18)
    assert tms['tileMatrices'][4]['matrixWidth'] == 1  # 300 sec: one global tile
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
    assert hb.get_pyramid_overview_levels_for_bb(1, [0, 0, 1, 1]) == [10, 30, 150, 300, 900, 1800, 3600]
    assert hb.get_pyramid_overview_levels_for_bb(10, [0, 0, 10, 10]) == [3, 15, 30, 90, 180, 360, 720, 3600]  # 4 deg does not divide 10
    assert hb.get_pyramid_overview_levels_for_bb(10, [-180, -90, 180, 90]) == hb.pyramid_compatible_overview_levels[10]


@pytest.fixture
def half_empty_pog(tmp_path):
    """A 900-second Byte POG whose west half is nodata."""
    raw, pog = str(tmp_path / 'raw.tif'), str(tmp_path / 'gradient.tif')
    W, H = 1440, 720
    ds = gdal.GetDriverByName('GTiff').Create(raw, W, H, 1, gdal.GDT_Byte, options=['TILED=YES', 'COMPRESS=DEFLATE'])
    ds.SetGeoTransform(hb.pyramid_compatible_geotransforms[900.0])
    arr = np.full((H, W), 255, dtype=np.uint8)
    arr[:, W // 2:] = (np.arange(W // 2) % 200).astype(np.uint8)
    ds.GetRasterBand(1).WriteArray(arr)
    ds.GetRasterBand(1).SetNoDataValue(255)
    ds = None
    hb.make_path_pog(raw, pog)
    assert hb.is_path_pog(pog, verbose=True)
    return pog


def test_tile_pog_to_tileset_and_vrt(half_empty_pog):
    vrt = hb.tile_pog_to_tileset(half_empty_pog, tile_degrees=90)
    tile_dir = os.path.join(os.path.dirname(half_empty_pog), 'gradient_900sec_90deg')
    tiles = sorted(os.path.basename(t) for t in glob.glob(os.path.join(tile_dir, '*.tif')))
    assert tiles == ['gradient_900sec_90deg_N00E000.tif', 'gradient_900sec_90deg_N00E090.tif',
                     'gradient_900sec_90deg_S90E000.tif', 'gradient_900sec_90deg_S90E090.tif'], 'only the non-empty east half is written'
    assert all(hb.is_path_subpog(os.path.join(tile_dir, t)) for t in tiles)
    assert not hb.is_path_pog(os.path.join(tile_dir, tiles[0]))
    assert hb.is_path_pog_tileset(vrt)
    xml = open(vrt).read()
    assert 'relativeToVRT="1"' in xml and tile_dir not in xml

    src = gdal.Open(half_empty_pog); vds = gdal.Open(vrt)
    assert vds.GetGeoTransform() == hb.pyramid_compatible_geotransforms[900.0]
    assert np.array_equal(src.ReadAsArray(), vds.ReadAsArray())
    original = src.ReadAsArray(); src = vds = None

    # Sparse tile sets are legitimate: a missing tile reads as nodata, everything else is unchanged.
    os.remove(os.path.join(tile_dir, 'gradient_900sec_90deg_N00E090.tif'))
    vds = gdal.Open(hb.build_pog_tileset_vrt(tile_dir)); sparse = vds.ReadAsArray(); vds = None
    assert np.all(sparse[0:360, 1080:1440] == 255)
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
