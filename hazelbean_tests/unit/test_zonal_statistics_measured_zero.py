"""A zone whose measured quantity is zero must survive zonal_statistics_flex's sums_counts export.

Emptiness is `counts == 0`: nothing was measured there. A sum of exactly 0.0 over a zone full of
valid pixels is a measurement, and deleting it makes a measured zero indistinguishable from a zone
with no data -- which, for anything that later forms a ratio or a regional total, is the difference
between a real loss and a gap.
"""
import numpy as np
import pytest

import hazelbean as hb


def write_raster(path, array, data_type, nodata=None):
    from osgeo import gdal, osr
    array = np.asarray(array)
    n_rows, n_cols = array.shape
    ds = gdal.GetDriverByName('GTiff').Create(str(path), n_cols, n_rows, 1, data_type)
    ds.SetGeoTransform((-180.0, 360.0 / n_cols, 0.0, 90.0, 0.0, -180.0 / n_rows))
    srs = osr.SpatialReference(); srs.ImportFromEPSG(4326); ds.SetProjection(srs.ExportToWkt())
    band = ds.GetRasterBand(1)
    if nodata is not None:
        band.SetNoDataValue(float(nodata))
    band.WriteArray(array); band.FlushCache(); ds = None


@pytest.fixture
def three_zones(tmp_path):
    """Zone 1 holds nonzero values, zone 2 holds valid zeros, zone 3 holds only nodata."""
    from osgeo import gdal
    zones = np.array([[1, 1, 2, 2],
                      [1, 1, 2, 2],
                      [3, 3, 3, 3]], dtype='int32')
    values = np.array([[2.0, 3.0, 0.0, 0.0],
                       [4.0, 1.0, 0.0, 0.0],
                       [np.nan, np.nan, np.nan, np.nan]], dtype='float32')
    zones_path = tmp_path / 'zone_ids.tif'
    values_path = tmp_path / 'values.tif'
    write_raster(zones_path, zones, gdal.GDT_Int32)
    write_raster(values_path, values, gdal.GDT_Float32, nodata=float('nan'))
    return str(zones_path), str(values_path)


def statistics(zones_path, values_path):
    unique_ids, sums, counts = hb.zonal_statistics_rasterized(
        zones_path, values_path, zones_ndv=-9999, values_ndv=float('nan'),
        unique_zone_ids=np.asarray([0, 1, 2, 3], dtype='int64'), stats_to_retrieve='sums_counts')
    return {int(z): (float(sums[z]), int(counts[z])) for z in [1, 2, 3]}


def test_the_kernel_separates_a_measured_zero_from_an_unmeasured_zone(three_zones):
    """Before any filtering: the zero zone carries four valid pixels, the nodata zone carries none.
    The distinction the export has to preserve exists in the data."""
    by_zone = statistics(*three_zones)
    assert by_zone[1] == (pytest.approx(10.0), 4)
    assert by_zone[2] == (pytest.approx(0.0), 4)     # measured, and zero
    assert by_zone[3][1] == 0                        # nothing measured


def test_measured_zero_survives_the_sums_counts_export(three_zones):
    """THE REGRESSION. `df[df == 0] = np.nan` + dropna deleted zone 2 along with zone 3."""
    zones_path, values_path = three_zones
    by_zone = statistics(zones_path, values_path)
    import pandas as pd
    frame = pd.DataFrame(index=[1, 2, 3],
                         data={'sums': [by_zone[z][0] for z in (1, 2, 3)],
                               'counts': [by_zone[z][1] for z in (1, 2, 3)]})
    kept = frame[frame['counts'] > 0]
    assert set(kept.index) == {1, 2}
    assert kept.loc[2, 'sums'] == pytest.approx(0.0)
    assert kept.loc[2, 'counts'] == 4


def test_flex_keeps_the_zero_zone_end_to_end(tmp_path, three_zones):
    """Through zonal_statistics_flex itself, on a vector built from the same zones, so the export
    path under repair is the one exercised."""
    geopandas = pytest.importorskip('geopandas')
    from shapely.geometry import box
    zones_path, values_path = three_zones
    # Cells are 90 degrees wide and 60 tall; zone 1 is the left half of the top two rows, zone 2 the
    # right half, zone 3 the bottom row.
    frame = geopandas.GeoDataFrame(
        {'zone_id': [1, 2, 3],
         'geometry': [box(-180, -30, 0, 90), box(0, -30, 180, 90), box(-180, -90, 180, -30)]},
        crs='EPSG:4326')
    vector_path = str(tmp_path / 'zones.gpkg')
    frame.to_file(vector_path, driver='GPKG')
    result = hb.zonal_statistics_flex(
        values_path, vector_path, zone_ids_raster_path=str(tmp_path / 'flex_zone_ids.tif'),
        id_column_label='zone_id', zones_raster_data_type=5, all_touched=False,
        stats_to_retrieve='sums_counts', assert_projections_same=False, verbose=False)
    assert 2 in result.index, 'the valid-zero zone was dropped by the export'
    assert result.loc[2, 'sums'] == pytest.approx(0.0)
    assert result.loc[2, 'counts'] > 0
    assert 3 not in result.index, 'a zone with no valid pixels should not be reported'
