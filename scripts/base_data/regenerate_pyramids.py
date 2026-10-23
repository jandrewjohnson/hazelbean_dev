"""Regenerate the pyramid base data under the POG specification (the pyramids paper, 2026-09-24b; pogs.qmd).

For new work this replaces create_ha_per_cell.py, make_as_pogs.py and make_match_rasters.py (in base_data/pyramids).
Those wrote the old ladder (7200 and 14400 s, no side rungs), without the POG_VARIABLE_CLASS metadata that is now
required, built whole global arrays in memory, and named fractional rungs 'ha_per_cell_0sec.tif'. Kept for the
record; do not rerun them.

What this writes, under base_data/pyramids. Any output file that already exists is skipped, valid or not: delete a file
to have it regenerated.
  1. pyramids/ha_per_cell_<rung>sec.tif            global POGs: extensive, Float64, sum overviews (hb.write_ha_per_cell_pog)
  2. pyramids/ha_per_cell_<rung>sec_1deg/ + .vrt    opt-in: tile sets for the rungs of 1 s and finer (paper, D.5.2)
  3. pyramids/ha_per_cell_column_<rung>sec.tif     one-column copies; gtap_invest reads them. Plain GeoTIFFs, not POGs
  3b. pyramids/ha_per_cell_<rung>sec.vrt           a few-hundred-byte VRT per rung that stretches the column across the
                                                    full global width: every cell reads its row's exact value
  4. pyramids/match_<rung>sec.tif                  constant categorical POGs, for code that still asks for a match
                                                    raster (make_path_pog itself no longer needs one)
  4b. pyramids/match_<rung>sec.vrt                 the rungs finer than 10 s: a VRT that stretches one shared 1 x 1 cell
                                                    (pyramids/match_cell.tif, value 1) across the rung's full global grid
Zone-id rasters (cartographic/ee) are not touched: each is a categorical POG whose internal mode overviews are its
coarser rungs, so no standalone coarse copies are made (until 2026-10-22 step 5 here wrote them).

Run in env1 with hazelbean at feature_pog_paper_spec or later. Leave DRY_RUN = True for the first run: it prints what
would be written and how many cells that is, so the expensive rungs can be dropped from the lists below.
"""
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from osgeo import gdal

import hazelbean as hb

gdal.UseExceptions()

DRY_RUN = '2026-10-20'

ALL_RUNGS = sorted(hb.pyramid_main_arcseconds + hb.pyramid_side_arcseconds)

# 1. Global ha_per_cell POGs. The paper keeps single global files down to 2 s and uses tile sets at 1 s and finer.
#    The values depend only on the row, so the files compress to little, but writing still touches every cell:
#    2 s is 2.1e11 cells (hours), 3 s 9.3e10, 9 s 1.2e10, 10 s 8.4e9 (minutes). Trim the list to taste.
HA_PER_CELL_GLOBAL_RUNGS = [a for a in ALL_RUNGS if a >= 10]

# 2. Tile sets for the finest rungs, one 1-degree tile per file (64,800 tiles each). Off by default: 1 s is 8.4e11
#    cells and 1/9 s 6.8e13, and nothing in hazelbean reads these files (aggregation computes the same numbers with
#    hb.ha_per_cell_rows). A window at any of these rungs can be written on demand with
#    hb.write_ha_per_cell_pog(path, arcseconds, bb=[...]).
HA_PER_CELL_TILE_SET_RUNGS = []  # e.g. [1.0] or [a for a in ALL_RUNGS if a <= 1]
TILE_WORKERS = max(1, (os.cpu_count() or 2) - 1)

# 3. One-column copies: cheap at every rung (the longest, 1/9 s, is 5.8 million rows).
HA_PER_CELL_COLUMN_RUNGS = ALL_RUNGS

# 3b. Stretched VRTs: the column of 3 drawn across the full width (nearest), so the VRT presents the whole global raster
#    at the rung's exact geotransform for a few hundred bytes. Values are bit-identical to hb.ha_per_cell_rows. It is not
#    a POG: it has no overviews, and a zoomed-out read samples fine cells rather than summing them, so for hectares at a
#    coarser rung use that rung's POG. Its column file is written first if missing. Only for 10 s and finer: there the
#    POGs are large or not written at all, while every coarser rung has a small global POG under the same name.
HA_PER_CELL_VRT_RUNGS = [a for a in ALL_RUNGS if a <= 10]  # 10 s and finer; coarser rungs have their global POG

