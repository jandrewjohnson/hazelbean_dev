"""The POG specification's variable classes, nodata convention, registration shift and conformance check.

Each test builds its own small synthetic rasters (900- or 300-second grids, a few MB) so none needs base_data. The
requirements are those of the pyramids paper's Section 4.1 and Appendices A.3, D.2 and G, mirrored in pogs.qmd.
"""
import filecmp
import os

import numpy as np
import pytest
from osgeo import gdal, gdal_array

import hazelbean as hb


def _write(path, arr, arcseconds, ndv=None, bb=None, metadata=None, projection=True):
    res = hb.pyramid_compatible_resolutions[arcseconds]
    left, top = (-180.0, 90.0) if bb is None else (bb[0], bb[3])
    ds = gdal.GetDriverByName('GTiff').Create(path, arr.shape[1], arr.shape[0], 1, gdal_array.NumericTypeCodeToGDALTypeCode(arr.dtype), options=['TILED=YES', 'COMPRESS=DEFLATE'])
    ds.SetGeoTransform((left, res, 0.0, top, 0.0, -res))
    if projection:
        ds.SetProjection(hb.wgs_84_wkt)
    for k, v in (metadata or {}).items():
        ds.SetMetadataItem(k, v)
    ds.GetRasterBand(1).WriteArray(arr)
    if ndv is not None:
        ds.GetRasterBand(1).SetNoDataValue(ndv)
    ds = None
    return path


def _overview(path, i):
    ds = gdal.Open(path)
    return ds.GetRasterBand(1).GetOverview(i).ReadAsArray()


@pytest.fixture
def gradient_900(tmp_path):
    """A global 900-second float field that varies with latitude and longitude, with an Arctic nodata cap."""
    arr = (np.add.outer(np.linspace(0, 1, 720), np.linspace(0, 1, 1440)) / 2).astype(np.float32)
    arr[:40] = -9999
    return _write(str(tmp_path / 'gradient.tif'), arr, 900.0, ndv=-9999)


def test_extensive_sums_overviews_and_promotes_integers(tmp_path):
    counts = np.random.default_rng(0).integers(0, 250, (720, 1440)).astype(np.uint8)
    pog = str(tmp_path / 'counts_pog.tif')
    hb.make_path_pog(_write(str(tmp_path / 'counts.tif'), counts, 900.0), pog, variable_class='extensive')
    assert hb.is_path_pog(pog, verbose=True)
    ds = gdal.Open(pog)
    assert ds.GetRasterBand(1).DataType == gdal.GDT_Int64  # cannot overflow at the top rung
    assert ds.GetRasterBand(1).GetNoDataValue() is None
    assert hb.get_pog_metadata(pog) == {'POG_VARIABLE_CLASS': 'extensive'}
    ds = None
    total = int(counts.astype(np.int64).sum())
    for i, f in enumerate(hb.pyramid_compatible_overview_levels[900.0]):
        level = _overview(pog, i)
        assert level.sum() == total, f'the total is the same at every rung (level {f})'
    assert np.array_equal(_overview(pog, 0), counts.astype(np.int64).reshape(360, 2, 720, 2).sum(axis=(1, 3)))


def test_intensive_overviews_are_area_weighted_and_observed_area_is_derived(gradient_900, tmp_path):
    pog = str(tmp_path / 'share.tif')
    hb.make_path_pog(gradient_900, pog, variable_class='intensive', observed_area_path='derive')
    observed = str(tmp_path / 'share_observed_area.tif')
    assert hb.is_path_pog(pog, verbose=True) and hb.is_path_pog(observed, verbose=True)
    meta = hb.get_pog_metadata(pog)
    assert meta == {'POG_VARIABLE_CLASS': 'intensive', 'POG_INTENSIVE_WEIGHTING': 'area',
                    'POG_DENOMINATOR': 'share_observed_area.tif', 'POG_OBSERVED_AREA': 'share_observed_area.tif'}
    assert hb.get_pog_metadata(observed)['POG_VARIABLE_CLASS'] == 'extensive'
    base = gdal.Open(pog).ReadAsArray().astype(np.float64)
    assert gdal.Open(pog).GetRasterBand(1).GetNoDataValue() is None and np.all(base[:40] == 0)  # nodata became zero
    area = gdal.Open(observed).ReadAsArray()
    ha = hb.ha_per_cell_rows(90.0, 0.25, 720)
    assert np.all(area[:40] == 0) and np.allclose(area[40:], ha[40:, None])
    # A 2 x 2 parent is the area-weighted mean of its children, not the plain mean (they differ where latitude varies).
    parent = _overview(pog, 0).astype(np.float64)
    num = (base * area).reshape(360, 2, 720, 2).sum(axis=(1, 3))
    den = area.reshape(360, 2, 720, 2).sum(axis=(1, 3))
    assert np.allclose(parent, np.divide(num, den, out=np.zeros_like(num), where=den > 0), rtol=1e-6)
    # Proportion x area aggregates to the same total at every rung: the lattice's consistency identity.
    for i, f in enumerate(hb.pyramid_compatible_overview_levels[900.0][:4]):
        level_area = _overview(observed, i).astype(np.float64)
        assert np.isclose((_overview(pog, i) * level_area).sum(), (base * area).sum(), rtol=1e-6)


