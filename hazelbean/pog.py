import os
import math
from fractions import Fraction
from osgeo import gdal, gdal_array, osr
import numpy as np
import tqdm
import multiprocessing as mp
from functools import partial # Useful for passing fixed arguments to worker

import hazelbean as hb


# ---------- Variable classes (the paper's Appendix A.3 and D.2.4; pogs.qmd) ----------
# Every POG declares how its overviews were computed, because a file records no method:
#   extensive    hectares, tonnes, counts: SUMMATION overviews, so every rung carries the exact total beneath it.
#                Integer extensive rasters are promoted to Int64 so the top rung cannot overflow.
#   intensive    proportions, densities, rates: AREA-WEIGHTED MEAN overviews, written at build time as the ratio of two
#                sum pyramids (value x denominator, and denominator). The denominator is the token ha_per_cell (the
#                WGS84 hectares of each cell, the same stack as the ha_per_cell POGs) or, for a variable defined only
#                where observed, its observed-area POG. POG_INTENSIVE_WEIGHTING=none declares the plain unweighted mean,
#                a permitted fast approximation that carries no exactness claim.
#   categorical  class labels: MODE overviews, for display only; modeling uses per-class intensive proportions.
#   covariate    elevation, temperature and other fields where zero is a measurement: keep the per-type nodata value
#                and unweighted mean overviews over valid children, with no exactness claim.
# Extensive, intensive and categorical POGs carry NO nodata value: a cell with nothing to report holds zero (or the
# none class), and incomplete coverage is carried by a companion observed-area POG (extensive, hectares observed).
POG_VARIABLE_CLASSES = ('extensive', 'intensive', 'categorical', 'covariate')
POG_METADATA_KEYS = ('POG_VARIABLE_CLASS', 'POG_INTENSIVE_WEIGHTING', 'POG_DENOMINATOR', 'POG_OBSERVED_AREA', 'POG_REGISTRATION_SHIFT')
POG_REGISTRATION_SHIFT_VALUE = '+0.5,-0.5'  # cells, longitude then latitude (Appendix G.4)


def _is_integer_gdal_type(data_type):
    return np.issubdtype(gdal_array.GDALTypeCodeToNumericTypeCode(data_type), np.integer)


def get_pog_metadata(path):
    """The POG_* metadata items of a raster as a dict. For a tile-set VRT, read from its first tile (a VRT carries none)."""
    ds = gdal.Open(path)
    if ds is None:
        raise FileNotFoundError(f'Could not open {path}')
    if os.path.splitext(path)[1].lower() == '.vrt' and len(ds.GetFileList()) > 1:
        ds = gdal.Open(ds.GetFileList()[1])
    return {k: v for k, v in (ds.GetMetadata() or {}).items() if k in POG_METADATA_KEYS}


def _resolve_pog_reference(pog_path, reference):
    """A POG_DENOMINATOR / POG_OBSERVED_AREA value as an absolute path (relative values resolve beside pog_path)."""
    if reference is None or reference == 'ha_per_cell':
        return reference
    return reference if os.path.isabs(reference) else os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(pog_path)), reference))


def _pog_reference_for(pog_path, reference_path):
    """How pog_path records a companion file: relative to pog_path's folder, so a folder of POGs moves as one."""
    return os.path.relpath(os.path.abspath(reference_path), os.path.dirname(os.path.abspath(pog_path)))


def ha_per_cell_rows(top_lat, cell_degrees, n_rows):
    """Hectares per cell for n_rows rows of a geographic grid of square cell_degrees cells whose top edge is top_lat.

    WGS84 ellipsoid, the formula of hb.get_area_of_pixel_column_from_center_lats (and so of the ha_per_cell POGs).
    Each row's area is a difference of one cumulative function at the row's edges, so the areas of the rows inside a
    coarser row sum to its area: the additivity that makes area-weighted aggregation exact on the lattice."""
    a, b = 6378137.0, 6356752.3142
    e = math.sqrt(1 - (b / a) ** 2)
    edges = np.clip(top_lat - cell_degrees * np.arange(n_rows + 1, dtype=np.float64), -90.0, 90.0)
    sin = np.sin(np.radians(edges))
    zm, zp = 1 - e * sin, 1 + e * sin
    cumulative = np.pi * b ** 2 * (np.log(zp / zm) / (2 * e) + sin / (zp * zm))
    return cell_degrees / 360.0 * (cumulative[:-1] - cumulative[1:]) / 10000.0