# 4. Match rasters. Only the coarser rungs are worth materializing; for any rung, hb.write_pyramid_frame_raster writes
#    a sparse frame of near-zero bytes, which is what make_path_pog uses internally.
MATCH_RUNGS = [a for a in ALL_RUNGS if a >= 10]

# 4b. Match VRTs for the finer rungs, where a materialized constant raster would be billions of cells: one shared 1 x 1
#    Byte cell holding 1 (match_cell.tif), stretched by nearest across the rung's exact global grid, as 3b does for
#    ha_per_cell. Not a POG (no overviews), but any read gives 1, the geotransform and shape are the rung's, and it
#    declares the Byte nodata 255 like the match POGs (no cell holds it). The tile-set VRTs of hb leave a non-covariate
#    declaration unset because there VRTNodata also fills missing tiles; this VRT has no gaps, so the declaration is safe.
MATCH_VRT_RUNGS = [a for a in ALL_RUNGS if a < 10]


def rung_name(arcseconds):
    return hb.arcseconds_to_token(arcseconds) + 'sec'  # '10sec', '3-10sec'


def n_cells(arcseconds):
    cols, rows = hb.pyramid_compatable_shapes[arcseconds]
    return cols * rows


def write_ha_per_cell_global(pyramids_dir, arcseconds):
    path = os.path.join(pyramids_dir, f'ha_per_cell_{rung_name(arcseconds)}.tif')
    if os.path.exists(path):
        return path, 'already there, skipped'
    hb.write_ha_per_cell_pog(path, arcseconds)
    return path, 'written'


def _write_ha_per_cell_tile(args):
    path, arcseconds, bb = args
    if os.path.exists(path):
        return False
    hb.write_ha_per_cell_pog(path, arcseconds, bb=bb)
    return True


def write_ha_per_cell_tile_set(pyramids_dir, arcseconds, workers=TILE_WORKERS):
    tile_degrees = hb.pyramid_tile_degrees[arcseconds]
    tile_dir = os.path.join(pyramids_dir, f'ha_per_cell_{rung_name(arcseconds)}_{tile_degrees}deg')
    os.makedirs(tile_dir, exist_ok=True)
    jobs = [(os.path.join(tile_dir, hb.get_tile_filename('ha_per_cell', arcseconds, corner, tile_degrees)), arcseconds,
             hb.get_tile_bb_from_corner_string(corner, tile_degrees)) for corner in hb.list_tile_corner_strings(tile_degrees)]
    jobs = [job for job in jobs if not os.path.exists(job[0])]  # tiles already there are skipped
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for i, _ in enumerate(pool.map(_write_ha_per_cell_tile, jobs, chunksize=16)):
            if i % 1000 == 0:
                print(f'  {rung_name(arcseconds)} tiles: {i} of {len(jobs)} to write')
    vrt = os.path.join(pyramids_dir, os.path.basename(tile_dir) + '.vrt')  # beside the folder
    if os.path.exists(vrt) and not jobs:
        return vrt, 'already there, skipped'
    hb.build_pog_tileset_vrt(tile_dir, vrt)  # rebuilt when a tile was added, so the index lists it
    return vrt, 'written' if hb.is_path_pog_tileset(vrt) else 'written, but FAILS is_path_pog_tileset'


def write_ha_per_cell_column(pyramids_dir, arcseconds):
    """The single column of a rung's ha_per_cell: one cell per row, the same values as the POG (hb.ha_per_cell_rows)."""
    path = os.path.join(pyramids_dir, f'ha_per_cell_column_{rung_name(arcseconds)}.tif')
    if os.path.exists(path):
        return path, 'already there, skipped'
    n_rows = hb.pyramid_compatable_shapes[arcseconds][1]
    column = hb.ha_per_cell_rows(arcseconds, 0, n_rows)[:, None]  # rows from the top of the globe: the same bits as the POG's rows
    ds = gdal.GetDriverByName('GTiff').Create(path, 1, n_rows, 1, gdal.GDT_Float64, options=['COMPRESS=DEFLATE', 'BIGTIFF=IF_SAFER'])
    ds.SetGeoTransform(hb.pyramid_compatible_geotransforms[arcseconds])  # the global origin and cell size, one column wide
    ds.SetProjection(hb.wgs_84_wkt)
    ds.SetMetadataItem('AREA_OR_POINT', 'Area')
    ds.GetRasterBand(1).WriteArray(column)
    ds.GetRasterBand(1).ComputeStatistics(False)  # exact, written into the file (update mode), no .aux.xml
    ds = None
    return path, 'written'