def test_conformance_check_catches_a_mislabelled_rule(gradient_900, tmp_path):
    """A file records no method, so is_path_pog recomputes a sample of overview cells: an unweighted-mean raster that
    claims area weighting fails, and declaring POG_INTENSIVE_WEIGHTING=none makes it pass."""
    pog = str(tmp_path / 'plain.tif')
    hb.make_path_pog(gradient_900, pog, variable_class='intensive', intensive_weighting='none')
    assert hb.get_pog_metadata(pog)['POG_INTENSIVE_WEIGHTING'] == 'none'
    assert hb.is_path_pog(pog, verbose=True)
    ds = gdal.OpenEx(pog, gdal.OF_UPDATE, open_options=['IGNORE_COG_LAYOUT_BREAK=YES'])
    ds.SetMetadataItem('POG_INTENSIVE_WEIGHTING', 'area'); ds.SetMetadataItem('POG_DENOMINATOR', 'ha_per_cell')
    ds = None
    assert not hb.is_path_pog_overview_conformant(pog, verbose=True)
    assert not hb.is_path_pog(pog)


def test_categorical_and_covariate_nodata_conventions(tmp_path):
    lulc = np.full((720, 1440), 255, dtype=np.uint8); lulc[360:] = 3
    cat = str(tmp_path / 'lulc_pog.tif')
    hb.make_path_pog(_write(str(tmp_path / 'lulc.tif'), lulc, 900.0, ndv=255), cat, variable_class='categorical', categorical_none_value=9)
    ds = gdal.Open(cat)
    assert ds.GetRasterBand(1).GetNoDataValue() is None and set(np.unique(ds.ReadAsArray())) == {3, 9}  # nodata became the none class
    ds = None
    elevation = np.linspace(-100, 4000, 720 * 1440, dtype=np.float32).reshape(720, 1440); elevation[:10] = -32768
    cov = str(tmp_path / 'elevation_pog.tif')
    hb.make_path_pog(_write(str(tmp_path / 'elevation.tif'), elevation, 900.0, ndv=-32768), cov, variable_class='covariate')
    assert hb.is_path_pog(cov, verbose=True)
    ds = gdal.Open(cov); arr = ds.ReadAsArray()
    assert ds.GetRasterBand(1).GetNoDataValue() == -9999 and np.all(arr[:10] == -9999) and not np.any(arr == -32768)  # per-type nodata, values converted
    ds = None


def test_undeclared_input_is_classed_by_data_type(tmp_path):
    pog = str(tmp_path / 'ids_pog.tif')
    hb.make_path_pog(_write(str(tmp_path / 'ids.tif'), np.ones((720, 1440), dtype=np.int32), 900.0, projection=False), pog)
    assert hb.get_pog_metadata(pog)['POG_VARIABLE_CLASS'] == 'categorical'
    assert hb.is_path_pog(pog, verbose=True)  # the CRS is set to EPSG:4326 on the way


def test_validator_rejects_what_the_spec_rejects(tmp_path):
    good = str(tmp_path / 'good.tif')
    hb.write_pog_of_value_from_scratch(good, 1.0, 900, gdal.GDT_Float32, variable_class='intensive')
    assert hb.is_path_pog(good, verbose=True)
    lzw = str(tmp_path / 'lzw.tif')
    gdal.Translate(lzw, good, creationOptions=['COMPRESS=LZW', 'TILED=YES', 'COPY_SRC_OVERVIEWS=YES'])
    assert not hb.is_path_global_pyramid(lzw)  # DEFLATE only
    for key, value in (('CONTROL', None), ('POG_VARIABLE_CLASS', None), ('AREA_OR_POINT', 'Point')):  # CONTROL: same path, nothing removed
        bad = str(tmp_path / f'bad_{key}.tif')
        gdal.Translate(bad, good, creationOptions=['COMPRESS=DEFLATE', 'TILED=YES', 'COPY_SRC_OVERVIEWS=YES'])
        ds = gdal.OpenEx(bad, gdal.OF_UPDATE, open_options=['IGNORE_COG_LAYOUT_BREAK=YES'])
        md = ds.GetMetadata(); md.pop(key, None)
        if value is not None:
            md[key] = value
        ds.SetMetadata(md); ds = None
        assert hb.is_path_global_pyramid(bad, verbose=True) == (key == 'CONTROL'), key