def _cascade_block_sums(read_rows, n_rows, n_cols, factors, emit, max_strip_bytes=256e6):
    """Stream a grid once through a cascade of exact block sums.

    read_rows(r0, r1) returns {name: float64 array (r1 - r0, n_cols)} of the quantities to sum. factors are cumulative
    (each an integer multiple of the one before, as on the ladder). For each level i, emit(i, row0, sums) receives
    {name: float64 array (rows, n_cols // factors[i])} of sums over factors[i] x factors[i] base cells, in row order.
    Each level is summed from the level below, in double precision, so memory holds one base strip and a few rows per level."""
    if not factors:
        return
    steps = [factors[0]] + [factors[i] // factors[i - 1] for i in range(1, len(factors))]
    widths = [n_cols] + [n_cols // f for f in factors]
    for i, (s, f) in enumerate(zip(steps, factors)):
        if f % (factors[i - 1] if i else 1) or n_cols % f or n_rows % f:
            raise ValueError(f'Overview factor {f} does not divide the {n_cols} x {n_rows} grid, or does not nest in the level below.')
    pending = [None] * len(steps)
    next_row = [0] * len(steps)

    def push(level, quantities):
        if pending[level] is not None:
            quantities = {k: np.concatenate([pending[level][k], v]) for k, v in quantities.items()}
        s = steps[level]
        n = next(iter(quantities.values())).shape[0] // s * s
        pending[level] = {k: v[n:] for k, v in quantities.items()}
        if n == 0:
            return
        w = widths[level]
        sums = {k: v[:n].reshape(n // s, s, w // s, s).sum(axis=(1, 3)) for k, v in quantities.items()}
        emit(level, next_row[level], sums)
        next_row[level] += n // s
        if level + 1 < len(steps):
            push(level + 1, sums)

    n_quantities = max(1, len(read_rows(0, 1)))
    strip = max(steps[0], int(max_strip_bytes / (8 * n_cols * n_quantities)) // steps[0] * steps[0])
    for r0 in range(0, n_rows, strip):
        push(0, read_rows(r0, min(n_rows, r0 + strip)))


def _read_window_at_cell_size(path, cell_degrees, lon_left, lat_top, n_cols, n_rows):
    """Read an n_rows x n_cols window, top-left at (lon_left, lat_top), from whichever level of path (base or an overview)
    has the given cell size. Levels are identified by their dimensions, never by position. Returns float64."""
    ds = gdal.Open(path)
    gt = ds.GetGeoTransform()
    band = ds.GetRasterBand(1)
    candidates = [band] + [band.GetOverview(i) for i in range(band.GetOverviewCount())]
    for level in candidates:
        level_cell = gt[1] * ds.RasterXSize / level.XSize
        if abs(level_cell - cell_degrees) <= cell_degrees * 1e-9:
            col, row = int(round((lon_left - gt[0]) / cell_degrees)), int(round((gt[3] - lat_top) / cell_degrees))
            return level.ReadAsArray(col, row, n_cols, n_rows).astype(np.float64)
    raise ValueError(f'{path} has no level at a cell size of {cell_degrees} degrees.')


def _class_block_quantities(variable_class, intensive_weighting, denominator_path, gt, n_cols):
    """(quantities(values, r0, r1) -> {name: array}, finish(sums) -> values) for the exact aggregation of a class.

    Extensive sums the values; intensive divides the block sum of value x weight by the block sum of weight, where the
    weight is 1 (POG_INTENSIVE_WEIGHTING=none), the observed-area POG, or the hectares of each cell (ha_per_cell)."""
    if variable_class == 'extensive':
        return (lambda v, r0, r1: {'s': v}), (lambda sums: sums['s'])
    if variable_class != 'intensive':
        raise ValueError(f'Only extensive and intensive rasters have exact block aggregation, not {variable_class}.')
    if intensive_weighting == 'none':
        weights = lambda r0, r1: np.ones((r1 - r0, n_cols))
    elif denominator_path not in (None, 'ha_per_cell'):
        weights = lambda r0, r1: _read_window_at_cell_size(denominator_path, gt[1], gt[0], gt[3] - r0 * gt[1], n_cols, r1 - r0)
    else:
        weights = lambda r0, r1: np.broadcast_to(ha_per_cell_rows(gt[3] - r0 * gt[1], gt[1], r1 - r0)[:, None], (r1 - r0, n_cols))

    def quantities(v, r0, r1):
        w = weights(r0, r1)
        return {'n': v * w, 'd': np.array(w, dtype=np.float64)}

    def finish(sums):
        out = np.zeros_like(sums['n'])
        np.divide(sums['n'], sums['d'], out=out, where=sums['d'] > 0)
        return out
    return quantities, finish


def _write_class_overviews(ds, overview_levels, variable_class, intensive_weighting, denominator_path):
    """Fill the allocated overviews of ds (a GTiff open for update) by the exact rule of its class, in one pass over the base.

    GDAL's overview builder has no weighted mean and no double-precision sum, so the levels are written directly."""
    band = ds.GetRasterBand(1)
    gt, n_cols, n_rows = ds.GetGeoTransform(), ds.RasterXSize, ds.RasterYSize
    overviews = [band.GetOverview(i) for i in range(band.GetOverviewCount())]
    if [(o.XSize, o.YSize) for o in overviews] != [(n_cols // f, n_rows // f) for f in overview_levels]:
        raise ValueError(f'Allocated overviews {[(o.XSize, o.YSize) for o in overviews]} do not match the levels {overview_levels}.')
    quantities, finish = _class_block_quantities(variable_class, intensive_weighting, denominator_path, gt, n_cols)
    np_type = gdal_array.GDALTypeCodeToNumericTypeCode(band.DataType)
    integer = np.issubdtype(np_type, np.integer)

    def emit(level, row0, sums):
        out = finish(sums)
        overviews[level].WriteArray((np.rint(out) if integer else out).astype(np_type), 0, row0)

    _cascade_block_sums(lambda r0, r1: quantities(band.ReadAsArray(0, r0, n_cols, r1 - r0).astype(np.float64), r0, r1),
                        n_rows, n_cols, overview_levels, emit)


def is_path_pog_overview_conformant(path, n_sample_rows=4, verbose=False):
    """The numerical conformance check of D.2.4: recompute a sample of overview cells of an extensive or intensive POG.

    A file records no resampling method, so the rule is checked on the numbers. In each overview, a few rows spread from
    pole to pole are read and the largest-magnitude cell of each is recomputed from the level directly below it (the
    base, for the first overview) by the declared rule, so every link of the chain is sampled. Floating-point levels
    must agree to a relative 1e-5 (float32 storage); integer levels exactly. Categorical and covariate POGs make no
    exactness claim and pass."""
    meta = get_pog_metadata(path)
    variable_class = meta.get('POG_VARIABLE_CLASS')
    if variable_class not in ('extensive', 'intensive'):
        return True
    weighting = meta.get('POG_INTENSIVE_WEIGHTING', 'area')
    denominator = _resolve_pog_reference(path, meta.get('POG_DENOMINATOR'))
    ds = gdal.Open(path)
    band = ds.GetRasterBand(1)
    gt = ds.GetGeoTransform()
    integer = _is_integer_gdal_type(band.DataType)
    finer_cell = gt[1]
    for i in range(band.GetOverviewCount()):
        ovr = band.GetOverview(i)
        cell = gt[1] * ds.RasterXSize / ovr.XSize
        step = int(round(cell / finer_cell))
        for row in sorted({int(round(k * (ovr.YSize - 1) / max(1, n_sample_rows - 1))) for k in range(n_sample_rows)}):
            values = ovr.ReadAsArray(0, row, ovr.XSize, 1)[0].astype(np.float64)
            col = int(np.argmax(np.abs(values)))
            lon_left, lat_top = gt[0] + col * cell, gt[3] - row * cell
            block = _read_window_at_cell_size(path, finer_cell, lon_left, lat_top, step, step)
            quantities, finish = _class_block_quantities(variable_class, weighting, denominator, (lon_left, finer_cell, 0.0, lat_top, 0.0, -finer_cell), step)
            expected = finish({k: np.array([[v.sum()]]) for k, v in quantities(block, 0, step).items()})[0, 0]
            scale = float(np.abs(block).max()) * (step * step if variable_class == 'extensive' else 1)
            ok = values[col] == round(expected) if integer else math.isclose(values[col], expected, rel_tol=1e-5, abs_tol=1e-6 * scale + 1e-12)
            if not ok:
                if verbose:
                    hb.log(f'Not conformant: overview {i} ({hb.arcseconds_to_token(cell * 3600)} arcseconds) cell ({row}, {col}) holds {values[col]}, '
                           f'but the {variable_class} rule on the level below gives {expected}: {path}')
                return False
        finer_cell = cell
    return True


def _apply_pog_nodata_rule(input_path, output_path, variable_class, output_data_type, fill_value=0, observed_area_output_path=None, max_strip_bytes=256e6):
    """Write input_path to output_path under the nodata convention of D.2.6.

    Extensive, intensive and categorical: every nodata (or non-finite) cell takes fill_value (zero, or the none class)
    and the nodata declaration is dropped. Covariate: nodata cells take the per-type nodata value, which is declared.
    With observed_area_output_path, also write the companion observed-area raster: hectares observed per cell (Float64)."""
    src = gdal.Open(input_path)
    band = src.GetRasterBand(1)
    src_ndv = band.GetNoDataValue()
    gt, n_cols, n_rows = src.GetGeoTransform(), src.RasterXSize, src.RasterYSize
    driver = gdal.GetDriverByName('GTiff')
    dst_ndv = hb.no_data_values_by_gdal_type[output_data_type][0] if variable_class == 'covariate' else None
    targets = [(output_path, output_data_type, dst_ndv)] + ([(observed_area_output_path, gdal.GDT_Float64, None)] if observed_area_output_path else [])
    dsts = []
    for path, data_type, ndv in targets:
        dst = driver.Create(path, n_cols, n_rows, 1, data_type, options=hb.globals.PRECOG_GTIFF_CREATION_OPTIONS_LIST)
        dst.SetGeoTransform(gt)
        dst.SetProjection(src.GetProjection() or hb.wgs_84_wkt)
        if ndv is not None:
            dst.GetRasterBand(1).SetNoDataValue(ndv)
        dsts.append(dst)
    dsts[0].SetMetadata(src.GetMetadata())
    np_type = gdal_array.GDALTypeCodeToNumericTypeCode(output_data_type)
    strip = max(1, int(max_strip_bytes / (8 * n_cols)))
    for r0 in range(0, n_rows, strip):
        r1 = min(n_rows, r0 + strip)
        values = band.ReadAsArray(0, r0, n_cols, r1 - r0)
        valid = np.ones(values.shape, dtype=bool) if src_ndv is None else values != src_ndv
        if np.issubdtype(values.dtype, np.floating):
            valid &= np.isfinite(values)
        dsts[0].GetRasterBand(1).WriteArray(np.where(valid, values, fill_value if dst_ndv is None else dst_ndv).astype(np_type), 0, r0)
        if observed_area_output_path:
            dsts[1].GetRasterBand(1).WriteArray(valid * ha_per_cell_rows(gt[3] - r0 * gt[1], gt[1], r1 - r0)[:, None], 0, r0)
    dsts = src = None
    return output_path


def _aggregate_on_lattice(input_path, output_path, output_arcseconds, variable_class, intensive_weighting, output_data_type, observed_area_output_path=None):
    """Aggregate a raster aligned on one rung onto a coarser rung it divides, by the exact rule of its class.

    Extensive children are summed; intensive children are averaged weighted by their hectares (or unweighted, for
    intensive_weighting='none'). Nodata children are left out, and a coarse cell with no valid child is nodata. With
    observed_area_output_path, also write the hectares of valid children under each coarse cell (the observed-area
    companion), which is exact here because it is itself a block sum."""
    src = gdal.Open(input_path)
    band = src.GetRasterBand(1)
    src_ndv = band.GetNoDataValue()
    gt, n_cols, n_rows = src.GetGeoTransform(), src.RasterXSize, src.RasterYSize
    res = hb.pyramid_compatible_resolutions[output_arcseconds]
    factor = int(round(res / gt[1]))
    dst_ndv = hb.no_data_values_by_gdal_type[output_data_type][0]
    driver = gdal.GetDriverByName('GTiff')
    dsts = []
    for path, data_type, ndv in [(output_path, output_data_type, dst_ndv)] + ([(observed_area_output_path, gdal.GDT_Float64, None)] if observed_area_output_path else []):
        dst = driver.Create(path, n_cols // factor, n_rows // factor, 1, data_type, options=hb.globals.PRECOG_GTIFF_CREATION_OPTIONS_LIST)
        dst.SetGeoTransform((gt[0], res, 0.0, gt[3], 0.0, -res))
        dst.SetProjection(src.GetProjection() or hb.wgs_84_wkt)
        if ndv is not None:
            dst.GetRasterBand(1).SetNoDataValue(ndv)
        dsts.append(dst)
    np_type = gdal_array.GDALTypeCodeToNumericTypeCode(output_data_type)
    area_weighted = variable_class == 'intensive' and intensive_weighting == 'area'

    def read(r0, r1):
        values = band.ReadAsArray(0, r0, n_cols, r1 - r0).astype(np.float64)
        valid = np.isfinite(values) if src_ndv is None else (values != src_ndv) & np.isfinite(values)
        ha = np.broadcast_to(ha_per_cell_rows(gt[3] - r0 * gt[1], gt[1], r1 - r0)[:, None], values.shape)
        weight = valid * (ha if area_weighted else 1.0)
        return {'observed': valid * ha, 'numerator': np.where(valid, values, 0.0) * (weight if variable_class == 'intensive' else 1.0), 'denominator': weight}

    def emit(level, row0, sums):
        out = sums['numerator'] if variable_class == 'extensive' else np.divide(sums['numerator'], np.where(sums['denominator'] > 0, sums['denominator'], 1.0))
        out = np.where(sums['denominator'] > 0, out, dst_ndv)
        dsts[0].GetRasterBand(1).WriteArray((np.rint(out) if np.issubdtype(np_type, np.integer) else out).astype(np_type), 0, row0)
        if observed_area_output_path:
            dsts[1].GetRasterBand(1).WriteArray(sums['observed'], 0, row0)

    _cascade_block_sums(read, n_rows, n_cols, [factor], emit)
    dsts = src = None
    return output_path


def _write_registration_shifted_copy(input_path, output_path, arcseconds):
    """The registration shift of Appendix G.4, if it applies: returns True and writes output_path, else returns False.

    It applies to a point-registered raster (AREA_OR_POINT=Point) whose samples fall on canonical grid lines of the rung
    (SRTM, NASADEM, ASTER GDEM, the Copernicus DEM). Each sample is read as the canonical cell whose north-west corner it
    occupies: the geotransform moves half a cell east and half a cell south of GDAL's cell-centred reading, the values
    are copied unchanged, and the duplicated tile edge (the last row and column of a 3601 x 3601 tile, which belong to
    the neighbouring tiles) is dropped. Uniform, so every derivative of the field (slope, flow direction) is unchanged."""
    ds = gdal.Open(input_path)
    if (ds.GetMetadataItem('AREA_OR_POINT') or 'Area').lower() != 'point':
        return False
    res = hb.pyramid_compatible_resolutions[arcseconds]
    gt = ds.GetGeoTransform()
    if abs(gt[1] - res) > res * 1e-6 or abs(-gt[5] - res) > res * 1e-6 or gt[2] != 0 or gt[4] != 0:
        return False
    # GDAL reports a point-registered file with its sample centred in a cell, so the sample sits half a cell in.
    cells_x, cells_y = (gt[0] + res / 2 + 180) / res, (90 - (gt[3] - res / 2)) / res
    if abs(cells_x - round(cells_x)) > 1e-6 or abs(cells_y - round(cells_y)) > 1e-6:
        return False
    n_cols, n_rows = ds.RasterXSize, ds.RasterYSize
    cells_per_degree = Fraction(3600) / Fraction(arcseconds).limit_denominator(1000000)
    if cells_per_degree.denominator == 1:
        per_degree = int(cells_per_degree)
        n_cols -= 1 if n_cols > 1 and n_cols % per_degree == 1 else 0
        n_rows -= 1 if n_rows > 1 and n_rows % per_degree == 1 else 0
    gdal.Translate(output_path, ds, srcWin=[0, 0, n_cols, n_rows], metadataOptions=['AREA_OR_POINT=Area'],
                   creationOptions=hb.globals.PRECOG_GTIFF_CREATION_OPTIONS_LIST)
    out = gdal.Open(output_path, gdal.GA_Update)
    out.SetMetadataItem('AREA_OR_POINT', 'Area')
    out.SetGeoTransform((round(cells_x) * res - 180, res, 0.0, 90 - round(cells_y) * res, 0.0, -res))
    out = ds = None
    return True


def write_ha_per_cell_pog(output_path, arcseconds, bb=None, compression='DEFLATE', blocksize=512, verbose=False):
    """Write the canonical hectares-per-cell POG of a rung (a subpog over bb, if given): Float64, extensive, sum overviews.

    These rasters are the denominator of every area-weighted aggregation and the one place the size and shape of the
    Earth enter the lattice; the token ha_per_cell in POG_DENOMINATOR refers to exactly these values."""
    res = hb.pyramid_compatible_resolutions[arcseconds]
    if bb is None:
        bb = [-180.0, -90.0, 180.0, 90.0]
    n_cols, n_rows = int(round((bb[2] - bb[0]) / res)), int(round((bb[3] - bb[1]) / res))
    temp_path = hb.temp('.tif', os.path.splitext(os.path.basename(output_path))[0] + '_b4_cog', True, tag_along_file_extensions=['.aux.xml'])
    ds = gdal.GetDriverByName('GTiff').Create(temp_path, n_cols, n_rows, 1, gdal.GDT_Float64, options=hb.globals.PRECOG_GTIFF_CREATION_OPTIONS_LIST)
    ds.SetGeoTransform((bb[0], res, 0.0, bb[3], 0.0, -res))
    ds.SetProjection(hb.wgs_84_wkt)
    strip = max(1, int(256e6 / (8 * n_cols)))
    for r0 in range(0, n_rows, strip):
        r1 = min(n_rows, r0 + strip)
        ds.GetRasterBand(1).WriteArray(np.repeat(ha_per_cell_rows(bb[3] - r0 * res, res, r1 - r0)[:, None], n_cols, axis=1), 0, r0)
    ds = None
    levels = hb.pyramid_compatible_overview_levels[arcseconds] if bb == [-180.0, -90.0, 180.0, 90.0] else hb.get_pyramid_overview_levels_for_bb(arcseconds, bb)
    _write_cog_with_pyramid_overviews(temp_path, output_path, levels, None, gdal.GDT_Float64, None, compression, blocksize, verbose, variable_class='extensive')
    return output_path


def is_path_pog(path, check_tiled=True, full_check=False, raise_exceptions=False, verbose=False):
    
    is_pyramid = hb.is_path_global_pyramid(path, verbose=verbose)
    is_cog = hb.is_path_cog(path, check_tiled=check_tiled, full_check=full_check, raise_exceptions=raise_exceptions, verbose=verbose)

    if verbose:
        if is_pyramid:
            hb.log(f"Raster is a global pyramid: {path}")
        else:
            hb.log(f"Raster is not a global pyramid: {path}")
        if is_cog:
            hb.log(f"Raster is a COG: {path}")
        else:
            hb.log(f"Raster is not a COG: {path}")
            
    return is_pyramid and is_cog




# This worker function will be executed by each process in the pool.
# It needs to be defined at the top level of a module so it can be pickled.
def _worker_make_path_pog_starmap(input_file_path, specific_output_path, common_pog_options_dict):
    """
    Worker function for starmap.
    input_file_path: The specific input file for this task.
    specific_output_path: The specific output file path for this task (can be None).
    common_pog_options_dict: Dictionary of common options for hb.make_path_pog.
    """
    process_name = mp.current_process().name
    base_name = os.path.basename(input_file_path)

    try:
        hb.make_path_pog(
            input_file_path,
            output_raster_path=specific_output_path, # CRITICAL: Use the specific output path
            output_data_type=common_pog_options_dict.get('output_data_type', 'auto'),
            output_arcseconds=common_pog_options_dict.get('output_arcseconds'),
            overview_resampling_method=common_pog_options_dict.get('overview_resampling_method'),
            ndv=common_pog_options_dict.get('ndv'),
            compression=common_pog_options_dict.get('compression', "DEFLATE"),
            blocksize=common_pog_options_dict.get('blocksize', 512),
            verbose=common_pog_options_dict.get('verbose_hb_call', False),
            include_displaced_and_temp_files=common_pog_options_dict.get('include_displaced_and_temp_files', False),
            expand_to_global_extent=common_pog_options_dict.get('expand_to_global_extent', True),
            remove_intermediate_files=common_pog_options_dict.get('remove_intermediate_files', True),
            remove_displaced_files=common_pog_options_dict.get('remove_displaced_files', False),
            variable_class=common_pog_options_dict.get('variable_class'),
            intensive_weighting=common_pog_options_dict.get('intensive_weighting', 'area'),
            observed_area_path=common_pog_options_dict.get('observed_area_path'),
            categorical_none_value=common_pog_options_dict.get('categorical_none_value', 0),
            allow_registration_shift=common_pog_options_dict.get('allow_registration_shift', True),
        )
        output_msg_part = f" (output: {os.path.basename(specific_output_path)})" if specific_output_path else " (output: in-place/default)"
        return (input_file_path, True, f"Successfully processed by {process_name}{output_msg_part}")
    except Exception as e:
        return (input_file_path, False, f"Error in {process_name} for {base_name}: {type(e).__name__} - {e}")


def make_paths_pogs_in_parallel(
    input_folder_or_list,
    include_strings=None,
    include_extensions='.tif',
    exclude_strings=None,
    exclude_extensions=None,
    output_raster_path_suffix=None,
    output_data_type='auto',
    output_arcseconds=None,
    overview_resampling_method=None,
    ndv=None,
    compression="DEFLATE",
    blocksize=512,
    verbose_hb_call=False,
    max_workers=None,
    dry_run=False,
    dont_actually_do_it=False,  # older spelling of dry_run, kept for existing callers
    force_reprocess_pog=False,
    seek_recursively=True, 
    verbose=0,
    verbose_pog_check=0, 
    include_displaced_and_temp_files=False,
    expand_to_global_extent=True,
    remove_intermediate_files=True,
    remove_displaced_files=False,
    variable_class=None,
    intensive_weighting='area',
    observed_area_path=None,
    categorical_none_value=0,
    allow_registration_shift=True,
):
    """
    Lists raster files (input_folder_or_list is a folder to scan, or an explicit list of file paths),
    checks POG status, and processes them in parallel using hazelbean's make_path_pog and starmap.
    Output filenames can be generated by appending a suffix. dry_run lists what would be queued and
    returns simulated results without starting any worker. variable_class, intensive_weighting, categorical_none_value
    and allow_registration_shift are passed to every make_path_pog call (see there); observed_area_path may only be None
    or 'derive' here, since a batch cannot share one companion file.
    """
    if observed_area_path not in (None, 'derive'):
        raise ValueError("make_paths_pogs_in_parallel: observed_area_path must be None or 'derive' (each file derives its own companion).")
    dry_run = dry_run or dont_actually_do_it
    if not include_displaced_and_temp_files:
        # Leftovers of earlier in-place runs (<stem>_displaced_/_copy_/... files) would otherwise be
        # queued and then silently skipped by make_path_pog, reported as successes.
        exclude_strings = ([exclude_strings] if isinstance(exclude_strings, str) else list(exclude_strings or [])) + list(TEMP_NAME_MARKERS)

    if isinstance(input_folder_or_list, (list, tuple)):
        initial_paths_found = [os.path.abspath(i) for i in input_folder_or_list]
        missing = [i for i in initial_paths_found if not os.path.isfile(i)]
        if missing:
            print(f"Error: Input files not found: {missing}")
            return []
        if exclude_strings:
            initial_paths_found = [i for i in initial_paths_found if not any(x in os.path.basename(i) for x in exclude_strings)]
        print(f"Given {len(initial_paths_found)} files.")
    elif not os.path.isdir(os.path.abspath(input_folder_or_list)):
        print(f"Error: Input folder not found: {os.path.abspath(input_folder_or_list)}")
        return []
    elif seek_recursively:
        abs_input_folder = os.path.abspath(input_folder_or_list)
        print(f"Scanning folder: {abs_input_folder}")
    
        initial_paths_found = hb.list_filtered_paths_recursively(
            abs_input_folder,
            include_strings=include_strings,
            include_extensions=include_extensions,
            exclude_strings=exclude_strings,
            exclude_extensions=exclude_extensions,
            return_only_filenames=False
        )
    else:
        abs_input_folder = os.path.abspath(input_folder_or_list)
        print(f"Scanning folder: {abs_input_folder}")
        initial_paths_found = hb.list_filtered_paths_nonrecursively(
            abs_input_folder,
            include_strings=include_strings,
            include_extensions=include_extensions,
            exclude_strings=exclude_strings,
            exclude_extensions=exclude_extensions,
            return_only_filenames=False
        )

    if not initial_paths_found:
        print("No files found matching the initial filter criteria.")
        return []

    print(f"\nFound {len(initial_paths_found)} candidate files. Checking POG status...")

    # Prepare lists for starmap: one for input paths, one for corresponding output paths
    input_paths_for_processing = []
    output_paths_for_processing = []

    for i, path_to_check in enumerate(initial_paths_found):
        base_name = os.path.basename(path_to_check)
        is_pog = (hb.is_path_pog if expand_to_global_extent else hb.is_path_subpog)(path_to_check, verbose=verbose_pog_check)

        if is_pog and not force_reprocess_pog:
            print(f"  {i+1}. Skipping: {base_name} (is POG and not forcing reprocess)")
            continue
        
        action_reason = "(is POG but forcing reprocess)" if is_pog else "(not POG or POG status unknown)"
        print(f"  {i+1}. Queuing: {base_name} {action_reason}")
        
        input_paths_for_processing.append(path_to_check)

        # Determine the specific output path for this task
        if output_raster_path_suffix is not None:
            # Generate output path using the suffix
            specific_output_path = hb.suri(path_to_check, output_raster_path_suffix)
            output_paths_for_processing.append(specific_output_path)
        else:
            # No suffix means output_raster_path for hb.make_path_pog will be None
            # This typically implies in-place modification or hb default output naming.
            output_paths_for_processing.append(None)

    if not input_paths_for_processing:
        print("\nNo files to process after POG check.")
        return []

    print(f"\n{len(input_paths_for_processing)} files will be processed.")
    if dry_run:
        print("  (dry_run: these would be processed)")
        for i_path, o_path in zip(input_paths_for_processing, output_paths_for_processing):
            print(f"    Input: {os.path.basename(i_path)} -> Output: {os.path.basename(o_path) if o_path else 'None (in-place/default)'}")


    # Prepare common options for hb.make_path_pog
    # These are fixed for all tasks and will be passed via partial.
    common_pog_options = {
        'output_data_type': output_data_type,
        'output_arcseconds': output_arcseconds,
        'overview_resampling_method': overview_resampling_method,
        'ndv': ndv,
        'compression': compression,
        'blocksize': blocksize,
        'verbose_hb_call': verbose_hb_call,
        'include_displaced_and_temp_files': include_displaced_and_temp_files,
        'expand_to_global_extent': expand_to_global_extent,
        'remove_intermediate_files': remove_intermediate_files,
        'remove_displaced_files': remove_displaced_files,
        'variable_class': variable_class,
        'intensive_weighting': intensive_weighting,
        'observed_area_path': observed_area_path,
        'categorical_none_value': categorical_none_value,
        'allow_registration_shift': allow_registration_shift,
    }

    # Prepare the arguments for starmap: a list of tuples,
    # where each tuple is (input_path, output_path)
    starmap_iterable = list(zip(input_paths_for_processing, output_paths_for_processing))

    # Use functools.partial to create a new worker function where common_pog_options_dict is pre-filled.
    # The resulting function will expect (input_file_path, specific_output_path) as arguments.
    worker_with_common_opts = partial(
        _worker_make_path_pog_starmap,
        common_pog_options_dict=common_pog_options
    )

    if max_workers is None:
        max_workers = os.cpu_count() - 1
    max_workers = min(max_workers, len(starmap_iterable)) # Don't use more processes than tasks

    results = []
    if max_workers <= 0:
        print("No tasks to process or max_workers is 0 or less. Skipping parallel execution.")
    else:
        print(f"\nStarting parallel processing with {max_workers} worker(s)...")
        if not dry_run:
            with mp.Pool(processes=max_workers) as pool:
                # pool.starmap expects an iterable of argument tuples.
                # For each (in_path, out_path) in starmap_iterable, it effectively calls:
                #   _worker_make_path_pog_starmap(in_path, out_path, common_pog_options_dict=common_pog_options)
                results = pool.starmap(worker_with_common_opts, starmap_iterable)
        else:
            print(f"\nSKIPPING ACTUAL PROCESSING due to dry_run=True.")
            # Simulate results if needed for testing downstream logic
            for in_path, out_path in starmap_iterable:
                results.append((in_path, True, f"Simulated success by DUMMY_PROCESS (output: {os.path.basename(out_path) if out_path else 'None'})"))


    print("\n--- Processing Summary ---")
    success_count = 0
    failure_count = 0
    for file_path, success, message in results: # Assuming worker returns this tuple
        base_name = os.path.basename(file_path)
        if success:
            print(f"SUCCESS: {base_name} - {message}")
            success_count += 1
        else:
            print(f"FAILURE: {base_name} - {message}")
            failure_count += 1
    
    print(f"\nFinished processing. {success_count} successful, {failure_count} failed.")
    return results
 
  
# Name fragments make_path_pog inserts into the files it leaves beside an input (see the skip check in make_path_pog).
# The keyword list itself lives in os_utils, beside hb.remove_temp_files_recursively which cleans them up.
TEMP_NAME_MARKERS = tuple('_' + k + '_' for k in hb.TEMP_FILE_KEYWORDS)


def _infer_variable_class(data_type):
    """The class assumed for a raster that declares none: categorical for integer types, covariate for floating point.
    Those are the two classes that make no exactness claim, and they reproduce the pre-specification behaviour (mode
    overviews for integers, mean overviews over valid cells for floats)."""
    return 'categorical' if _is_integer_gdal_type(data_type) else 'covariate'


def _write_cog_with_pyramid_overviews(current_path, output_raster_path, overview_levels, overview_resampling_method, output_data_type, ndv, compression, blocksize, verbose=False,
                                      variable_class=None, intensive_weighting='area', denominator=None, pog_metadata=None):
    """The POG finishing sequence shared by make_path_pog and the subpog writers. current_path is modified in place.

    Records the POG metadata of the variable class (POG_VARIABLE_CLASS; for an intensive raster POG_INTENSIVE_WEIGHTING
    and POG_DENOMINATOR; any POG_OBSERVED_AREA / POG_REGISTRATION_SHIFT given in pog_metadata) and AREA_OR_POINT=Area,
    applies the nodata declaration of the class (the per-type value for a covariate, none otherwise; the values must
    already follow it, see _apply_pog_nodata_rule), computes exact statistics, builds the internal overviews at
    overview_levels by the class rule (extensive sums and intensive area-weighted means written directly; categorical
    mode and covariate mean by GDAL), then copies through the COG driver with those overviews and no others.

    denominator is the token ha_per_cell or the absolute path of the observed-area POG an intensive raster is weighted by."""
    if variable_class is None:
        variable_class = _infer_variable_class(output_data_type)
    if variable_class not in POG_VARIABLE_CLASSES:
        raise ValueError(f'variable_class must be one of {POG_VARIABLE_CLASSES}, not {variable_class!r}.')
    if intensive_weighting not in ('area', 'none'):
        raise ValueError(f"intensive_weighting must be 'area' or 'none', not {intensive_weighting!r}.")
    if overview_resampling_method is not None and variable_class in ('extensive', 'intensive'):
        raise ValueError(f'The overviews of an {variable_class} POG are fixed by its class (D.2.4); overview_resampling_method cannot be set.')

    # Open the source raster in UPDATE MODE so it writes the overviews as internal
    if verbose:
        hb.log(f"Opening {current_path} for overview building.")
    src_ds = gdal.OpenEx(current_path, gdal.GA_Update, open_options=["IGNORE_COG_LAYOUT_BREAK=YES"])
    if not src_ds:
        raise ValueError(f"Unable to open raster: {current_path}")

    metadata = {k: v for k, v in (src_ds.GetMetadata() or {}).items() if k not in POG_METADATA_KEYS}
    metadata['AREA_OR_POINT'] = 'Area'
    metadata['POG_VARIABLE_CLASS'] = variable_class
    if variable_class == 'intensive':
        metadata['POG_INTENSIVE_WEIGHTING'] = intensive_weighting
        if intensive_weighting == 'area':
            metadata['POG_DENOMINATOR'] = 'ha_per_cell' if denominator in (None, 'ha_per_cell') else _pog_reference_for(output_raster_path, denominator)
    metadata.update({k: v for k, v in (pog_metadata or {}).items() if v is not None})
    src_ds.SetMetadata(metadata)
    if not src_ds.GetProjection():
        src_ds.SetProjection(hb.wgs_84_wkt)
    for i in range(1, src_ds.RasterCount + 1):
        if variable_class == 'covariate':
            src_ds.GetRasterBand(i).SetNoDataValue(hb.no_data_values_by_gdal_type[output_data_type][0])
        elif src_ds.GetRasterBand(i).GetNoDataValue() is not None:
            src_ds.GetRasterBand(i).DeleteNoDataValue()

    # Exact statistics, computed on the update-mode dataset so they are written INTO the TIFF. A read-only
    # compute (gdalinfo -stats, or ComputeStatistics on a read-only open) lands in a .aux.xml sidecar, which
    # is invisible to the COG copy below whenever GDAL_DISABLE_READDIR_ON_OPEN=EMPTY_DIR is set.
    if verbose:
        hb.log(f"Computing exact statistics for {current_path}.")
    stats_by_band = {i: src_ds.GetRasterBand(i).ComputeStatistics(False) for i in range(1, src_ds.RasterCount + 1)}

    # Remove existing overviews (if any), then build the rung's chain by the class rule.
    src_ds.BuildOverviews(None, [])
    if overview_levels:
        if verbose:
            hb.log(f"Building {variable_class} overviews for {current_path} with levels {overview_levels}...")
        if variable_class in ('extensive', 'intensive'):
            src_ds.BuildOverviews('NONE', overview_levels)  # allocate only; the levels are written exactly below
            _write_class_overviews(src_ds, overview_levels, variable_class, intensive_weighting, denominator)
        else:
            method = overview_resampling_method or ('mode' if variable_class == 'categorical' else 'average')
            src_ds.BuildOverviews(method.upper(), overview_levels, hb.make_gdal_callback(f'Building overviews for {current_path}'))

    # Re-apply the statistics after overview building (BuildOverviews can drop band metadata), then close.
    for i, (stat_min, stat_max, stat_mean, stat_std) in stats_by_band.items():
        band = src_ds.GetRasterBand(i)
        for key, value in (('STATISTICS_MINIMUM', stat_min), ('STATISTICS_MAXIMUM', stat_max), ('STATISTICS_MEAN', stat_mean), ('STATISTICS_STDDEV', stat_std)):
            band.SetMetadataItem(key, str(value))
        band.SetMetadataItem('STATISTICS_APPROXIMATE', 'NO')
    del src_ds

    # Reopen it to use it as a copy target
    if verbose:
        hb.log(f"Reopening {current_path} for COG creation...")
    src_ds = gdal.OpenEx(current_path, gdal.GA_ReadOnly)

    # The COG driver copies the overviews built above and adds none of its own: left to itself it inserts dyadic
    # 2, 4, 8... levels whenever a source larger than a block carries none (the top rung, or a small subpog extent).
    creation_options = [
        f"COMPRESS={compression}",
        f"BLOCKSIZE={blocksize}",
        f"BIGTIFF=YES",
        f"OVERVIEW_COMPRESS={compression}",
        "OVERVIEWS=FORCE_USE_EXISTING" if overview_levels else "OVERVIEWS=NONE",
    ]

    cog_driver = gdal.GetDriverByName('COG')
    if cog_driver is None:
        raise RuntimeError("COG driver is not available in this GDAL build.")

    if verbose:
        hb.log(f"Creating COG at {output_raster_path}. Abs path: {os.path.abspath(output_raster_path)}")

    dst_ds = cog_driver.CreateCopy(
        output_raster_path,
        src_ds,
        strict=0,  # set to 1 to fail on any “creation option not recognized”
        options=creation_options,
        callback=hb.make_gdal_callback(f'cog_driver creating copy at {output_raster_path}')
    )

    dst_ds = None


def is_path_subpog(path, check_tiled=True, full_check=False, raise_exceptions=False, verbose=False):
    """A subpog is a POG in every respect except extent: pyramid-aligned sub-extent (hb.is_path_subglobal_pyramid) and a valid COG."""
    return hb.is_path_subglobal_pyramid(path, verbose=verbose) and hb.is_path_cog(path, check_tiled=check_tiled, full_check=full_check, raise_exceptions=raise_exceptions, verbose=verbose)


def write_subpog_from_pog_window(pog_path, bb, output_path, compression='DEFLATE', blocksize=512, verbose=False):
    """Cut bb out of a POG and write it as a subpog at output_path. bb must be pyramid-aligned at the POG's resolution
    (snap it with hb.snap_bb_to_pyramid first); the overview chain is truncated to the levels that divide bb. The
    variable class and its POG metadata carry over, with companion paths re-pointed from output_path's folder."""
    arcseconds = hb.get_cell_size_from_path_in_arcseconds(pog_path, force_to_pyramid=True)
    output_data_type = hb.get_datatype_from_uri(pog_path)
    meta = get_pog_metadata(pog_path)
    variable_class = meta.get('POG_VARIABLE_CLASS') or _infer_variable_class(output_data_type)
    ndv = hb.no_data_values_by_gdal_type[output_data_type][0] if variable_class == 'covariate' else None
    denominator = _resolve_pog_reference(pog_path, meta.get('POG_DENOMINATOR'))
    observed_area = _resolve_pog_reference(pog_path, meta.get('POG_OBSERVED_AREA'))
    stem = os.path.splitext(os.path.basename(output_path))[0]
    temp_path = hb.temp('.tif', stem + '_translate', True, tag_along_file_extensions=['.aux.xml'])  # in hb.get_temp_dir(), so tile folders stay clean
    gdal.Translate(temp_path, pog_path, projWin=[bb[0], bb[3], bb[2], bb[1]], noData=ndv if ndv is not None else 'none', creationOptions=hb.globals.PRECOG_GTIFF_CREATION_OPTIONS_LIST)
    _write_cog_with_pyramid_overviews(temp_path, output_path, hb.get_pyramid_overview_levels_for_bb(arcseconds, bb), None, output_data_type, ndv, compression, blocksize, verbose,
                                      variable_class=variable_class, intensive_weighting=meta.get('POG_INTENSIVE_WEIGHTING', 'area'), denominator=denominator,
                                      pog_metadata={'POG_OBSERVED_AREA': _pog_reference_for(output_path, observed_area) if observed_area else None,
                                                    'POG_REGISTRATION_SHIFT': meta.get('POG_REGISTRATION_SHIFT')})
    return output_path


def _tileset_stem(pog_path, arcseconds):
    """The dataset stem of a POG for naming its tiles: 'lulc_esa_2020' for lulc_esa_2020_10sec.tif (the rung is re-added)."""
    stem = os.path.splitext(os.path.basename(pog_path))[0]
    suffix = f'_{hb.arcseconds_to_token(arcseconds)}sec'
    return stem[:-len(suffix)] if stem.endswith(suffix) else stem


def tile_pog_to_tileset(pog_path, output_dir=None, tile_degrees=None, skip_empty_tiles=True, verbose=False):
    """Cut a global POG into corner-named subpog tiles plus a VRT that presents them as the global raster again.

    Tiles go in output_dir (default <pog dir>/<stem>_<rung>sec_<deg>deg/) named <stem>_<rung>sec_<corner>_<deg>_<deg>.tif by
    hb.get_tile_filename; the VRT is written beside that folder with the same name and .vrt. tile_degrees defaults to
    hb.pyramid_tile_degrees for the POG's resolution and must divide 180 and be a whole number of cells. With
    skip_empty_tiles, tiles that hold nothing (all zero, or all nodata for a covariate) are not written; the VRT reads them
    as zero (or nodata). Returns the VRT path.
    """
    if not is_path_pog(pog_path, verbose=verbose):
        raise ValueError(f'Not a POG, refusing to tile it: {pog_path}')
    arcseconds = hb.get_cell_size_from_path_in_arcseconds(pog_path, force_to_pyramid=True)
    if tile_degrees is None:
        tile_degrees = hb.pyramid_tile_degrees[arcseconds]
    if tile_degrees is None:
        raise ValueError(f'{hb.arcseconds_to_token(arcseconds)} arcseconds is not a tiled resolution (see hb.pyramid_tile_degrees); pass tile_degrees to force a tiling.')
    stem = _tileset_stem(pog_path, arcseconds)
    tileset_name = f'{stem}_{hb.arcseconds_to_token(arcseconds)}sec_{int(tile_degrees)}deg'
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(pog_path)), tileset_name)
    os.makedirs(output_dir, exist_ok=True)
    ds = gdal.Open(pog_path); band = ds.GetRasterBand(1)
    empty = band.GetNoDataValue() if band.GetNoDataValue() is not None else 0
    res = hb.pyramid_compatible_resolutions[arcseconds]
    n_written = 0
    for corner in hb.list_tile_corner_strings(tile_degrees):
        bb = hb.get_tile_bb_from_corner_string(corner, tile_degrees)
        if skip_empty_tiles:
            xoff, yoff, size = int(round((bb[0] + 180) / res)), int(round((90 - bb[3]) / res)), int(round(tile_degrees / res))
            if np.all(band.ReadAsArray(xoff, yoff, size, size) == empty):
                continue
        write_subpog_from_pog_window(pog_path, bb, os.path.join(output_dir, hb.get_tile_filename(stem, arcseconds, corner, tile_degrees)), verbose=verbose)
        n_written += 1
    ds = None
    if verbose:
        hb.log(f'Wrote {n_written} tiles to {output_dir}')
    return build_pog_tileset_vrt(output_dir, os.path.join(os.path.dirname(output_dir), tileset_name + '.vrt'))


def build_pog_tileset_vrt(tile_dir, vrt_path=None):
    """Index the corner-named tiles in tile_dir as one global raster: a VRT with the exact global geotransform and relative
    source paths, so the folder plus VRT move together. A missing tile reads as zero, which is what it holds; for a
    covariate tile set the VRT declares the per-type nodata instead, so a missing tile reads as nodata. Returns vrt_path."""
    tiles = sorted(i for i in hb.list_filtered_paths_nonrecursively(tile_dir, include_extensions='.tif') if _is_tile_filename(i))
    if not tiles:
        raise ValueError(f'No corner-named tiles (<stem>_<rung>sec_<corner>_<height>_<width>.tif) in {tile_dir}')
    stem, arcseconds, _, tile_degrees, _ = hb.parse_tile_filename(tiles[0])
    res = hb.pyramid_compatible_resolutions[arcseconds]
    ndv = hb.get_ndv_from_path(tiles[0])
    if vrt_path is None:
        vrt_path = os.path.join(os.path.dirname(os.path.abspath(tile_dir)), f'{stem}_{hb.arcseconds_to_token(arcseconds)}sec_{int(tile_degrees)}deg.vrt')
    nodata_options = dict(VRTNodata=ndv, srcNodata=ndv) if ndv is not None else {}
    gdal.BuildVRT(vrt_path, tiles, options=gdal.BuildVRTOptions(outputBounds=(-180, -90, 180, 90), xRes=res, yRes=res, **nodata_options)).FlushCache()
    return vrt_path


def _is_tile_filename(path):
    try:
        hb.parse_tile_filename(path); return True
    except ValueError:
        return False


def is_path_pog_tileset(vrt_path, verbose=False):
    """True if vrt_path presents a set of subpog tiles as the global raster: global pyramid geotransform on the VRT, every
    source a corner-named tile of one dataset, rung and edge whose extent matches its name, and every tile a subpog."""
    ds = gdal.Open(vrt_path)
    if ds is None:
        return False
    sources = [i for i in ds.GetFileList()[1:]]
    gt = ds.GetGeoTransform(); ds = None
    if not sources:
        if verbose: hb.log('Not a POG tileset: the VRT has no sources: ' + str(vrt_path))
        return False
    try:
        stem, arcseconds, _, tile_height, tile_width = hb.parse_tile_filename(sources[0])
    except ValueError as e:
        if verbose: hb.log(f'Not a POG tileset: {e}')
        return False
    expected = hb.pyramid_compatible_geotransforms[arcseconds]
    if any(abs(a - b) > 1e-9 for a, b in zip(gt, expected)):
        if verbose: hb.log(f'Not a POG tileset: VRT geotransform {gt} is not the global {expected}: {vrt_path}')
        return False
    for tile in sources:
        tile_stem, sec, corner, height, width = hb.parse_tile_filename(tile)
        bb = hb.get_tile_bb_from_corner_string(corner, height, width)
        tgt = hb.get_geotransform_path(tile); shape = hb.get_shape_from_dataset_path(tile)
        if (tile_stem, sec, height, width) != (stem, arcseconds, tile_height, tile_width) or abs(tgt[0] - bb[0]) > 1e-9 or abs(tgt[3] - bb[3]) > 1e-9 \
                or abs(shape[1] * tgt[1] - width) > 1e-6 or abs(shape[0] * -tgt[5] - height) > 1e-6:
            if verbose: hb.log(f'Not a POG tileset: {tile} is not a tile of {stem} at this rung and edge covering the extent its name claims ({bb})')
            return False
        if not is_path_subpog(tile, verbose=verbose):
            if verbose: hb.log(f'Not a POG tileset: {tile} is not a subpog')
            return False
    return True


def _explain_unsupported_resolution(input_raster_path):
    """Error text for a raster whose output resolution make_path_pog cannot infer: says whether the CRS is WGS84,
    what the native cell size is in arcseconds, which supported resolution to pass as output_arcseconds, and where."""
    from osgeo import osr
    ds = gdal.Open(input_raster_path)
    gt = ds.GetGeoTransform()
    srs = osr.SpatialReference(wkt=ds.GetProjection()) if ds.GetProjection() else None
    ds = None
    crs_name = (srs.GetName() if srs is not None else None) or ''
    if crs_name in ('', 'unknown') and srs is not None:
        crs_name = srs.GetAttrValue('PROJECTION') or 'unknown'
    supported = sorted(k for k in hb.pyramid_compatible_resolutions if isinstance(k, float))
    supported_text = ', '.join(hb.arcseconds_to_token(k) for k in supported)
    meters_per_arcsecond = 2 * np.pi * 6378137 / (360 * 3600)  # equatorial

    if srs is None or srs.ExportToWkt() == '':
        crs_text = 'has no projection defined'
        native_arcseconds = None
    elif srs.IsGeographic():
        is_wgs84 = srs.GetAuthorityCode(None) == '4326' or 'WGS 84' in (srs.GetName() or '')
        crs_text = f"is in geographic CRS {crs_name}" + ('' if is_wgs84 else ', which is not WGS84 (EPSG:4326)')
        native_arcseconds = abs(gt[1]) * 3600.0
        cell_text = f"{abs(gt[1]):.8g} degrees ({native_arcseconds:.4g} arcseconds)"
    else:
        cell_meters = abs(gt[1]) * srs.GetLinearUnits()
        native_arcseconds = cell_meters / meters_per_arcsecond
        crs_text = f"is in projected CRS {crs_name}, not WGS84 (EPSG:4326)"
        cell_text = f"{abs(gt[1]):.8g} {srs.GetLinearUnitsName()} ({native_arcseconds:.4g} arcseconds at the equator)"

    lines = [f"make_path_pog cannot infer an output resolution for {input_raster_path}.",
             f"The raster {crs_text}" + (f" and its cell size is {cell_text}, which is not one of the supported pyramid "
                                         f"resolutions ({supported_text} arcseconds)." if native_arcseconds is not None else '.')]
    if native_arcseconds is not None:
        coarser = [k for k in supported if k >= native_arcseconds * 0.999]
        suggested = hb.arcseconds_to_token(coarser[0] if coarser else supported[-1]).replace('-', '/')  # a Python literal: 1/3, not 1-3
        finer = [k for k in supported if k < native_arcseconds * 0.999]
        lines.append(f"Suggested output_arcseconds={suggested}: the closest supported resolution at or coarser than the native "
                     f"cell, so no detail is invented." + (f" Use {hb.arcseconds_to_token(finer[-1]).replace('-', '/')} to resample finer instead." if finer else ''))
    else:
        suggested = 30
        lines.append(f"Fix the projection first, then pass output_arcseconds explicitly (for example {suggested}).")
    lines.append(f"Pass it as the output_arcseconds argument: hb.make_path_pog(path, output_arcseconds={suggested}) for one file, or "
                 f"hb.make_paths_pogs_in_parallel(paths, output_arcseconds={suggested}) for a batch (it applies to every file in "
                 f"that call, so give files needing a different resolution their own call). The input is reprojected to "
                 f"WGS84 and resampled to that resolution on the way." if native_arcseconds is not None else
                 f"Pass it as the output_arcseconds argument of hb.make_path_pog or hb.make_paths_pogs_in_parallel.")
    return ' '.join(lines)


def write_pyramid_frame_raster(output_path, arcseconds, bb=None, data_type=None, ndv=None):
    """Write a sparse (all-nodata, near-zero bytes) raster with the pyramid geotransform at arcseconds over bb (global if None).

    Used as the geometry-only match for resampling onto the pyramid: any rung, spine or side, any aligned extent,
    without needing a data file at that rung. Returns output_path."""
    res = hb.pyramid_compatible_resolutions[arcseconds]
    if bb is None:
        bb = [-180.0, -90.0, 180.0, 90.0]
    cols, rows = int(round((bb[2] - bb[0]) / res)), int(round((bb[3] - bb[1]) / res))
    if data_type is None:
        data_type = gdal.GDT_Byte
    # Large blocks: a sparse file costs only its tile directory, and at 512-pixel tiles a global 3/10-second frame
    # would carry 36 million tile entries (1.7 GB); at 8192-pixel tiles it is a few megabytes.
    ds = gdal.GetDriverByName('GTiff').Create(output_path, cols, rows, 1, data_type, options=['TILED=YES', 'BLOCKXSIZE=8192', 'BLOCKYSIZE=8192', 'SPARSE_OK=TRUE', 'BIGTIFF=YES'])
    ds.SetGeoTransform((bb[0], res, 0.0, bb[3], 0.0, -res))
    ds.SetProjection(hb.wgs_84_wkt)
    if ndv is not None:
        ds.GetRasterBand(1).SetNoDataValue(ndv)
    ds = None
    return output_path


def _native_rung(path):
    """(arcseconds, aligned) for a geographic raster whose cell is within the snapping tolerance of a rung, else (None, False).
    aligned: the cell edges fall on that rung's canonical grid lines from (-180, 90)."""
    ds = gdal.Open(path)
    srs = ds.GetSpatialRef()
    gt = ds.GetGeoTransform()
    ds = None
    if srs is not None and not srs.IsGeographic():
        return None, False
    arcseconds = None
    for k, (low, high) in hb.pyramid_compatible_resolution_bounds.items():
        if isinstance(k, float) and low <= gt[1] <= high:
            arcseconds = k
    if arcseconds is None:
        return None, False
    res = hb.pyramid_compatible_resolutions[arcseconds]
    cells_x, cells_y = (gt[0] + 180) / res, (90 - gt[3]) / res
    aligned = abs(-gt[5] - res) <= res * 1e-6 and gt[2] == 0 and gt[4] == 0 and abs(cells_x - round(cells_x)) < 1e-6 and abs(cells_y - round(cells_y)) < 1e-6
    return arcseconds, aligned


def make_path_pog(input_raster_path,
                  output_raster_path=None,
                  output_data_type=None,
                  output_arcseconds=None,
                  ndv=None,
                  overview_resampling_method=None,
                  compression="DEFLATE",
                  blocksize=512,
                  force_rewrite=False,
                  value_reclassification_dict=None,
                  ndv_above=None,
                  ndv_below=None,
                  remove_intermediate_files=True,
                  remove_displaced_files=False,
                  verbose=False,
                  include_displaced_and_temp_files=False,
                  expand_to_global_extent=True,
                  variable_class=None,
                  intensive_weighting='area',
                  observed_area_path=None,
                  categorical_none_value=0,
                  allow_registration_shift=True):

    """ Create a POG (pyramidal cog) from input_raster_path. Writes in-place if output_raster_path is not set. Follows the
    steps of the specification (the paper's Appendix D.4; pogs.qmd).

    variable_class declares what the values are, which fixes how they aggregate and how nodata is carried:
    'extensive' (hectares, tonnes, counts: sum overviews, integers promoted to Int64), 'intensive' (proportions,
    densities, rates: area-weighted mean overviews, or unweighted with intensive_weighting='none'), 'categorical'
    (labels: mode overviews, for display) or 'covariate' (elevation, temperature: mean overviews over valid cells, per-type
    nodata). If None, the class the input declares (POG_VARIABLE_CLASS) is kept; an input declaring none is taken as
    categorical (integer types) or covariate (floats), with a log line, since the class must be declared, not guessed.

    Extensive, intensive and categorical POGs carry no nodata value: nodata cells become zero (categorical_none_value for
    a categorical raster) and the declaration is dropped. When the input's nodata marks UNOBSERVED rather than empty
    cells, pass observed_area_path: 'derive' writes the companion observed-area POG (hectares observed per cell, from
    the nodata mask) as <output stem>_observed_area.tif beside the output; a path attaches an existing one. An intensive
    raster is then weighted by the observed area instead of ha_per_cell.

    expand_to_global_extent=True (default) makes a POG: a non-global input is placed on the global grid and padded.
    expand_to_global_extent=False makes a SUBPOG instead: the input keeps its footprint, snapped outward to the pyramid
    grid at the output resolution (hb.snap_bb_to_pyramid), with the overview chain truncated to the levels that divide
    that extent. Both are no-ops on an input that already is the requested kind.

    output_arcseconds, if given, sets the rung of the output explicitly. Required when the input is not close to any
    rung; also the way to convert deliberately between rungs. Reaching a coarser rung aggregates by the class rule:
    exactly (block sums, area-weighted for intensive) when the input sits aligned on a rung that divides the target,
    otherwise by one GDAL resample (sum, average, mode). A point-registered input whose samples fall on canonical grid
    lines (SRTM, NASADEM) enters by the half-cell registration shift instead of a resample (allow_registration_shift)."""

    # Check if input exists
    if not hb.path_exists(input_raster_path, verbose=verbose):
        raise FileNotFoundError(f"Input raster does not exist: {input_raster_path} at abs path {hb.path_abs(input_raster_path)}")

    # An in-place conversion leaves the original beside the POG as <name>_displaced_<stamp>.tif, and its
    # intermediates as <name>_copy_<stamp>.tif etc. (kept when remove_intermediate_files=False, or after a
    # crash). A directory walk that reruns would otherwise poggerize those too; skip them by default.
    if any(marker in os.path.basename(input_raster_path) for marker in TEMP_NAME_MARKERS) and not include_displaced_and_temp_files:
        if verbose:
            hb.log(f"Skipping displaced/temp file (pass include_displaced_and_temp_files=True to convert it): {input_raster_path}")
        return

    if output_arcseconds is not None and output_arcseconds not in hb.pyramid_compatible_resolutions:
        raise ValueError(f"output_arcseconds {output_arcseconds} is not a supported pyramid resolution. Supported values (arcseconds): "
                         f"main rungs {', '.join(hb.arcseconds_to_token(k) for k in hb.pyramid_main_arcseconds)}; "
                         f"side rungs {', '.join(hb.arcseconds_to_token(k) for k in hb.pyramid_side_arcseconds)} (fractions written p-q).")
    if variable_class is not None and variable_class not in POG_VARIABLE_CLASSES:
        raise ValueError(f'variable_class must be one of {POG_VARIABLE_CLASSES}, not {variable_class!r}.')

    # Do a fast check to see if it's pog (or, when not expanding, subpog).
    is_path_requested_kind = is_path_pog if expand_to_global_extent else is_path_subpog
    is_path_requested_pyramid = hb.is_path_global_pyramid if expand_to_global_extent else hb.is_path_subglobal_pyramid
    needs_censoring = ndv_above is not None or ndv_below is not None
    if not is_path_requested_pyramid(input_raster_path, verbose):
        if verbose:
            hb.log(f"Raster is not a {'global' if expand_to_global_extent else 'sub-global'} pyramid. {input_raster_path}")
    else:
        if needs_censoring:
            stats_by_band = hb.get_stats_from_geotiff(input_raster_path)
            needs_censoring = (ndv_above is not None and ndv_above < stats_by_band[1]['max']) or (ndv_below is not None and ndv_below > stats_by_band[1]['min'])
            if needs_censoring and verbose:
                hb.log(f"Raster has values outside the ndv_above / ndv_below thresholds. {input_raster_path}")

        needs_reclassification = value_reclassification_dict is not None
        needs_class_change = variable_class is not None and get_pog_metadata(input_raster_path).get('POG_VARIABLE_CLASS') != variable_class

        # A requested output_arcseconds different from the input's resolution means the input
        # cannot be accepted as-is even if it already validates as a POG.
        needs_resolution_change = False
        if output_arcseconds is not None:
            input_resolution = hb.determine_pyramid_resolution(input_raster_path)
            if input_resolution is None or hb.pyramid_compatible_resolution_to_arcseconds[input_resolution] != float(output_arcseconds):
                needs_resolution_change = True

        # Do a full check to see if the input is already a POG. If so, skip it.
        if not (force_rewrite or needs_censoring or needs_reclassification or needs_resolution_change or needs_class_change) and is_path_requested_kind(input_raster_path, verbose=verbose):
            if verbose:
                hb.log(f"Raster is already a POG: {input_raster_path}")
            return

    # Get the resolution of the output: explicit if output_arcseconds was given, otherwise snapped from the input.
    # Done before any copying so an unsupported input fails without first duplicating it.
    if output_arcseconds is not None:
        arcseconds = float(hb.pyramid_compatible_resolution_to_arcseconds[hb.pyramid_compatible_resolutions[output_arcseconds]])
        degrees = hb.pyramid_compatible_resolutions[output_arcseconds]
    else:
        try:
            degrees = hb.get_cell_size_from_path(input_raster_path, force_to_pyramid=True)
            arcseconds = hb.get_cell_size_from_path_in_arcseconds(input_raster_path, force_to_pyramid=True)
        except ValueError as e:
            raise ValueError(_explain_unsupported_resolution(input_raster_path)) from e

    # Make a local copy at a temp file to process on to avoid corrupting the original.
    # Intermediates are named <input stem>_<step>_<stamp>.tif so they sort beside their source.
    input_dir = os.path.dirname(input_raster_path)
    input_stem = os.path.splitext(os.path.basename(input_raster_path))[0]
    def intermediate(step, folder=input_dir):
        path = hb.temp('.tif', input_stem + '_' + step, remove_intermediate_files, folder=folder, tag_along_file_extensions=['.aux.xml'])
        intermediate_paths.append(path)
        return path
    intermediate_paths = []  # deleted at the end when remove_intermediate_files

    # Ensure output directory exists
    try:
        os.makedirs(input_dir, exist_ok=True)
    except:
        pass

    input_data_type = hb.get_datatype_from_uri(input_raster_path)
    if output_data_type is None or output_data_type == 'auto':
        output_data_type = input_data_type

    declared = get_pog_metadata(input_raster_path)
    if variable_class is None:
        variable_class = declared.get('POG_VARIABLE_CLASS')
        if variable_class is None:
            variable_class = _infer_variable_class(output_data_type)
            hb.log(f"make_path_pog: {input_raster_path} declares no variable class; taking it as {variable_class} from its data type. "
                   f"Pass variable_class ('extensive', 'intensive', 'categorical' or 'covariate'): it fixes the aggregation rule and the nodata convention.")
        if variable_class == 'intensive' and 'POG_INTENSIVE_WEIGHTING' in declared:
            intensive_weighting = declared['POG_INTENSIVE_WEIGHTING']
    if intensive_weighting not in ('area', 'none'):
        raise ValueError(f"intensive_weighting must be 'area' or 'none', not {intensive_weighting!r}.")
    if variable_class == 'extensive' and _is_integer_gdal_type(output_data_type) and output_data_type != gdal.GDT_Int64:
        if verbose:
            hb.log(f"Promoting the integer extensive raster {input_raster_path} to Int64 so its sums cannot overflow at the top rung.")
        output_data_type = gdal.GDT_Int64
    ndv = hb.no_data_values_by_gdal_type[output_data_type][0]  # the per-type nodata used while processing (and kept for a covariate)

    if os.path.splitext(input_raster_path)[1].lower() == '.vrt' or output_data_type != input_data_type:
        # A tile-set VRT is read through into one GeoTIFF; a type change is made on the same pass.
        current_path = intermediate('translate')
        if verbose:
            hb.log(f"Translating {input_raster_path} to {current_path} as data type {output_data_type}.")
        gdal.Translate(current_path, input_raster_path, outputType=output_data_type, creationOptions=hb.globals.PRECOG_GTIFF_CREATION_OPTIONS_LIST,
                       callback=hb.make_gdal_callback(f"Translating {hb.path_filename(input_raster_path)} to {current_path}."))
    else:
        current_path = intermediate('copy')
        if verbose:
            hb.log(f"Data type is already {output_data_type} for {input_raster_path}, so just copying to {current_path}.")
        hb.path_copy(input_raster_path, current_path) # Can just copy it direclty without accessing the raster.

    # A point-registered input on canonical grid lines enters by the half-cell registration shift (Appendix G.4).
    registration_shift = None
    if allow_registration_shift:
        shifted_path = intermediate('shift')
        if _write_registration_shifted_copy(current_path, shifted_path, arcseconds):
            registration_shift = POG_REGISTRATION_SHIFT_VALUE
            current_path = shifted_path
            if verbose:
                hb.log(f"Applied the registration shift {registration_shift} (cells) to the point-registered {input_raster_path}.")

    original_output_raster_path = output_raster_path
    if output_raster_path is None:
        output_raster_path = hb.temp('.tif', input_stem + '_pog', remove_at_exit=False, folder=os.path.dirname(input_raster_path), tag_along_file_extensions=['.aux.xml'])
    final_raster_path = original_output_raster_path or input_raster_path

    # POG SPECIFIC DIFFERENCE HERE: Handles the case where the raster is not global.
    gt = hb.get_geotransform_path(current_path)
    gt_pyramid = hb.pyramid_compatible_geotransforms[arcseconds]
    input_shape = hb.get_shape_from_dataset_path(current_path)
    input_bb = [gt[0], gt[3] + input_shape[0] * gt[5], gt[0] + input_shape[1] * gt[1], gt[3]]
    if expand_to_global_extent:
        target_bb = [-180.0, -90.0, 180.0, 90.0]
        needs_reframing = gt != gt_pyramid
        if needs_reframing and (verbose or gt[1] == degrees):
            hb.log(f"make_path_pog: expanding {input_raster_path} from extent {[round(i, 6) for i in input_bb]} to the global "
                   f"{int(round(360 / degrees))} x {int(round(180 / degrees))} grid at {hb.arcseconds_to_token(arcseconds)} arcseconds (pass expand_to_global_extent=False for a subpog).")
    else:
        target_bb = hb.snap_bb_to_pyramid(input_bb, arcseconds)
        needs_reframing = abs(gt[1] - degrees) > 1e-12 or any(abs(a - b) > 1e-9 for a, b in zip(input_bb, target_bb))
        if verbose:
            hb.log(f"make_path_pog: subpog extent {target_bb} (input extent {[round(i, 6) for i in input_bb]})")

    # Where the nodata rule will need the observed-area companion, and whether aggregation already produced it.
    derive_observed_area = observed_area_path == 'derive'
    observed_area_temp_path = intermediate('observed_area') if derive_observed_area else None
    observed_area_done = False

    if needs_reframing:
        native_arcseconds, native_aligned = _native_rung(current_path)
        coarser = hb.get_cell_size_from_path(current_path) < hb.pyramid_compatible_resolution_bounds[arcseconds][0]
        has_nodata = hb.get_ndv_from_path(current_path) is not None
        # Padding a raster with no nodata (a POG, say) fills with zero, which is what an empty cell holds; declaring a
        # nodata value there instead would turn real cells holding that value into holes.
        frame_ndv = ndv if (has_nodata or variable_class == 'covariate') else None
        exact_aggregation = (coarser and variable_class in ('extensive', 'intensive') and native_arcseconds is not None and native_aligned
                             and hb.pyramids._divides(native_arcseconds, arcseconds))
        if exact_aggregation:
            # Place the input on its own rung over the target extent (exact: aligned cells are copied), then block-aggregate.
            native_frame_path = intermediate('native_frame', hb.get_temp_dir())
            write_pyramid_frame_raster(native_frame_path, native_arcseconds, target_bb, output_data_type, frame_ndv)
            native_path = intermediate('native')
            hb.resample_to_match(current_path, native_frame_path, native_path, resample_method='near', output_data_type=output_data_type, src_ndv=None, ndv=frame_ndv,
                                 compress=True, ensure_fits=False, gtiff_creation_options=hb.globals.PRECOG_GTIFF_CREATION_OPTIONS_LIST,
                                 calc_raster_stats=False, add_overviews=False, bb_override=target_bb, verbose=False)
            aggregated_path = intermediate('aggregate')
            if verbose:
                hb.log(f"Aggregating {native_path} exactly from {hb.arcseconds_to_token(native_arcseconds)} to {hb.arcseconds_to_token(arcseconds)} arcseconds as {variable_class}.")
            _aggregate_on_lattice(native_path, aggregated_path, arcseconds, variable_class, intensive_weighting, output_data_type, observed_area_temp_path)
            observed_area_done = derive_observed_area
            current_path = aggregated_path
        else:
            if coarser:
                resample_method = {'extensive': 'sum', 'intensive': 'average', 'categorical': 'mode', 'covariate': 'average'}[variable_class]
            elif native_aligned and native_arcseconds == arcseconds:
                resample_method = 'near'  # already on this rung's grid: a copy onto the new extent
            elif variable_class == 'extensive':
                resample_method = 'sum'  # conserves the total when cells are split or regridded
            elif variable_class == 'categorical' or _is_integer_gdal_type(output_data_type):
                resample_method = 'near'
            else:
                resample_method = 'bilinear'
            # The target frame is synthesized from the pyramid tables (a sparse raster with the exact pyramid
            # geotransform and WGS84) rather than fetched: resample_to_match only reads geometry from its match,
            # and a fetched raster cannot exist for every rung (a global 3/10-arcsecond one would be 9 trillion cells).
            match_path = intermediate('frame', hb.get_temp_dir())
            write_pyramid_frame_raster(match_path, arcseconds, target_bb, output_data_type, frame_ndv)
            resample_temp_path = intermediate('resample')
            if verbose:
                hb.log(f"Resampling {current_path} ({resample_method}, {variable_class}) to match {match_path}. Saving at {resample_temp_path}.")
            hb.resample_to_match(
                current_path,
                match_path,
                resample_temp_path,
                resample_method=resample_method,
                output_data_type=output_data_type,
                src_ndv=None,
                ndv=frame_ndv,
                s_srs_wkt=None,
                compress=True,
                ensure_fits=False,
                gtiff_creation_options=hb.globals.PRECOG_GTIFF_CREATION_OPTIONS_LIST,
                calc_raster_stats=False,
                add_overviews=False,
                pixel_size_override=None,
                target_aligned_pixels=True, # DOESNT DO ANYTHING BUT DONT WANT TO FUBAR STUFF
                bb_override=target_bb if not expand_to_global_extent else None,
                verbose=False,
            )
            current_path = resample_temp_path

    if needs_censoring:
        censor_temp_path = intermediate('censor')
        def op(x):
            out_of_range = np.zeros(x.shape, dtype=bool)
            if ndv_above is not None:
                out_of_range |= x > ndv_above
            if ndv_below is not None:
                out_of_range |= x < ndv_below
            return np.where(out_of_range, ndv, x)

        hb.log(f"Censoring {current_path} with ndv_above={ndv_above} and ndv_below={ndv_below}. Saving at {censor_temp_path}.")
        hb.raster_calculator_flex(current_path, op, censor_temp_path, output_data_type=output_data_type, ndv=ndv, compression=compression, verbose=verbose)
        current_path = censor_temp_path

    if value_reclassification_dict is not None:
        reclassify_temp_path = intermediate('reclassify')
        hb.log(f"Reclassifying {current_path} with {value_reclassification_dict}. Saving at {reclassify_temp_path}.")
        hb.reclassify_raster_hb(current_path, value_reclassification_dict, reclassify_temp_path, output_data_type=output_data_type, output_ndv=ndv)
        current_path = reclassify_temp_path

    # The nodata rule of the class (zero or the none class, declaration dropped; per-type nodata for a covariate),
    # deriving the observed-area companion from the nodata mask on the same pass if aggregation did not already.
    nodata_rule_path = intermediate('nodata')
    _apply_pog_nodata_rule(current_path, nodata_rule_path, variable_class, output_data_type,
                           fill_value=categorical_none_value if variable_class == 'categorical' else 0,
                           observed_area_output_path=observed_area_temp_path if (derive_observed_area and not observed_area_done) else None)
    current_path = nodata_rule_path

    overview_levels = hb.pyramid_compatible_overview_levels[arcseconds] if expand_to_global_extent else hb.get_pyramid_overview_levels_for_bb(arcseconds, target_bb)

    # The observed-area companion is itself an extensive POG, finished first because an intensive raster's overviews read it.
    if derive_observed_area:
        observed_area_path = os.path.join(os.path.dirname(os.path.abspath(final_raster_path)), os.path.splitext(os.path.basename(final_raster_path))[0] + '_observed_area.tif')
        _write_cog_with_pyramid_overviews(observed_area_temp_path, observed_area_path, overview_levels, None, gdal.GDT_Float64, None, compression, blocksize, verbose, variable_class='extensive')
    elif observed_area_path is not None:
        observed_area_path = os.path.abspath(observed_area_path)
        if not os.path.exists(observed_area_path):
            raise FileNotFoundError(f'observed_area_path does not exist: {observed_area_path}')
    denominator = observed_area_path if (variable_class == 'intensive' and observed_area_path is not None) else 'ha_per_cell'

    _write_cog_with_pyramid_overviews(current_path, output_raster_path, overview_levels, overview_resampling_method, output_data_type, ndv, compression, blocksize, verbose,
                                      variable_class=variable_class, intensive_weighting=intensive_weighting, denominator=denominator,
                                      pog_metadata={'POG_OBSERVED_AREA': _pog_reference_for(final_raster_path, observed_area_path) if observed_area_path else None,
                                                    'POG_REGISTRATION_SHIFT': registration_shift or declared.get('POG_REGISTRATION_SHIFT')})

    if not is_path_requested_kind(output_raster_path, verbose=verbose) and verbose:
        hb.log(f"Failed to create {'POG' if expand_to_global_extent else 'subpog'}: {output_raster_path} at abs path {hb.path_abs(output_raster_path)}")

    if original_output_raster_path is None:
        # The swap only renames the main file, so an input's external .ovr / .aux.xml would stay
        # behind under the new POG's name and shadow its internal overviews (is_path_pog then
        # fails on the result). Move them with the displaced original, or drop them with it.
        displaced_path = hb.rsuri(input_raster_path, 'displaced')
        for ext in ('.ovr', '.aux.xml'):
            if os.path.exists(input_raster_path + ext):
                if remove_displaced_files:
                    os.remove(input_raster_path + ext)
                else:
                    os.rename(input_raster_path + ext, displaced_path + ext)
        hb.displace_file(output_raster_path, input_raster_path, displaced_path=displaced_path, delete_original=remove_displaced_files)

    if remove_intermediate_files:
        # hb.temp only registers these for deletion at interpreter exit, and that hook rarely runs inside a
        # multiprocessing pool worker (the pool terminates its workers), so delete them here explicitly.
        for path in intermediate_paths:
            for sidecar in (path, path + '.aux.xml'):
                if os.path.exists(sidecar):
                    os.remove(sidecar)


def _write_pog_of_value(output_path, value, geotransform, x_size, y_size, arcseconds, bb, output_data_type, ndv, overview_resampling_method, compression, blocksize, verbose, variable_class):
    """Shared body of the write_pog_of_value_* functions: a constant raster on the given frame, finished as a POG."""
    if variable_class is None:
        variable_class = _infer_variable_class(output_data_type)
    if variable_class == 'extensive' and _is_integer_gdal_type(output_data_type):
        output_data_type = gdal.GDT_Int64  # sums of an integer extensive raster must not overflow at the top rung
    temp_path = hb.temp('.tif', filename_start=os.path.splitext(os.path.basename(output_path))[0] + '_b4_cog', remove_at_exit=True, tag_along_file_extensions=['.aux.xml'])
    options = [f"COMPRESS={compression}", f"BLOCKXSIZE={blocksize}", f"BLOCKYSIZE={blocksize}", "BIGTIFF=YES", "TILED=YES"]
    tmp_ds = gdal.GetDriverByName('GTiff').Create(temp_path, x_size, y_size, 1, output_data_type, options=options)
    tmp_ds.SetGeoTransform(geotransform)
    tmp_ds.SetProjection(hb.wgs_84_wkt)
    band = tmp_ds.GetRasterBand(1)
    value_rows = np.full((min(y_size, max(1, int(64e6 / (8 * x_size)))), x_size), value, dtype=gdal_array.GDALTypeCodeToNumericTypeCode(output_data_type))
    for row in range(0, y_size, value_rows.shape[0]):
        band.WriteArray(value_rows[:min(value_rows.shape[0], y_size - row)], xoff=0, yoff=row)
    tmp_ds = None
    levels = hb.pyramid_compatible_overview_levels[arcseconds] if bb is None else hb.get_pyramid_overview_levels_for_bb(arcseconds, bb)
    # The shared POG finishing sequence: class metadata and nodata convention, exact stats, the rung's overview chain, COG copy.
    _write_cog_with_pyramid_overviews(temp_path, output_path, levels, overview_resampling_method, output_data_type, ndv, compression, blocksize, verbose, variable_class=variable_class)


def write_pog_of_value_from_scratch(output_path, value, arcsecond_resolution, output_data_type, ndv=None, overview_resampling_method=None, compression='DEFLATE', blocksize='512', verbose=False, variable_class=None):
    """A global POG at arcsecond_resolution holding value everywhere. variable_class as in make_path_pog (None: inferred
    from the data type). A covariate carries the per-type nodata value; the other classes carry none, so ndv is unused."""
    arcseconds = float(arcsecond_resolution)
    x_size, y_size = hb.pyramid_compatable_shapes[arcseconds]
    _write_pog_of_value(output_path, value, hb.pyramid_compatible_geotransforms[arcseconds], x_size, y_size, arcseconds, None,
                        output_data_type, ndv, overview_resampling_method, compression, blocksize, verbose, variable_class)


def write_pog_of_value_from_match(output_path, match_path, value, output_data_type=None, ndv=None, overview_resampling_method=None, compression='DEFLATE', blocksize='512', verbose=False, variable_class=None):
    """A POG (or subpog) on the frame of match_path holding value everywhere. variable_class as in write_pog_of_value_from_scratch."""
    if not hb.path_exists(match_path, verbose=verbose):
        raise FileNotFoundError(f"Input raster does not exist: {match_path} at abs path {hb.path_abs(match_path)}")
    if output_data_type is None:
        output_data_type = hb.get_datatype_from_uri(match_path)
    src_ds = gdal.Open(match_path)
    geotransform, x_size, y_size = src_ds.GetGeoTransform(), src_ds.RasterXSize, src_ds.RasterYSize
    src_ds = None
    arcseconds = hb.get_cell_size_from_path_in_arcseconds(match_path, force_to_pyramid=True)
    bb = [geotransform[0], geotransform[3] + y_size * geotransform[5], geotransform[0] + x_size * geotransform[1], geotransform[3]]
    is_global = tuple(geotransform) == tuple(hb.pyramid_compatible_geotransforms[arcseconds])
    _write_pog_of_value(output_path, value, geotransform, x_size, y_size, arcseconds, None if is_global else bb,
                        output_data_type, ndv, overview_resampling_method, compression, blocksize, verbose, variable_class)