def write_ha_per_cell_vrt(pyramids_dir, arcseconds):
    """ha_per_cell_<rung>sec.vrt: the one-column file stretched across the global width, nearest, so each row repeats its value."""
    path = os.path.join(pyramids_dir, f'ha_per_cell_{rung_name(arcseconds)}.vrt')
    if os.path.exists(path):
        return path, 'already there, skipped'
    column_path, _ = write_ha_per_cell_column(pyramids_dir, arcseconds)  # skipped if it is already there
    cols, rows = hb.pyramid_compatable_shapes[arcseconds]
    res = hb.pyramid_compatible_resolutions[arcseconds]  # repr() round-trips the double exactly, so GDAL reads the canonical geotransform
    with open(path, 'w', encoding='utf-8') as f:
        f.write(f'''<VRTDataset rasterXSize="{cols}" rasterYSize="{rows}">
  <SRS>EPSG:4326</SRS>
  <GeoTransform>-180.0, {res!r}, 0.0, 90.0, 0.0, {-res!r}</GeoTransform>
  <VRTRasterBand dataType="Float64" band="1">
    <SimpleSource resampling="nearest">
      <SourceFilename relativeToVRT="1">{os.path.basename(column_path)}</SourceFilename>
      <SourceBand>1</SourceBand>
      <SrcRect xOff="0" yOff="0" xSize="1" ySize="{rows}"/>
      <DstRect xOff="0" yOff="0" xSize="{cols}" ySize="{rows}"/>
    </SimpleSource>
  </VRTRasterBand>
</VRTDataset>
''')
    ds = gdal.Open(path)
    ok = ds.GetGeoTransform() == tuple(hb.pyramid_compatible_geotransforms[arcseconds]) and (ds.RasterXSize, ds.RasterYSize) == (cols, rows) \
        and ds.GetRasterBand(1).GetNoDataValue() == 255
    ds = None
    return path, 'written' if ok else 'written, but its geotransform, shape or nodata is not the canonical one'


def write_match(pyramids_dir, arcseconds):
    path = os.path.join(pyramids_dir, f'match_{rung_name(arcseconds)}.tif')
    if os.path.exists(path):
        return path, 'already there, skipped'
    hb.write_pog_of_value_from_scratch(path, 1, arcseconds, gdal.GDT_Byte, variable_class='categorical')
    return path, 'written'


def write_match_cell(pyramids_dir):
    """match_cell.tif: a single Byte cell holding 1, georeferenced as one cell covering the globe. The source every match VRT stretches."""
    path = os.path.join(pyramids_dir, 'match_cell.tif')
    if os.path.exists(path):
        return path, 'already there, skipped'
    ds = gdal.GetDriverByName('GTiff').Create(path, 1, 1, 1, gdal.GDT_Byte)
    ds.SetGeoTransform((-180.0, 360.0, 0.0, 90.0, 0.0, -180.0))
    ds.SetProjection(hb.wgs_84_wkt)
    ds.SetMetadataItem('AREA_OR_POINT', 'Area')
    ds.GetRasterBand(1).WriteArray(np.ones((1, 1), dtype='uint8'))
    ds = None
    return path, 'written'