def test_exact_aggregation_between_rungs(tmp_path):
    """output_arcseconds onto a coarser rung the input divides is a block aggregation by the class rule: totals are exact."""
    counts = np.random.default_rng(1).random((2160, 4320)).astype(np.float64) * 10
    counts[:30] = -9999
    src = _write(str(tmp_path / 'fine.tif'), counts, 300.0, ndv=-9999)
    coarse = str(tmp_path / 'coarse.tif')
    hb.make_path_pog(src, coarse, output_arcseconds=900, variable_class='extensive', observed_area_path='derive')
    assert hb.is_path_pog(coarse, verbose=True)
    assert np.isclose(gdal.Open(coarse).ReadAsArray().sum(), counts[30:].sum(), rtol=1e-12)
    observed = gdal.Open(str(tmp_path / 'coarse_observed_area.tif')).ReadAsArray()
    assert np.isclose(observed.sum(), hb.ha_per_cell_rows(90.0, 1 / 12, 2160)[30:].sum() * 4320, rtol=1e-12)
    assert np.all(observed[9] < observed[11])  # the 900 s row holding the nodata edge is only partly observed


def test_registration_shift_admits_a_point_registered_tile(tmp_path):
    """A 3601 x 3601 point-registered 1-arcsecond tile (SRTM layout) becomes a 3600 x 3600 canonical subpog with its
    values unchanged, by the half-cell shift of Appendix G.4, recorded in POG_REGISTRATION_SHIFT."""
    n = 3601
    dem = (np.arange(n * n, dtype=np.int32).reshape(n, n) % 5000).astype(np.int16)
    raw = str(tmp_path / 'N40W130.tif')
    ds = gdal.GetDriverByName('GTiff').Create(raw, n, n, 1, gdal.GDT_Int16)
    ds.SetMetadataItem('AREA_OR_POINT', 'Point')
    res = 1 / 3600
    ds.SetGeoTransform((-130 - res / 2, res, 0, 41 + res / 2, 0, -res))  # samples on whole arcseconds, 40N..41N
    ds.SetProjection(hb.wgs_84_wkt)
    ds.GetRasterBand(1).WriteArray(dem)
    ds = None
    sub = str(tmp_path / 'dem_1sec_40N_130W_1_1.tif')
    hb.make_path_pog(raw, sub, expand_to_global_extent=False, variable_class='covariate')
    assert hb.is_path_subpog(sub, verbose=True)
    ds = gdal.Open(sub)
    assert ds.GetGeoTransform() == (-130.0, res, 0.0, 41.0, 0.0, -res) and (ds.RasterXSize, ds.RasterYSize) == (3600, 3600)
    assert ds.GetMetadataItem('AREA_OR_POINT') == 'Area' and hb.get_pog_metadata(sub)['POG_REGISTRATION_SHIFT'] == '+0.5,-0.5'
    assert np.array_equal(ds.ReadAsArray(), dem[:3600, :3600])  # copied, not resampled; the duplicated south row and east column dropped
    ds = None
    assert hb.get_tile_bb_from_corner_string(hb.parse_tile_filename(sub)[2], 1) == [-130, 40, -129, 41]


def test_tileset_round_trip_rebuilds_the_pog(tmp_path):
    """A tile set converts back to a single POG by one copy of its VRT through make_path_pog: same values, same
    overviews, same metadata, and (the claim of D.5.2) the same bytes."""
    counts = np.zeros((720, 1440), dtype=np.float32); counts[400:600, 800:1300] = 2.5
    pog = str(tmp_path / 'crop_900sec.tif')
    hb.make_path_pog(_write(str(tmp_path / 'crop.tif'), counts, 900.0), pog, variable_class='extensive')
    vrt = hb.tile_pog_to_tileset(pog, tile_degrees=90)
    assert os.path.basename(vrt) == 'crop_900sec_90deg.vrt' and hb.is_path_pog_tileset(vrt, verbose=True)
    assert sorted(os.listdir(str(tmp_path / 'crop_900sec_90deg'))) == ['crop_900sec_90S_0E_90_90.tif', 'crop_900sec_90S_90E_90_90.tif']  # all-zero tiles omitted
    rebuilt = str(tmp_path / 'rebuilt' / 'crop_900sec.tif')
    os.makedirs(os.path.dirname(rebuilt))
    hb.make_path_pog(vrt, rebuilt)
    assert hb.is_path_pog(rebuilt, verbose=True) and hb.get_pog_metadata(rebuilt) == hb.get_pog_metadata(pog)
    for i in range(len(hb.pyramid_compatible_overview_levels[900.0])):
        assert np.array_equal(_overview(rebuilt, i), _overview(pog, i))
    assert filecmp.cmp(pog, rebuilt, shallow=False)


def test_ha_per_cell_pog_is_additive_across_rungs(tmp_path):
    path = hb.write_ha_per_cell_pog(str(tmp_path / 'ha_per_cell_900sec.tif'), 900)
    assert hb.is_path_pog(path, verbose=True)
    top = _overview(path, len(hb.pyramid_compatible_overview_levels[900.0]) - 1)
    assert top.shape == (1, 2) and np.allclose(top, hb.ha_per_cell_rows(90.0, 180.0, 1)[0], rtol=1e-12)  # each 180 x 180 degree face
    assert np.isclose(top.sum(), 5.10065621e10, rtol=1e-8)  # the WGS84 authalic area, in hectares