def write_match_vrt(pyramids_dir, arcseconds):
    """match_<rung>sec.vrt: the one cell of match_cell.tif stretched over the rung's global grid, nearest, so every cell reads 1."""
    path = os.path.join(pyramids_dir, f'match_{rung_name(arcseconds)}.vrt')
    if os.path.exists(path):
        return path, 'already there, skipped'
    cell_path, _ = write_match_cell(pyramids_dir)  # skipped if it is already there
    cols, rows = hb.pyramid_compatable_shapes[arcseconds]
    res = hb.pyramid_compatible_resolutions[arcseconds]
    with open(path, 'w', encoding='utf-8') as f:
        f.write(f'''<VRTDataset rasterXSize="{cols}" rasterYSize="{rows}">
  <SRS>EPSG:4326</SRS>
  <GeoTransform>-180.0, {res!r}, 0.0, 90.0, 0.0, {-res!r}</GeoTransform>
  <VRTRasterBand dataType="Byte" band="1">
    <NoDataValue>255</NoDataValue>
    <SimpleSource resampling="nearest">
      <SourceFilename relativeToVRT="1">{os.path.basename(cell_path)}</SourceFilename>
      <SourceBand>1</SourceBand>
      <SrcRect xOff="0" yOff="0" xSize="1" ySize="1"/>
      <DstRect xOff="0" yOff="0" xSize="{cols}" ySize="{rows}"/>
    </SimpleSource>
  </VRTRasterBand>
</VRTDataset>
''')
    ds = gdal.Open(path)
    ok = ds.GetGeoTransform() == tuple(hb.pyramid_compatible_geotransforms[arcseconds]) and (ds.RasterXSize, ds.RasterYSize) == (cols, rows)
    ds = None
    return path, 'written' if ok else 'written, but its geotransform or shape is not the canonical one'


def print_plan():
    print('Rungs of the lattice:', ', '.join(rung_name(a) for a in ALL_RUNGS))
    rows = [('ha_per_cell global POG', a) for a in HA_PER_CELL_GLOBAL_RUNGS] + [('ha_per_cell tile set', a) for a in HA_PER_CELL_TILE_SET_RUNGS] \
        + [('match POG', a) for a in MATCH_RUNGS]
    for what, a in rows:
        print(f'  {what:24s} {rung_name(a):>11s}  {n_cells(a):>20,d} cells')
    print(f'  ha_per_cell columns at {len(HA_PER_CELL_COLUMN_RUNGS)} rungs')
    print(f'  ha_per_cell stretched VRTs at {len(HA_PER_CELL_VRT_RUNGS)} rungs')
    print(f'  match stretched VRTs at {len(MATCH_VRT_RUNGS)} rungs: ' + ', '.join(rung_name(a) for a in MATCH_VRT_RUNGS))


if __name__ == '__main__':  # required: the tile-set step spawns worker processes that re-import this file
    base_data_dir = hb.ProjectFlow().base_data_dir
    pyramids_dir = os.path.join(base_data_dir, 'pyramids')
    print(f'base_data: {base_data_dir}')
    print_plan()
    if hb.resolve_dry_run(DRY_RUN):  # True, False, or a date: a real run on that day and a dry run once it has passed
        print('Dry run: nothing written. Set DRY_RUN to False, or to today\'s date, to run the plan above.')
        raise SystemExit

    results = []
    for arcseconds in sorted(HA_PER_CELL_GLOBAL_RUNGS, reverse=True):  # coarse first: the quick ones land before the long ones
        results.append(write_ha_per_cell_global(pyramids_dir, arcseconds)); print(*results[-1])
    for arcseconds in sorted(HA_PER_CELL_TILE_SET_RUNGS, reverse=True):
        results.append(write_ha_per_cell_tile_set(pyramids_dir, arcseconds)); print(*results[-1])
    for arcseconds in HA_PER_CELL_COLUMN_RUNGS:
        results.append(write_ha_per_cell_column(pyramids_dir, arcseconds)); print(*results[-1])
    for arcseconds in HA_PER_CELL_VRT_RUNGS:
        results.append(write_ha_per_cell_vrt(pyramids_dir, arcseconds)); print(*results[-1])
    for arcseconds in MATCH_RUNGS:
        results.append(write_match(pyramids_dir, arcseconds)); print(*results[-1])
    for arcseconds in MATCH_VRT_RUNGS:
        results.append(write_match_vrt(pyramids_dir, arcseconds)); print(*results[-1])

    # Every POG written by this run must validate; a failure here means the file should not be shipped. Files that were
    # already there are not checked: list them with hb.is_path_pog(path, verbose=True) if they predate this script.
    written = [path for path, status in results if not status.endswith('skipped')]
    failures = [path for path in written if path.endswith('.tif') and '_column_' not in path and not hb.is_path_pog(path)]
    print(f'\n{len(written)} written, {len(results) - len(written)} skipped.')
    print('All POGs written validate.' if not failures else 'FAILED is_path_pog:\n  ' + '\n  '.join(failures))

