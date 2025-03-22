import math
import os
import random
import copy
import inspect
import numpy as np
import matplotlib
import matplotlib.style
import matplotlib.cm
import matplotlib.colors
from matplotlib import pyplot as plt
import mpl_toolkits
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
# from mpl_toolkits.basemap import Basemap
import geopandas as gpd
import pandas as pd
import scipy
import scipy.ndimage # Scipy requires this. Can't just do e.g. scipy.ndimage.filters.gaussian_filter()
import atexit
import hazelbean as hb
import matplotlib.gridspec as gridspec


L = hb.get_logger()

from aenum import MultiValueEnum

class LULC_ESA(MultiValueEnum):
    """Enum class containing basic LULC types"""

    # NO_DATA = "No Data", 255, "#ffffff"
    # CULTIVATED_LAND = "Cultivated Land", 10, "#ffff00"
    # FOREST = "Forest", 2, "#054907"
    # GRASSLAND = "Grassland", 3, "#ffa500"
    # SHRUBLAND = "Shrubland", 4, "#806000"
    # WATER = "Water", 5, "#069af3"
    # WETLAND = "Wetlands", 6, "#95d0fc"
    TUNDRA = "Tundra", 7, "#967bb6"
    # ARTIFICIAL_SURFACE = "Artificial Surface", 8, "#dc143c"
    # BARELAND = "Bareland", 9, "#a6a6a6"
    # SNOW_AND_ICE = "Snow and Ice", 10, "#000000"

    ndv = 'ndv', 0, "#000000"
    crop_rainfed = 'crop_rainfed', 10, "#ffff00"
    crop_rainfed_herb = 'crop_rainfed_herb', 11, "#ffff01"
    crop_rainfed_tree = 'crop_rainfed_tree', 12, "#ffff02"
    crop_irrigated = 'crop_irrigated', 20, "#ffff03"
    crop_natural_mosaic = 'crop_natural_mosaic', 30, "#ffff04"
    natural_crop_mosaic = 'natural_crop_mosaic', 40, "#806001"
    tree_broadleaved_evergreen = 'tree_broadleaved_evergreen', 50, "#054908"
    tree_broadleaved_deciduous_closed_to_open_15 = 'tree_broadleaved_deciduous_closed_to_open_15', 60, "#054909"
    tree_broadleaved_deciduous_closed_40 = 'tree_broadleaved_deciduous_closed_40', 61, "#054910"
    tree_broadleaved_deciduous_open_15_40 = 'tree_broadleaved_deciduous_open_15_40', 62, "#054911"
    tree_needleleaved_deciduous_closed_to_open_15 = 'tree_needleleaved_deciduous_closed_to_open_15', 70, "#054912"
    tree_needleleaved_evergreen_closed_to_open_15_extended = 'tree_needleleaved_evergreen_closed_to_open_15_extended', 71, "#054913"
    tree_needleleaved_evergreen_open_15_40 = 'tree_needleleaved_evergreen_open_15_40', 72, "#054914"
    # tree_needleleaved_deciduous_closed_to_open_15 = 'tree_needleleaved_deciduous_closed_to_open_15', 80, "#054915"
    tree_needleleaved_deciduous_closed_40 = 'tree_needleleaved_deciduous_closed_40', 81, "#054916"
    tree_needleleaved_deciduous_open_15_40 = 'tree_needleleaved_deciduous_open_15_40', 82, "#054917"
    tree_mixed_type = 'tree_mixed_type', 90, "#054919"
    mosaic_tree_and_shrub_50_herbaceous_cover_50 = 'mosaic_tree_and_shrub_50_herbaceous_cover_50', 100, "#054918"
    mosaic_herbaceous_cover_50_tree_and_shrub_50 = 'mosaic_herbaceous_cover_50_tree_and_shrub_50', 110, "#806002"
    shrubland = 'shrubland', 120, "#806003"
    evergreen_shrubland = 'evergreen_shrubland', 121, "#806004"
    deciduous_shrubland = 'deciduous_shrubland', 122, "#806005"
    grassland = 'grassland', 130, "#ffa501"
    lichens_and_mosses = 'lichens_and_mosses', 140, "#806006"
    sparse_vegetation_tree_shrub_herbaceous_cover_15 = 'sparse_vegetation_tree_shrub_herbaceous_cover_15', 150, "#806007"
    sparse_tree_15 = 'sparse_tree_15', 151, "#806008"
    sparse_shrub_15 = 'sparse_shrub_15', 152, "#806009"
    sparse_herbaceous_cover_15 = 'sparse_herbaceous_cover_15', 153, "#806010"
    tree_cover_flooded_fresh_or_brakish_water = 'tree_cover_flooded_fresh_or_brakish_water', 160, "#95d0fc"
    tree_cover_flooded_saline_water = 'tree_cover_flooded_saline_water', 170, "#95d0fd"
    shrub_or_herbaceous_cover_flooded_fresh_saline_brakish_water = 'shrub_or_herbaceous_cover_flooded_fresh_saline_brakish_water', 180, "#95d0fe"
    urban_areas = 'urban_areas', 190, "#dc143c"
    bare_areas = 'bare_areas', 200, "#a6a6a6"
    consolidated_bare_areas = 'consolidated_bare_areas', 201, "#a6a6a7"
    unconsolidated_bare_areas = 'unconsolidated_bare_areas', 202, "#a6a6a8"
    water_bodies = 'water_bodies', 210, "#069af3"
    permanent_snow_and_ice = 'permanent_snow_and_ice', 220, "#000001"
    #
    # esacci_to_seals_simplified_correspondence[0] = [0, 'ndv', 'ndv']
    # esacci_to_seals_simplified_correspondence[10] = [2, 'crop_rainfed', 'crop']
    # esacci_to_seals_simplified_correspondence[11] = [2, 'crop_rainfed_herb', 'crop']
    # esacci_to_seals_simplified_correspondence[12] = [2, 'crop_rainfed_tree', 'crop']
    # esacci_to_seals_simplified_correspondence[20] = [2, 'crop_irrigated', 'crop']
    # esacci_to_seals_simplified_correspondence[30] = [2, 'crop_natural_mosaic', 'crop']
    # esacci_to_seals_simplified_correspondence[40] = [2, 'natural_crop_mosaic', 'crop']
    # esacci_to_seals_simplified_correspondence[50] = [4, 'tree_broadleaved_evergreen', 'forest']
    # esacci_to_seals_simplified_correspondence[60] = [4, 'tree_broadleaved_deciduous_closed_to_open_15', 'forest']
    # esacci_to_seals_simplified_correspondence[61] = [4, 'tree_broadleaved_deciduous_closed_40', 'forest']
    # esacci_to_seals_simplified_correspondence[62] = [4, 'tree_broadleaved_deciduous_open_15_40', 'forest']
    # esacci_to_seals_simplified_correspondence[70] = [4, 'tree_needleleaved_deciduous_closed_to_open_15', 'forest']
    # esacci_to_seals_simplified_correspondence[71] = [4, 'tree_needleleaved_evergreen_closed_to_open_15_extended', 'forest']
    # esacci_to_seals_simplified_correspondence[72] = [4, 'tree_needleleaved_evergreen_open_15_40', 'forest']
    # esacci_to_seals_simplified_correspondence[80] = [4, 'tree_needleleaved_deciduous_closed_to_open_15', 'forest']
    # esacci_to_seals_simplified_correspondence[81] = [4, 'tree_needleleaved_deciduous_closed_40', 'forest']
    # esacci_to_seals_simplified_correspondence[82] = [4, 'tree_needleleaved_deciduous_open_15_40', 'forest']
    # esacci_to_seals_simplified_correspondence[90] = [4, 'tree_mixed_type', 'forest']
    # esacci_to_seals_simplified_correspondence[100] = [4, 'mosaic_tree_and_shrub_50_herbaceous_cover_50', 'forest']
    # esacci_to_seals_simplified_correspondence[110] = [5, 'mosaic_herbaceous_cover_50_tree_and_shrub_50', 'shrubland']
    # esacci_to_seals_simplified_correspondence[120] = [5, 'shrubland', 'shrubland']
    # esacci_to_seals_simplified_correspondence[121] = [5, 'evergreen_shrubland', 'shrubland']
    # esacci_to_seals_simplified_correspondence[122] = [5, 'deciduous_shrubland', 'shrubland']
    # esacci_to_seals_simplified_correspondence[130] = [3, 'grassland', 'grassland']
    # esacci_to_seals_simplified_correspondence[140] = [5, 'lichens_and_mosses', 'shrubland']
    # esacci_to_seals_simplified_correspondence[150] = [5, 'sparse_vegetation_tree_shrub_herbaceous_cover_15', 'shrubland']
    # esacci_to_seals_simplified_correspondence[151] = [4, 'sparse_tree_15', 'forest']
    # esacci_to_seals_simplified_correspondence[152] = [5, 'sparse_shrub_15', 'shrubland']
    # esacci_to_seals_simplified_correspondence[153] = [5, 'sparse_herbaceous_cover_15', 'shrubland']
    # esacci_to_seals_simplified_correspondence[160] = [4, 'tree_cover_flooded_fresh_or_brakish_water', 'forest']
    # esacci_to_seals_simplified_correspondence[170] = [4, 'tree_cover_flooded_saline_water', 'forest']
    # esacci_to_seals_simplified_correspondence[180] = [5, 'shrub_or_herbaceous_cover_flooded_fresh_saline_brakish_water', 'shrubland']
    # esacci_to_seals_simplified_correspondence[190] = [1, 'urban_areas', 'urban']
    # esacci_to_seals_simplified_correspondence[200] = [7, 'bare_areas', 'other']
    # esacci_to_seals_simplified_correspondence[201] = [7, 'consolidated_bare_areas', 'other']
    # esacci_to_seals_simplified_correspondence[202] = [7, 'unconsolidated_bare_areas', 'other']
    # esacci_to_seals_simplified_correspondence[210] = [6, 'water_bodies', 'water']
    # esacci_to_seals_simplified_correspondence[220] = [7, 'permanent_snow_and_ice', 'other']

    @property
    def id(self):
        return self.values[1]

    @property
    def color(self):
        return self.values[2]


class LULC_SENTINEL(MultiValueEnum):
    """Enum class containing basic LULC types"""

    NO_DATA = "No Data", 0, "#ffffff"
    CULTIVATED_LAND = "Cultivated Land", 1, "#ffff00"
    FOREST = "Forest", 2, "#054907"
    GRASSLAND = "Grassland", 3, "#ffa500"
    SHRUBLAND = "Shrubland", 4, "#806000"
    WATER = "Water", 5, "#069af3"
    WETLAND = "Wetlands", 6, "#95d0fc"
    TUNDRA = "Tundra", 7, "#967bb6"
    ARTIFICIAL_SURFACE = "Artificial Surface", 8, "#dc143c"
    BARELAND = "Bareland", 9, "#a6a6a6"
    SNOW_AND_ICE = "Snow and Ice", 10, "#000000"

    @property
    def id(self):
        return self.values[1]

    @property
    def color(self):
        return self.values[2]

from matplotlib.colors import ListedColormap, BoundaryNorm
# Reference colormap things
lulc_cmap_sentinel = ListedColormap([x.color for x in LULC_SENTINEL], name="lulc_cmap_sentinel")
lulc_cmap_esa = ListedColormap([x.color for x in LULC_ESA], name="lulc_cmap_esa")
lulc_norm_sentinel = BoundaryNorm([x - 0.5 for x in range(len(LULC_SENTINEL) + 1)], lulc_cmap_sentinel.N)
lulc_norm_esa = BoundaryNorm([x - 0.5 for x in range(len(LULC_ESA) + 1)], lulc_cmap_esa.N)
# lulc_norm = BoundaryNorm([x - 0.5 for x in range(len(LULC) + 1)], lulc_cmap.N)

def plot_polygon_collection(ax, geoms, values=None, color=None,
                            cmap=None, vmin=None, vmax=None, color_kwargs=None, **kw):
    """
    Plots a collection of Polygon and MultiPolygon geometries to `ax`
    Parameters
    ----------
    ax : matplotlib.axes.Axes
        where shapes will be plotted
    geoms : a sequence of `N` Polygons and/or MultiPolygons (can be mixed)
    values : a sequence of `N` values, optional
        Values will be mapped to colors using vmin/vmax/cmap. They should
        have 1:1 correspondence with the geometries (not their components).
        Otherwise follows `color` / `facecolor` color_kwargs.
    edgecolor : single color or sequence of `N` colors
        Color for the edge of the polygons
    facecolor : single color or sequence of `N` colors
        Color to fill the polygons. Cannot be used together with `values`.
    color : single color or sequence of `N` colors
        Sets both `edgecolor` and `facecolor`
    **color_kwargs
        Additional keyword arguments passed to the collection
    Returns
    -------
    collection : matplotlib.collections.Collection that was plotted
    """
    from descartes.patch import PolygonPatch
    from matplotlib.collections import PatchCollection

    geoms, values = _flatten_multi_geoms(geoms, values)
    if None in values:
        values = None

    if color_kwargs is None:
        color_kwargs = {}  # This is so that i don't put a mutable variable as a default.

    # PatchCollection does not accept some color_kwargs.
    if 'markersize' in color_kwargs:
        del color_kwargs['markersize']

    # NOTE Default behavior deactivated to force default default.
    color = None
    # color=None overwrites specified facecolor/edgecolor with default color
    if color is not None:
        color_kwargs['color'] = color

    collection = PatchCollection([PolygonPatch(poly) for poly in geoms],
                                 **color_kwargs)

    if values is not None:
        collection.set_array(np.asarray(values))
        collection.set_cmap(cmap)
        collection.set_clim(vmin, vmax)

    ax.add_collection(collection, autolim=True)
    ax.autoscale_view()
    return collection


def plot_list(input_list):
    return plt.plot(input_list)


def show(input_flex, **kwargs):
    """Analyze input_flex and choose the best way to show it. E.g, if its a raster, plot it with imshow."""
    
    # Get name of variable passed to input_flex
    # NOT ADVISED TO MONKEY WITH
    frame = inspect.currentframe()
    frame = inspect.getouterframes(frame)[1]
    string = inspect.getframeinfo(frame[0]).code_context[0].strip()
    function_args = string[string.find('(') + 1:-1].split(',')
    var_names = []
    for i in function_args:
        if i.find('=') != -1:
            var_names.append(i.split('=')[1].strip())
        else:
            var_names.append(i)
    var_name = var_names[0]

    if isinstance(input_flex, hb.ArrayFrame):
        show_array(input_flex.data, var_name=var_name, **kwargs)
    elif isinstance(input_flex, np.ndarray):
        show_array(input_flex, var_name=var_name, **kwargs)
    elif isinstance(input_flex, str) and os.path.splitext(input_flex)[1] in hb.common_gdal_readable_file_extensions:
        if os.path.exists(input_flex):
            input_array = hb.as_array_resampled_to_size(hb.LARGE_MEMORY_ARRAY_SIZE)
            show_array(input_array, var_name=var_name, **kwargs)
        else:
            raise NameError('hb.show given a string with a gdal readable extension, but the file doesnt seem to exist.')
    else:
        raise NameError('hb.show unable to interpret input_flex type.')


def show_array(input_array, **kwargs):
    """Temporarily deprecated for hb_show_array."""
    # try:
    #     hb.full_show_array(input_array, **kwargs)
    # except:
    #     hb.simple_show_array(input_array, **kwargs)


    full_show_array(input_array, **kwargs)

def simple_show_array(input_array, **kwargs):
    fig, ax = plt.subplots()
    cmap = matplotlib.cm.get_cmap('Spectral')
    im = ax.imshow(input_array, cmap=cmap, interpolation='nearest')
    cbar = plt.colorbar(im, orientation='horizontal')
    plt.show()

def simple_show_arra_at_exity(input_array, **kwargs):
    fig, ax = plt.subplots()
    cmap = matplotlib.cm.get_cmap('Spectral')
    im = ax.imshow(input_array, cmap=cmap, interpolation='nearest')
    cbar = plt.colorbar(im, orientation='horizontal')
    hb.plot_at_exit(plt)

def plot_array(input_array, output_path=None, title=None, cbar_label=None, cbar_font_size=9,
               ndv=None, vmin=None, vmid=None, vmax=None, percent_clip=None,
               color_scheme=None, plot_spines=False, plot_box=False,
               num_cbar_ticks=3, tick_labels=None, switch_to_scientific_notation_threshold=100000,
               fig_height=None, fig_width=None, dpi=200, display_plot=True, log_normalize=False, **kwargs):

    # # Available color-schemes:
    # available_color_schemes = ['bold_spectral', 'bold_spectral_white_left', 'spectral', 'spectral_white_center', 'prgn', 'white_to_black', 'spectral_cotnrast',
    #                            'brbg', 'piyg', 'puor', 'rdbu', 'rdylbu', 'oranges', 'reds', 'purples', 'greys', 'greens', 'blues', 'bugn',
    #                            'bupu', 'gnbu', 'orrd', 'pubu', 'show_state_boundaries', 'purd', 'rdpu', 'ylgn', 'ylgnbu', 'ylorbr', 'ylorrd', 'random']
    #
    # # Here are the builtin mpl cmaps.
    # cmaps_list = [('Sequential', ['Blues', 'BuGn', 'BuPu', 'GnBu', 'Greens', 'Greys', 'Oranges', 'OrRd', 'PuBu', 'PuBuGn', 'PuRd', 'Purples', 'RdPu', 'Reds', 'YlGn', 'YlGnBu', 'YlOrBr', 'YlOrRd']),
    #               ('Sequential (2)', ['afmhot', 'autumn', 'bone', 'cool', 'copper', 'gist_heat', 'gray', 'hot', 'pink', 'spring', 'summer', 'winter']),
    #               ('Diverging', ['BrBG', 'bwr', 'coolwarm', 'PiYG', 'PRGn', 'PuOr', 'RdBu', 'RdGy', 'RdYlBu', 'RdYlGn', 'Spectral', 'seismic']),
    #               ('Qualitative', ['Accent', 'Dark2', 'Paired', 'Pastel1', 'Pastel2', 'Set1', 'Set2', 'Set3']),

    if title is None:
        # Get name of variable passed to input_array
        # NOT ADVISED TO MONKEY WITH
        frame = inspect.currentframe()
        frame = inspect.getouterframes(frame)[1]
        string = inspect.getframeinfo(frame[0]).code_context[0].strip()
        function_args = string[string.find('(') + 1:-1].split(',')
        var_names = []
        for i in function_args:
            if i.find('=') != -1:
                var_names.append(i.split('=')[1].strip())
            else:
                var_names.append(i)
        var_name = var_names[0]
        title = var_name

    if output_path is None:
        output_path =  hb.temp('.png', title)

    if ndv is not None:
        if vmin is None:
            vmin = np.min(input_array[input_array != ndv])
        if vmax is None:
            vmax = np.max(input_array[input_array != ndv])
        if vmid is None:
            vmid = vmax - ((vmax - vmin) / 2.0)
    else:
        if vmin is None:
            vmin = np.min(input_array)
        if vmax is None:
            vmax = np.max(input_array)
        if vmid is None:
            vmid = vmax - ((vmax - vmin) / 2.0)

    # Altenatively to providing specific vmin, vmid, vmax, you can specify it as a percent. This also achieves the percent clip feature of arcgis.
    # NOTE: Overrides behavior of setting vmin vmid or vmax
    if percent_clip is not None:
        vmin = np.percentile(input_array[input_array != ndv], 2)
        vmax = np.percentile(input_array[input_array != ndv], 98)
        # I chose not to make this one calculated from the data by default because many times it would but vmid right next to vmin
        vmid = np.percentile(input_array[input_array != ndv], 50)

        # Now check to see if the new vmid is too close to either extreme
        safe_proportion = 0.33
        if (vmin / vmid) < (vmax / vmid) * safe_proportion:
            vmid = (vmax - vmin) * safe_proportion
        elif (vmax / vmid) > (vmin / vmid) * (1 - safe_proportion):
            vmid = (vmax - vmin) * (1 - safe_proportion)

    elif type(percent_clip) == list and len(percent_clip) == 3:
        # TODOO make this dynamic with tick marks.
        if not kwargs.get('vmin'):
            vmin = np.percentile(input_array[input_array != ndv], percent_clip[0])
        if not kwargs.get('vmax'):
            vmid = np.percentile(input_array[input_array != ndv], percent_clip[1])
        if not kwargs.get('vmid'):
            vmax = np.percentile(input_array[input_array != ndv], percent_clip[2])

    else:
        L.info('Unable to interpret vmin, vmid, vmax values.')

    # If not given, choose color scheme based on data
    if color_scheme is None:
        if vmin < 0 and vmax > 0:
            color_scheme = 'Spectral'
            # if not kwargs.get('vmid'):
            #     vmid = 0
            if not kwargs.get('pinch'):
                pinch = True
        else:
            color_scheme = 'Viridis'

    cmap = matplotlib.cm.get_cmap(color_scheme)
    if ndv is not None:
        input_array = np.where(input_array != ndv, input_array, np.nan)

    if num_cbar_ticks == 2:
        if not tick_labels:
            cbar_tick_labels = [vmin, vmax]
        else:
            cbar_tick_labels = tick_labels
        cbar_tick_locations = [vmin, vmax]
    elif num_cbar_ticks == 3:
        if not tick_labels:
            cbar_tick_labels = [vmin, vmid, vmax]
        else:
            cbar_tick_labels = tick_labels
        cbar_tick_locations = [vmin, vmid, vmax]
    elif num_cbar_ticks == 5:
        if not tick_labels:
            cbar_tick_labels = [vmin, vmin + (vmid - vmin) / 2, vmid, vmid + (vmax - vmid) / 2, vmax]
        else:
            cbar_tick_labels = tick_labels
        cbar_tick_locations = [vmin, vmin + (vmid - vmin) / 2, vmid, vmid + (vmax - vmid) / 2, vmax]
    else:

        cbar_tick_labels = []
        cbar_tick_locations = []
        for i in range(num_cbar_ticks):
            # tick_value = hb.round_significant_n(vmin + (abs(vmin) + abs(vmax)) * (float(i) / (float(num_cbar_ticks) - 1.)))
            tick_value = hb.round_significant_n((vmin + abs(vmin) + abs(vmax) * float(i)) / (float(num_cbar_ticks) - 1.), 1)
            if not tick_labels:
                cbar_tick_locations.append(tick_value)
            else:
                cbar_tick_labels = tick_labels
            cbar_tick_labels.append(tick_value)

    # Round tick values to be reasonable size
    if not tick_labels:
        for i, tick_value in enumerate(cbar_tick_labels):

            tick_value_string = str(tick_value)

            decimals_present = len(tick_value_string.split('.'))
            if -0.01 < tick_value < 0.01:
                if decimals_present > 3:
                    decimals_to_show = 3
                else:
                    decimals_to_show = decimals_present
            elif abs(tick_value) < 1:
                if decimals_present > 2:
                    decimals_to_show = 2
                else:
                    decimals_to_show = decimals_present
            elif abs(tick_value) < 10:
                if decimals_present > 0:
                    decimals_to_show = 1
            elif abs(tick_value) < 1000000:
                if decimals_present > 0:
                    decimals_to_show = 1

            else:
                decimals_to_show = 0
            tick_value_rounded = round(float(tick_value), decimals_to_show)
            if tick_value_rounded > 10000000:
                tick_value_rounded = "{:.2e}".format(tick_value_rounded)

            new_tick_value_rounded = hb.round_significant_n(tick_value, 2)
            if abs(new_tick_value_rounded) > abs(switch_to_scientific_notation_threshold):
                new_tick_value_rounded = "{:.2e}".format(new_tick_value_rounded)
            cbar_tick_labels[i] = str(new_tick_value_rounded)
    #
    # Create fig with a 3,2 gridspec
    if fig_height is not None:
        fig = plt.figure(figsize=(fig_width, fig_height))
    else:
        fig = plt.figure()

    # NOTE Cbars are placed into their own ax, greated as an inner 1,3 gridspec to allow for edge cropping.
    outer_grid = gridspec.GridSpec(2, 1, height_ratios=[1, .2], wspace=0.0, hspace=0.0)

    # fig = plt.figure(figsize=(11, 11))
    im_ax = plt.subplot(outer_grid[0])

    im_ax.spines['top'].set_visible(False)
    im_ax.spines['right'].set_visible(False)
    im_ax.spines['bottom'].set_visible(False)
    im_ax.spines['left'].set_visible(False)
    im_ax.get_xaxis().set_visible(False)
    im_ax.get_yaxis().set_visible(False)
    # cbar_ax = plt.subplot(inner_grid[0, 1])

    inner_grid = gridspec.GridSpecFromSubplotSpec(1, 3, subplot_spec=outer_grid[1], wspace=0.0, hspace=0.0, width_ratios=[1, 5, 1])

    cbar_ax = plt.Subplot(fig, inner_grid[1])

    import matplotlib as mpl

    # im = im_ax.imshow(input_array, cmap=cmap, interpolation='nearest', vmin=vmin, vmax=vmax)
    cmap = 'Spectral'

    if log_normalize:
        im = im_ax.imshow(input_array, cmap=cmap, norm=mpl.colors.SymLogNorm(linthresh=0.03, linscale=0.03), interpolation='nearest', vmin=vmin, vmax=vmax)
    else:
        im = im_ax.imshow(input_array, cmap=cmap, interpolation='nearest', vmin=vmin, vmax=vmax)
    im.set_clim(vmin, vmax)


    #
    # cbar_ax.spines['top'].set_visible(False)
    # cbar_ax.spines['right'].set_visible(False)
    # cbar_ax.spines['bottom'].set_visible(False)
    # cbar_ax.spines['left'].set_visible(False)
    # cbar_ax.get_xaxis().set_visible(False)
    # cbar_ax.get_yaxis().set_visible(False)

    # if plot_spines is False:
    #     for ax in [im_ax, cbar_ax]:
    #         ax.spines['top'].set_visible(False)
    #         ax.spines['right'].set_visible(False)
    #         ax.spines['bottom'].set_visible(False)
    #         ax.spines['left'].set_visible(False)
    #
    # if plot_box is False:
    #     im_ax.get_xaxis().set_visible(False)
    #     im_ax.get_yaxis().set_visible(False)
    #
    # cbar = plt.colorbar(im, orientation='horizontal', ticks=cbar_tick_locations, aspect=33, shrink=0.7)
    cbar = fig.colorbar(im, ax=cbar_ax, orientation='horizontal')
    # cbar.ax.set_xticklabels(cbar_tick_labels, fontsize=cbar_font_size)
    if cbar_label is not None:
        cbar.set_label(cbar_label, size=cbar_font_size)



    if title:
        # fig.suptitle(title)
        im_ax.set_title(title)

    plt.tight_layout()  # NOTE This can only be callled after a plt creation method.

    output_padding_inches = 0.001
    if output_path:
        try:
            plt.savefig(output_path, dpi=dpi, alpha=True)
            # plt.savefig(output_path, dpi=dpi, alpha=True, bbox_inches='tight', pad_inches=output_padding_inches)
        except:
            raise Exception('Failed to savefig at ' + str(output_path))

    # # force_display = kwargs.get('force_display', None)
    if display_plot:
        try:
            hb.plot_at_exit(plt)
        except:
            raise Exception('Failed to plot in hazelbean')

    plt.close()


def full_show_array(input_array, **kwargs):
    input_path = kwargs.get('input_path', None)

    var_name = kwargs.get('var_name', None)
    if not var_name:
        # Get name of variable passed to input_array
        # NOT ADVISED TO MONKEY WITH
        frame = inspect.currentframe()
        frame = inspect.getouterframes(frame)[1]
        string = inspect.getframeinfo(frame[0]).code_context[0].strip()
        function_args = string[string.find('(') + 1:-1].split(',')
        var_names = []
        for i in function_args:
            if i.find('=') != -1:
                var_names.append(i.split('=')[1].strip())
            else:
                var_names.append(i)
        var_name = var_names[0]

    if type(input_array) is not np.ndarray:
        raise TypeError('Gave a non-array object to geoecon visualization show_array()')

    # In case we want to write it to a png, specify a uri.
    output_path = kwargs.get('output_path', None)
    save_dir = kwargs.get('save_dir', None)

    array_dtype = input_array.dtype

    # no_data_value = kwargs.get('no_data_value', hb.default_no_data_values_by_gdal_number[
    #     hb.numpy_type_to_gdal_number[array_dtype]])

    # These affect the cbar and will be calculated from the data if not set.
    vmin = kwargs.get('vmin', None)
    vmax = kwargs.get('vmax', None)
    vmid = kwargs.get('vmid', None)

    set_bad = kwargs.get('set_bad', None)

    # Pinch slices out a portion of the cbar to increase contrast of values above and below it (e.g. for divergent data)
    pinch = kwargs.get('pinch', False)
    pinch_at_steps = kwargs.get('pinch_at_steps', [])

    # If true, will generate a cpar clipped to [2, 50, 98]. If a list of three percentages, will generate the cbar to that.
    cbar_percentiles = kwargs.get('cbar_percentiles', False)

    color_scheme = kwargs.get('color_scheme', None)

    display_immediately = kwargs.get('display_immediately', False)

    fig_height = kwargs.get('fig_height', 9)
    fig_width = kwargs.get('fig_width', 12)
    vertical_shift = kwargs.get('vertical_shift', 0)
    horizontal_shift = kwargs.get('horizontal_shift', 0)
    vertical_stretch = kwargs.get('vertical_stretch', 1.0)
    horizontal_stretch = kwargs.get('horizontal_stretch', 1.0)
    use_basemap = kwargs.get('use_basemap', False)
    overlay_shp_uri = kwargs.get('overlay_shp_uri', None)
    title = kwargs.get('title', None)
    cbar_label = kwargs.get('cbar_label', None)
    show_lat_lon = kwargs.get('show_lat_lon', False)  # if True, show best 5 graticules.
    resolution = kwargs.get('resolution', 'c')  # c (coarse), l, i, h
    bounding_box = kwargs.get('bounding_box', None)
    bounding_box_lat_lon = kwargs.get('bounding_box_lat_lon', None)
    num_cbar_ticks = kwargs.get('num_cbar_ticks', 2)
    projection = kwargs.get('projection', 'cyl')

    tick_labels = kwargs.get('tick_labels', None)
    # crop_inf = kwargs.get('crop_inf', True)

    reverse_colorbar = kwargs.get('reverse_colorbar', False)
    show_state_boundaries = kwargs.get('show_state_boundaries', False)
    cbar_font_size = kwargs.get('cbar_font_size', 10)
    use_pcolormesh = kwargs.get('use_pcolormesh', False)  # useful for when you need to project to non cylindrical. not fully implemented.
    insert_white_divergence_point = kwargs.get('insert_white_divergence_point', False)  # This is still in testing. It might mess up the data. Better is to just make a note in the legend.
    dpi = kwargs.get('dpi', 300)
    output_padding_inches = kwargs.get('output_padding_inches', .03)
    block_plotting = kwargs.get('block_plotting', False)

    move_ticks_in = kwargs.get('move_ticks_in', 0.0)
    ndv = kwargs.get('ndv', hb.default_no_data_values_by_gdal_number[hb.numpy_type_to_gdal_number[array_dtype]])

    # Show or save an array as a global map in .jpg ready for publication. Functionality to create a custom colorbar with optimal min, max and zero_values is provided.
    # At the moment, only the basemap method is implemented and it still lacks proper projected clipping.

    whiteout_left = False
    whiteout_right = False

    switch_to_scientific_notation_threshold = 100000

    # Available color-schemes:
    available_color_schemes = ['bold_spectral', 'bold_spectral_white_left', 'spectral', 'spectral_white_center', 'prgn', 'white_to_black', 'spectral_cotnrast',
                               'brbg', 'piyg', 'puor', 'rdbu', 'rdylbu', 'oranges', 'reds', 'purples', 'greys', 'greens', 'blues', 'bugn',
                               'bupu', 'gnbu', 'orrd', 'pubu', 'show_state_boundaries', 'purd', 'rdpu', 'ylgn', 'ylgnbu', 'ylorbr', 'ylorrd', 'random']

    # Here are the builtin mpl cmaps.
    cmaps_list = [('Sequential', ['Blues', 'BuGn', 'BuPu', 'GnBu', 'Greens', 'Greys', 'Oranges', 'OrRd', 'PuBu', 'PuBuGn', 'PuRd', 'Purples', 'RdPu', 'Reds', 'YlGn', 'YlGnBu', 'YlOrBr', 'YlOrRd']),
                  ('Sequential (2)', ['afmhot', 'autumn', 'bone', 'cool', 'copper', 'gist_heat', 'gray', 'hot', 'pink', 'spring', 'summer', 'winter']),
                  ('Diverging', ['BrBG', 'bwr', 'coolwarm', 'PiYG', 'PRGn', 'PuOr', 'RdBu', 'RdGy', 'RdYlBu', 'RdYlGn', 'Spectral', 'seismic']),
                  ('Qualitative', ['Accent', 'Dark2', 'Paired', 'Pastel1', 'Pastel2', 'Set1', 'Set2', 'Set3']),
                  ('Miscellaneous', ['gist_earth', 'terrain', 'ocean', 'gist_stern', 'brg', 'CMRmap', 'cubehelix', 'gnuplot', 'gnuplot2', 'gist_ncar', 'nipy_spectral', 'jet', 'rainbow', 'gist_rainbow', 'hsv', 'flag', 'prism'])]

    # Be careful not to modify the input_array because this will change the array that was passed in unless you do everything on a copy.
    m = hb.as_array_no_path_resampled_to_size(input_array, hb.MAX_IN_MEMORY_ARRAY_SIZE)

    # rewrite all infs as ndv
    m = np.where((m >= -1 * np.inf) & (m <= np.inf), m, ndv)

    zero_as_nan = kwargs.get('zero_as_nan', True)
    if zero_as_nan:
        m = np.where(m == 0, ndv, m)

    nan_as_zero = kwargs.get('nan_as_0', True)
    if nan_as_zero:
        m = np.where(np.isnan(m), 0, m)

    n_nonzero = np.count_nonzero(m[m != ndv])

    if n_nonzero > 0:
        if vmin is None:
            vmin = np.min(m[m != ndv])
        if vmax is None:
            vmax = np.max(m[m != ndv])
        if vmid is None:
            vmid = vmax - ((vmax - vmin) / 2.0)

        # Altenatively to providing specific vmin, vmid, vmax, you can specify it as a percent. This also achieves the percent clip feature of arcgis.
        if cbar_percentiles is True:
            if not kwargs.get('vmin'):
                vmin = np.percentile(m[m != ndv], 2)
            if not kwargs.get('vmax'):
                vmax = np.percentile(m[m != ndv], 98)
            if not kwargs.get('vmid'):
                # I chose not to make this one calculated from the data by default because many times it would but vmid right next to vmin
                vmid = np.percentile(m[m != ndv], 50)

                # Now check to see if the new vmid is too close to either extreme
                safe_proportion = 0.33
                if (vmin / vmid) < (vmax / vmid) * safe_proportion:
                    vmid = (vmax - vmin) * safe_proportion
                elif (vmax / vmid) > (vmin / vmid) * (1 - safe_proportion):
                    vmid = (vmax - vmin) * (1 - safe_proportion)

        elif type(cbar_percentiles) == list and len(cbar_percentiles) == 3:
            # TODOO make this dynamic with tick marks.
            if not kwargs.get('vmin'):
                vmin = np.percentile(m[m != ndv], cbar_percentiles[0])
            if not kwargs.get('vmax'):
                vmid = np.percentile(m[m != ndv], cbar_percentiles[1])
            if not kwargs.get('vmid'):
                vmax = np.percentile(m[m != ndv], cbar_percentiles[2])

    else:
        vmin, vmid, vmax = -1, 0, 1

    # Notation for proportionclip is [clip from top, from bottom, from left, from right]
    if bounding_box == 'us_midwest':
        # the notation on prortion clips is kinda odd.
        use_proportion_clip = True  # It's a proportion from the relevant edge such that can't sum to > 1
        bounding_box_proportion_clip = [.21, .68, .2, .73]
    elif bounding_box == 'clip_poles':
        use_proportion_clip = True
        bounding_box_proportion_clip = [.03, .18, 0, 0]
    elif bounding_box == 'global':
        use_proportion_clip = True
        bounding_box_proportion_clip = [0, 0, 0, 0]
    elif bounding_box == 'has_gli_data':
        use_proportion_clip = True
        bounding_box_proportion_clip = [.12, .19, .15, .07]
    elif bounding_box == 'se_asia':
        use_proportion_clip = True
        bounding_box_proportion_clip = [.38, .435, .76, .1]
    elif bounding_box == 'se_asia_vs':
        use_proportion_clip = True
        bounding_box_proportion_clip = [.338, .435, .753, .103]
    elif bounding_box == 'horn_of_africa':
        use_proportion_clip = True
        bounding_box_proportion_clip = [.414, .488, .588, .355]
    elif bounding_box == 'sahel':
        use_proportion_clip = True
        bounding_box_proportion_clip = [.358, .514, .445, .385]
    elif bounding_box == 'uganda':
        use_proportion_clip = True
        bounding_box_proportion_clip = [.474, .486, .58, .401]
    elif bounding_box == 'indonesia':
        use_proportion_clip = True
        bounding_box_proportion_clip = [.448, .435, .753, .103]
    elif bounding_box == 'central_america':
        use_proportion_clip = True
        bounding_box_proportion_clip = [.448, .435, .753, .103]
    elif isinstance(bounding_box, list):
        bounding_box_proportion_clip = bounding_box
        use_proportion_clip = True
    else:
        bounding_box_proportion_clip = [0., 0., 0., 0.]
        use_proportion_clip = True

    # The bounding box then is used to created the clipped_array. The method of clipping and the type of bounding box varyies dramatically according to what plotting method (imshow, basemape, pcolormeash) is used.
    def convert_bounding_box_proportion_to_array_slice_indices(bounding_box_proportion_clip, array_to_clip):
        input_rows, input_cols = array_to_clip.shape[0], array_to_clip.shape[1]

        top_rows_to_clip = math.floor(bounding_box_proportion_clip[0] * input_rows)
        bottom_rows_to_clip = math.floor(bounding_box_proportion_clip[1] * input_rows)
        left_cols_to_clip = math.floor(bounding_box_proportion_clip[2] * input_cols)
        right_cols_to_clip = math.floor(bounding_box_proportion_clip[3] * input_cols)

        # in array notation, a bounding box is defined via slice notation. Below, in the lat lon version, it will be different.
        bounding_box = [0 + top_rows_to_clip, input_rows - bottom_rows_to_clip, 0 + left_cols_to_clip, input_cols - right_cols_to_clip]

        return bounding_box

    def convert_bounding_box_proportion_to_lat_lon(bounding_box_proportion_clip, array_to_clip):
        input_rows, input_cols = array_to_clip.shape[0], array_to_clip.shape[1]

        top_lats_to_clip = (bounding_box_proportion_clip[0] * 180)
        bottom_lats_to_clip = (bounding_box_proportion_clip[1] * 180)
        left_lons_to_clip = (bounding_box_proportion_clip[2] * 360)
        right_lons_to_clip = (bounding_box_proportion_clip[3] * 360)

        llcrnrlat = -90 + bottom_lats_to_clip
        urcrnrlat = 90 - top_lats_to_clip
        llcrnrlon = -180 + left_lons_to_clip
        urcrnrlon = 180 - right_lons_to_clip

        bounding_box = [llcrnrlat, urcrnrlat, llcrnrlon, urcrnrlon]
        return bounding_box

    if use_basemap and False:
        if use_proportion_clip:
            bounding_box_processed = convert_bounding_box_proportion_to_lat_lon(bounding_box_proportion_clip, m)

        # NOTE, giving bounding_box_lat_lon overrides anything else.
        if bounding_box_lat_lon:
            bounding_box_processed = bounding_box_lat_lon
        bounding_box_slices = convert_bounding_box_proportion_to_array_slice_indices(bounding_box_proportion_clip, m)
        m = m[bounding_box_slices[0]: bounding_box_slices[1], bounding_box_slices[2]: bounding_box_slices[3]]

    else:
        bounding_box_processed = convert_bounding_box_proportion_to_array_slice_indices(bounding_box_proportion_clip, m)
        m = m[bounding_box_processed[0]: bounding_box_processed[1], bounding_box_processed[2]: bounding_box_processed[3]]

    # Apply any mask needed
    # NOTE: all math on vmid etc must be done before this line else nan will dominate.

    # If not given, choose color scheme based on data
    if color_scheme is None:
        if vmin < 0 and vmax > 0:
            color_scheme = 'spectral_white_center'
            if not kwargs.get('vmid'):
                vmid = 0
            if not kwargs.get('pinch'):
                pinch = True
        else:
            color_scheme = 'spectral_bold'

    # Generate cmap
    # LEARNING POINT, i think the best way to deal with passing kwargs to inner functions woud
    # be to pass newly created ones like breakpoints, then just pass the original kwargs. this saves the state from the right point.
    # HOWEVER, here is a weird case where i introduce information in the defaults and that would not register unless i manually create a new kwargs as below,
    # but I wouldn't want to pass in vmin=vmin because i would get a DOUBLE KWARGS keyword error.
    cbar_kwargs = {}
    cbar_kwargs['vmin'] = vmin
    cbar_kwargs['vmax'] = vmax
    cbar_kwargs['vmid'] = vmid
    cbar_kwargs['pinch'] = pinch
    cbar_kwargs['pinch_at_steps'] = pinch_at_steps
    cbar_kwargs['color_scheme'] = color_scheme
    cbar_kwargs['reverse_colorbar'] = reverse_colorbar

    if color_scheme in color_scheme_data:
        cmap = generate_custom_colorbar(m, **cbar_kwargs)
    else:
        cmap = matplotlib.cm.get_cmap(color_scheme)

    # Basemap plots np.nan as white by default, can be changed by set_bad.
    if ndv:
        m = np.where(m != ndv, m, np.nan)

    # TODO Refactor this to have a secondary normalization such that values NEAR the vmid don't accidently flip signs.
    # Modify m so that the values over vmax are actually equal to vmax, so that set_over works for different colors.
    # m[m < vmin] = vmin
    # m[m > vmax] = vmax
    #
    # #m[m==0] = np.inf # equiv to setting to np.nan
    # m[m==0] = 999999999999999999999999999999999999999999999999
    #
    # # NOTE, masks have the same effect as setting to nan via set_bad.
    # # m = np.ma.masked_where(m > 333, m)
    #
    # cmap.set_bad((.9, .9, .9))
    # cmap.set_over((1.0, 1.0, 1.0))
    # cmap.set_under((.999, .7, .95))
    #
    #

    #
    # if no_data_value is not None:
    #     m = np.ma.masked_where(m==no_data_value, m)

    # NOTE: I'm pretty sure that only set_bad works atm because i don't use pcolormesh. I've kept these activated in case it shows me when/how it does start working.
    # cmap.set_bad((.97, .97, .97), 1.)
    # cmap.set_over((.7, .95, .95), 1.)
    # cmap.set_under((.5, .95, .7), 1.)

    if num_cbar_ticks == 2:
        if not tick_labels:
            cbar_tick_labels = [vmin, vmax]
        else:
            cbar_tick_labels = tick_labels
        cbar_tick_locations = [vmin, vmax]
    elif num_cbar_ticks == 3:
        if not tick_labels:
            cbar_tick_labels = [vmin, vmid, vmax]
        else:
            cbar_tick_labels = tick_labels
        cbar_tick_locations = [vmin, vmid, vmax]
    elif num_cbar_ticks == 5:
        if not tick_labels:
            cbar_tick_labels = [vmin, vmin + (vmid - vmin) / 2, vmid, vmid + (vmax - vmid) / 2, vmax]
        else:
            cbar_tick_labels = tick_labels
        cbar_tick_locations = [vmin, vmin + (vmid - vmin) / 2, vmid, vmid + (vmax - vmid) / 2, vmax]
    else:

        cbar_tick_labels = []
        cbar_tick_locations = []
        for i in range(num_cbar_ticks):
            # tick_value = hb.round_significant_n(vmin + (abs(vmin) + abs(vmax)) * (float(i) / (float(num_cbar_ticks) - 1.)))
            tick_value = hb.round_significant_n((vmin + abs(vmin) + abs(vmax) * float(i)) / (float(num_cbar_ticks) - 1.), 1)
            if not tick_labels:
                cbar_tick_locations.append(tick_value)
            else:
                cbar_tick_labels = tick_labels
            cbar_tick_labels.append(tick_value)

    # Round tick values to be reasonable size
    if not tick_labels:
        for i, tick_value in enumerate(cbar_tick_labels):

            tick_value_string = str(tick_value)

            decimals_present = len(tick_value_string.split('.'))
            if -0.01 < tick_value < 0.01:
                if decimals_present > 3:
                    decimals_to_show = 3
                else:
                    decimals_to_show = decimals_present
            elif abs(tick_value) < 1:
                if decimals_present > 2:
                    decimals_to_show = 2
                else:
                    decimals_to_show = decimals_present
            elif abs(tick_value) < 10:
                if decimals_present > 0:
                    decimals_to_show = 1
            elif abs(tick_value) < 1000000:
                if decimals_present > 0:
                    decimals_to_show = 1

            else:
                decimals_to_show = 0
            tick_value_rounded = round(float(tick_value), decimals_to_show)
            if tick_value_rounded > 10000000:
                tick_value_rounded = "{:.2e}".format(tick_value_rounded)

            new_tick_value_rounded = hb.round_significant_n(tick_value, 2)
            if abs(new_tick_value_rounded) > abs(switch_to_scientific_notation_threshold):
                new_tick_value_rounded = "{:.2e}".format(new_tick_value_rounded)
            cbar_tick_labels[i] = str(new_tick_value_rounded)

    # Create the matplotlib objects
    fig, ax = plt.subplots()

    if set_bad:
        cmap.set_bad(set_bad)
    # cmap.set_bad('w')
    # cmap.set_under('w') #i think the way to fix this is modify the array we're plotting. #this messes up when vmin clips something, but seems to fix the bug in pcoormesh that doesn't work with set_bad method.

    # If using basemap, create a basemap object and either an imshow or pcolormesh object to plot the array.
    if use_basemap and False: # DEPRECATED start using Cartopy
        pass
        # bm = Basemap(projection=projection, lon_0=0, llcrnrlat=bounding_box_processed[0], urcrnrlat=bounding_box_processed[1], llcrnrlon=bounding_box_processed[2], urcrnrlon=bounding_box_processed[3], resolution=resolution, area_thresh=5000)  # Resolution: c (crude), l (low), i (intermediate), h (high), f (full), area_thresh=10000 is size of lakes and coastlines to ignore in m2

        # if kwargs.get('draw_continents'):
        #     overlay_shp_uri = os.path.join(hb.BASE_DATA_DIR, 'naturalearth', 'ne_110m_coastline.shp')
        #
        # if overlay_shp_uri:
        #     s = bm.readshapefile(overlay_shp_uri, 'attributes', linewidth=0.15, color='0.1')
        #
        # im = bm.imshow(np.flipud(m), cmap=cmap, interpolation='nearest', vmin=vmin, vmax=vmax)
        #
        # if not overlay_shp_uri:
        #     bm.drawcoastlines(linewidth=0.15, color='0.1')
        #     bm.drawcountries(linewidth=0.15, color='0.1')
        #
        # # bm.drawrivers()
        # if show_lat_lon:
        #     bm.drawparallels(np.arange(-90., 120., 30.), linewidth=0.25)
        #     bm.drawmeridians(np.arange(0., 420., 60.), linewidth=0.25)
        # if show_state_boundaries:
        #     bm.drawstates(linewidth=0.15, color='0.1')
        #
        # divider = mpl_toolkits.axes_grid1.make_axes_locatable(plt.gca())
        # cbar = plt.colorbar(im, orientation='horizontal', ticks=cbar_tick_locations)
        #
        # ax.spines['top'].set_visible(False)
        # ax.spines['right'].set_visible(False)
        # ax.spines['bottom'].set_visible(False)
        # ax.spines['left'].set_visible(False)

    # Due to limitations in the basemap method, this section creates an imshow object instead. It doesn't have projection ability but is faster and more stable for regular arrays.
    else:  # at the moment, this is still not implemented.
        im = ax.imshow(m, cmap=cmap, interpolation='nearest', vmin=vmin, vmax=vmax)
        # im = ax.imshow(m, cmap=cmap, norm=MidpointNormalize(midpoint=111.), interpolation='nearest', vmin=vmin, vmax=vmax)
        im.set_clim(vmin, vmax)

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)

        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)

        divider = mpl_toolkits.axes_grid1.make_axes_locatable(plt.gca())
        cbar = plt.colorbar(im, orientation='horizontal', ticks=cbar_tick_locations, aspect=33, shrink=0.7)

    cbar.ax.set_xticklabels(cbar_tick_labels, fontsize=cbar_font_size)
    if cbar_label is not None:
        cbar.set_label(cbar_label)

    if title == 'from_output_path' or title is None:
        if output_path:
            title_string = os.path.split(output_path)[1].replace('_', ' ').title()
            title = True

        else:
            title_string = var_name  # DEFAULT TITLE
            title = True
    else:
        title_string = title

    if title:
        ax.set_title(title_string)

    if save_dir and not output_path:
        output_path = os.path.join(save_dir, title_string + '.png')

    if output_path == 'inplace_png' and input_path is not None:
        output_path = input_path.replace(os.path.splitext(input_path)[1], '.png')

    if kwargs.get('tight_layout'):
        plt.tight_layout()  # NOTE This can only be callled after a plt creation method.

    if output_path:
        try:
            plt.savefig(output_path, dpi=dpi, bbox_inches='tight', pad_inches=output_padding_inches)
        except:
            raise Exception('Failed to savefig at ' + str(output_path))

    force_display = kwargs.get('force_display', None)
    if display_immediately:
        try:
            plt.show()
        except:
            raise Exception('Failed to plot in hazelbean')
    elif block_plotting:
        pass
    elif output_path is None:
        hb.plot_at_exit(plt)
    elif force_display:
        hb.plot_at_exit(plt)
    else:
        pass

    # plt.close()

    return plt, cbar, fig, ax


def plot_at_exit(input_plt):
    hb.plots_to_display_at_exit.append(input_plt)

def do_plot_at_exit():
    for plt in hb.plots_to_display_at_exit:
        plt.show()
atexit.register(do_plot_at_exit)


def generate_custom_colorbar(input_array, **kwargs):
    # The following dict defines a very customizable colorbar. See http://wiki.scipy.org/Cookbook/Matplotlib/Show_colormaps for details on the solution
    # each color of RGB is defined by 3 tuple. The first element in each tuple is the iterpolation point (always normalized 0 - 1), the second element is the color going left and the third is the color going right (higher values).

    vmin = kwargs.get('vmin', 0)
    vmax = kwargs.get('vmax', 1)
    reverse_colorbar = kwargs.get('reverse_colorbar', False)
    insert_white_divergence_point = kwargs.get('insert_white_divergence_point', False)
    whiteout_left = kwargs.get('whiteout_left', False)
    whiteout_right = kwargs.get('whiteout_right', False)
    vmid = kwargs.get('vmid', None)
    pinch = kwargs.get('pinch', False)
    pinch_at_steps = kwargs.get('pinch_at_steps', [])
    color_scheme = kwargs.get('color_scheme', 'bold_spectral')

    if vmin is None:
        vmin = np.min(input_array)
    if vmax is None:
        vmax = np.max(input_array)

    color_scheme = color_scheme
    rgb_string_to_use = color_scheme_data[color_scheme]

    if reverse_colorbar is True:
        rgb_list_reversed = rgb_string_to_use.splitlines()
        rgb_list_reversed.reverse()
        rgb_string_to_use = ''
        for entry in rgb_list_reversed:
            rgb_string_to_use += entry
            if entry is not rgb_list_reversed[-1]:
                rgb_string_to_use += '\n'

    if vmid is not None and (vmid < vmin or vmax < vmid):
        raise NameError('Must set center cbar inbetween vmin and vmax. Received vmin,vmid,vmax of ' + ', '.join([str(i) for i in [vmin, vmid, vmax]]))

    breakpoints = kwargs.get('breakpoints', [])

    n_rgb_lines = len(rgb_string_to_use.splitlines())

    pinch_at_steps = kwargs.get('pinch_at_steps', [])
    if type(pinch_at_steps) is not list and pinch_at_steps:
        pinch_at_steps = [pinch_at_steps]

    if pinch:
        if len(pinch_at_steps):
            pass
        else:
            pinch_at_steps = [int(n_rgb_lines / 2)]
    else:
        if len(pinch_at_steps):
            pinch = True
        else:
            pass

    if len(breakpoints) == 0:
        if vmid is None:
            if len(pinch_at_steps) == 0:
                for i in range(0, n_rgb_lines):
                    breakpoints.append(((float(vmax) - float(vmin)) * (float(i) / (float(n_rgb_lines) - 1.0))) / (float(vmax) - float(vmin)))
            else:
                raise NameError('Currently only 1 pinch_at_step is supported, but this could be extended pretty easlity if I properly account for cases where there are many pinches and few breakpoints.')
        else:
            if len(pinch_at_steps) == 0:
                if float(vmax) - float(vmin) != 0.:
                    mid_proportion = (float(vmid) - float(vmin)) / (float(vmax) - float(vmin))
                else:
                    mid_proportion = 0

                n_on_left = float(math.floor(n_rgb_lines / 2))  # Dropping decimals.

                if n_rgb_lines % 2 == 0:
                    for i in range(int(n_on_left)):
                        to_append = (float(i) / (n_on_left - 1)) * float(mid_proportion)
                        breakpoints.append(to_append)
                    for i in range(int(n_on_left), n_rgb_lines):
                        to_append = ((float(i) - n_on_left + 1) / (n_on_left)) * (1.0 - mid_proportion) + mid_proportion
                        breakpoints.append(to_append)
                else:
                    for i in range(int(n_on_left)):
                        to_append = (float(i) / (n_on_left)) * float(mid_proportion)
                        breakpoints.append(to_append)

                    # Have to insert a middle point because there's an odd number of colors to interpolate from.
                    to_append = float(mid_proportion)
                    breakpoints.append(to_append)

                    for i in range(int(n_on_left + 1), n_rgb_lines):
                        to_append = ((float(i) - n_on_left) / (n_on_left)) * (1.0 - mid_proportion) + mid_proportion
                        breakpoints.append(to_append)

            elif len(pinch_at_steps) == 1:
                if float(vmax) - float(vmin) != 0.:
                    mid_proportion = (float(vmid) - float(vmin)) / (float(vmax) - float(vmin))
                else:
                    mid_proportion = 0

                n_on_left = float(math.floor(n_rgb_lines / 2))  # Dropping decimals.

                if n_rgb_lines % 2 == 0:
                    for i in range(int(n_on_left)):
                        to_append = (float(i) / (n_on_left - 1.0)) * float(mid_proportion)
                        breakpoints.append(to_append)
                    for i in range(int(n_on_left), n_rgb_lines):
                        to_append = ((float(i) - n_on_left) / (n_on_left - 1.0)) * (1.0 - mid_proportion) + mid_proportion
                        breakpoints.append(to_append)
                else:
                    for i in range(int(n_on_left)):
                        to_append = (float(i) / (n_on_left - 1.0)) * float(mid_proportion)
                        breakpoints.append(to_append)

                    # Have to insert a middle point because there's an odd number of colors to interpolate from.
                    to_append = float(mid_proportion)
                    breakpoints.append(to_append)

                    for i in range(int(n_on_left + 2), n_rgb_lines + 1):
                        to_append = ((float(i) - n_on_left - 2) / (n_on_left - 1.0)) * (1.0 - mid_proportion) + mid_proportion
                        breakpoints.append(to_append)

            else:
                raise NameError('Currently only 1 pinch_at_step is supported, but this could be extended pretty easlity if I properly account for cases where there are many pinches and few breakpoints.')
    else:
        raise NameError('Havent yet implemented manual lists breakpoints.')

    cdict_to_use = convert_rgb_string_to_cdict(rgb_string_to_use, breakpoints)

    transparent_at_cbar_step = kwargs.get('transparent_at_cbar_step', None)
    # By default, a cbar's cdict has thre (RGB) values. if this is set, it puts on a FOURTH alpha at that cbar step.
    if transparent_at_cbar_step is not None:

        # Make everything opaque to initilaize
        add_alpha_list = [1.0 for i in list(range(len(cdict_to_use['red'])))]

        # Depending on input, add zero-alpha values at the right parts of the cbar.
        if type(transparent_at_cbar_step) in [tuple, list]:
            try:
                for break_value in transparent_at_cbar_step:
                    add_alpha_list[int(break_value)] = 0.0
            except:
                raise NameError('Unable to set transparent_at_cbar_step at ' + str(transparent_at_cbar_step) + '. Perhaps you defined a step outside of the cbars range?')

        else:
            try:
                add_alpha_list[int(transparent_at_cbar_step)] = 0.0
            except:
                raise NameError('Unable to set transparent_at_cbar_step at ' + str(transparent_at_cbar_step) + '. Perhaps you defined a step outside of the cbars range?')

        cdict_with_alpha = copy.deepcopy(cdict_to_use)
        for k, v in cdict_to_use.items():
            tuple_list = []
            for c, ii in enumerate(v):
                new_tuple = tuple([ii[0], add_alpha_list[c], add_alpha_list[c]])
                tuple_list.append(new_tuple)
        cdict_with_alpha['alpha'] = tuple(tuple_list)
        cdict_to_use = cdict_with_alpha

    cmap = matplotlib.colors.LinearSegmentedColormap('custom_cmap', cdict_to_use, 512)
    # cmap = matplotlib.colors.LinearSegmentedColormap('custom_cmap', cdict_to_use, 256)
    return cmap


def convert_rgb_string_to_cdict(input_string, breakpoints=None):
    # Converts a string, such as that copy-pasted from colorbrewer2.org, to a matplotlib-compatible cdict.
    # Optionally defines non-symetric breakpoints (e.g., to put zero at non center points, or log-plots)

    # Convert the string into a list of lists
    input_list = input_string.splitlines()
    for i, j in enumerate(input_list):
        input_list[i] = j.split(',')

    num_colors = len(input_list)

    # the list breakpoints defines where the colors defined in input_string are placed on the 0-1 matplotlib colorbar spectrum
    if breakpoints is None:
        breakpoints = []
        for i in range(num_colors):
            breakpoints.append(float(i) / (float(num_colors) - 1.0))
    if len(breakpoints) is not num_colors:
        L.critical('The breakpoints specified are not in the same quantity as the colors defined in input_string. This can lead to spurious color statements.')

    # create cdict, a dictionary of RGB values, wherein each dict entry has a seperate tuples for each point in breakpoint, wherein each breakpoint tuple defines (point on 0-1, color from left, color from right)
    cdict = {'red': None, 'green': None, 'blue': None}
    red_tuple_list = []
    green_tuple_list = []
    blue_tuple_list = []
    for color_index in range(num_colors):

        insert_white_divergence_point = False  # 'NYI'
        whiteout_left = False  # 'NYI'
        whiteout_right = False  # 'NYI'

        if insert_white_divergence_point:
            epsilon = 0.005
            if color_index == num_colors / 2 - 2:  # the one before the divergence
                red_tuple_list.append((breakpoints[color_index] - epsilon, float(input_list[color_index][0]) / 255.0, float(input_list[color_index][0]) / 255.0))
                green_tuple_list.append((breakpoints[color_index] - epsilon, float(input_list[color_index][1]) / 255.0, float(input_list[color_index][1]) / 255.0))
                blue_tuple_list.append((breakpoints[color_index] - epsilon, float(input_list[color_index][2]) / 255.0, float(input_list[color_index][2]) / 255.0))
            elif color_index == num_colors / 2 - 1:  # the divergence
                red_tuple_list.append((breakpoints[color_index], float(input_list[color_index][0]) / 255.0, 255.0 / 255.0))  # now the second interpolation color is white
                green_tuple_list.append((breakpoints[color_index], float(input_list[color_index][1]) / 255.0, 255.0 / 255.0))
                blue_tuple_list.append((breakpoints[color_index], float(input_list[color_index][2]) / 255.0, 255.0 / 255.0))
            elif color_index == num_colors / 2 - 0:  # the one after the divergence
                red_tuple_list.append((breakpoints[color_index] + epsilon, 255.0 / 255.0, float(input_list[color_index][0]) / 255.0))  # now the first interpolation color is white
                green_tuple_list.append((breakpoints[color_index] + epsilon, 255.0 / 255.0, float(input_list[color_index][1]) / 255.0))
                blue_tuple_list.append((breakpoints[color_index] + epsilon, 255.0 / 255.0, float(input_list[color_index][2]) / 255.0))
            else:  # has a divergent point, but this point is not on or next to it.
                red_tuple_list.append((breakpoints[color_index], float(input_list[color_index][0]) / 255.0, float(input_list[color_index][0]) / 255.0))
                green_tuple_list.append((breakpoints[color_index], float(input_list[color_index][1]) / 255.0, float(input_list[color_index][1]) / 255.0))
                blue_tuple_list.append((breakpoints[color_index], float(input_list[color_index][2]) / 255.0, float(input_list[color_index][2]) / 255.0))
        else:  # no divergence point
            if whiteout_left:
                if color_index < num_colors / 2:  # because MPL interpolates, having values other than white on unused parts of the colorbar still end up being shown for the extreme left value. Thus, I white them out here.
                    red_tuple_list.append((breakpoints[color_index], 1.0, 1.0))
                    green_tuple_list.append((breakpoints[color_index], 1.0, 1.0))
                    blue_tuple_list.append((breakpoints[color_index], 1.0, 1.0))
                else:
                    red_tuple_list.append((breakpoints[color_index], float(input_list[color_index][0]) / 255.0, float(input_list[color_index][0]) / 255.0))
                    green_tuple_list.append((breakpoints[color_index], float(input_list[color_index][1]) / 255.0, float(input_list[color_index][1]) / 255.0))
                    blue_tuple_list.append((breakpoints[color_index], float(input_list[color_index][2]) / 255.0, float(input_list[color_index][2]) / 255.0))
            elif whiteout_right:
                if color_index >= num_colors / 2:
                    red_tuple_list.append((breakpoints[color_index], 1.0, 1.0))
                    green_tuple_list.append((breakpoints[color_index], 1.0, 1.0))
                    blue_tuple_list.append((breakpoints[color_index], 1.0, 1.0))
                else:
                    red_tuple_list.append((breakpoints[color_index], float(input_list[color_index][0]) / 255.0, float(input_list[color_index][0]) / 255.0))
                    green_tuple_list.append((breakpoints[color_index], float(input_list[color_index][1]) / 255.0, float(input_list[color_index][1]) / 255.0))
                    blue_tuple_list.append((breakpoints[color_index], float(input_list[color_index][2]) / 255.0, float(input_list[color_index][2]) / 255.0))
            else:
                red_tuple_list.append((breakpoints[color_index], float(input_list[color_index][0]) / 255.0, float(input_list[color_index][0]) / 255.0))
                green_tuple_list.append((breakpoints[color_index], float(input_list[color_index][1]) / 255.0, float(input_list[color_index][1]) / 255.0))
                blue_tuple_list.append((breakpoints[color_index], float(input_list[color_index][2]) / 255.0, float(input_list[color_index][2]) / 255.0))

    cdict['red'] = tuple(red_tuple_list)
    cdict['green'] = tuple(green_tuple_list)
    cdict['blue'] = tuple(blue_tuple_list)

    return cdict


def plot_bar_graph(input_data, **kw):
    def autolabel(rects):
        """
        Attach a text label above each bar displaying its height
        """
        for rect in rects:
            height = rect.get_height()
            ax.text(rect.get_x() + rect.get_width() / 2., 1.05 * height,
                    '%d' % int(height),
                    ha='center', va='bottom')

    fig, ax = plt.subplots()

    ylabel = kw.get('ylabel', None)
    xlabel = kw.get('xlabel', None)
    title = kw.get('title', None)
    xtick_labels = kw.get('xtick_labels', None)

    color = kw.get('color', None)

    width = .8
    locs = np.arange(len(input_data))

    rects1 = ax.bar(locs, input_data, width, alpha=0.8, color=color)  # , yerr=men_std

    ax.set_ylabel(ylabel)
    ax.set_xlabel(xlabel)
    ax.set_title(title)

    ax.set_xticks([i + width / 2 for i in locs])
    ax.set_xticklabels(xtick_labels)

    # autolabel(rects1)

    if kw.get('output_uri'):
        fig.savefig(kw['output_uri'])

    return ax


def plot_geodataframe_shapefile(gdf, column,
                                figsize=None, color_kwargs=None, **kw):
    # Deprecated because pysal was throwing a deprecation and this wasnt THAT cool
    override_deprecation = False
    if override_deprecation:
        if kw.get('style'):
            matplotlib.style.use(kw['style'])
        else:
            matplotlib.style.use('ggplot')

        vmin = kw.get('vmin', gdf[column].min())
        vmax = kw.get('vmax', gdf[column].max())

        if not kw.get('make_symmetric_divergent_colorbar'):
            if vmin < 0 and vmax > 0:
                make_symmetric_divergent_colorbar = True
            else:
                make_symmetric_divergent_colorbar = False

        if make_symmetric_divergent_colorbar:
            if abs(vmin) > abs(vmax):
                vmax = vmin * -1
            else:
                vmin = vmax * -1

        color_scheme = kw.get('color_scheme', 'Spectral')

        if kw.get('bins'):
            bins = kw['bins']
            num_steps = len(bins)
        else:
            num_steps = 21  # This only determines the resolution of the cbar
            bins = list(np.linspace(vmin, vmax, num_steps))

        # I deprecated this until pysal new api is finished
        # custom_cbar_categories = User_Defined(gdf[column], bins)
        # values = np.array(custom_cbar_categories.yb)
        custom_cbar_categories = 'fix'
        fig, ax = plt.subplots(figsize=figsize)

        ax.set_aspect('equal')

        # These are the color category ids, not actual values.
        mn = custom_cbar_categories.min()
        mx = custom_cbar_categories.max()

        poly_idx = np.array(
            (gdf.geometry.type == 'Polygon') | (gdf.geometry.type == 'MultiPolygon'))
        polys = gdf.geometry[poly_idx]

        if color_kwargs is None:
            color_kwargs = {}  # This is so that i don't put a mutable variable as a default.

        color_kwargs['linewidth'] = kw.get('linewidth', 0.5)

        if not polys.empty:
            plot_polygon_collection(ax, polys, custom_cbar_categories[poly_idx], True,
                                    vmin=mn, vmax=mx, cmap=color_scheme,
                                    color_kwargs=color_kwargs, **kw)
        show_lat_lon_lines = kw.get('show_lat_lon_lines', True)
        if show_lat_lon_lines:
            ax.get_xaxis().set_visible(True)
            ax.get_yaxis().set_visible(True)
        else:
            ax.get_xaxis().set_visible(False)
            ax.get_yaxis().set_visible(False)

        show_lat_lon_ticks = kw.get('show_lat_lon_ticks', False)
        if show_lat_lon_ticks:
            ax.get_xaxis().set_ticklabels([])
            ax.get_yaxis().set_ticklabels([])
        else:
            ax.get_xaxis().set_ticklabels([])
            ax.get_yaxis().set_ticklabels([])

        if kw.get('title'):
            ax.set_title(kw['title'])

        # Draw Cbar
        cbar_label = kw.get('cbar_label', None)
        fig = ax.get_figure()  # had to get the fig from the ax, because geopandas plot only returns an ax.
        sm = plt.cm.ScalarMappable(cmap=color_scheme, norm=plt.Normalize(vmin=vmin, vmax=vmax))
        sm._A = []  # fake up the array of the scalar mappable. Urgh...
        if kw.get('cbar_position') == 'vertical':
            cax = fig.add_axes([0.9, 0.15, 0.03, 0.7])  # place it manually to the right
            fig.colorbar(sm, orientation='vertical', label=cbar_label, cax=cax)
        else:
            cax = fig.add_axes([0.2, 0.08, 0.6, 0.03])  # place it manually to the bottom
            fig.colorbar(sm, orientation='horizontal', label=cbar_label, cax=cax)

            # Make it less vertically tall to fit the cbar
            pos1 = ax.get_position()  # get the original position
            shift = 1.22
            pos2 = [pos1.x0 - ((shift - 1) / 2), pos1.y0, pos1.width * shift, pos1.height]
            ax.set_position(pos2)

        # Make it a little wider
        pos1 = ax.get_position()  # get the original position
        shift = 0.04
        pos2 = [pos1.x0, pos1.y0 + shift, pos1.width, pos1.height * (1 - shift)]
        ax.set_position(pos2)

        # plt.tight_layout() ignored cbar

        if kw.get('output_uri'):
            fig.savefig(kw['output_uri'])

    return ax

def plot_categorized_raster(input_array, min_category, max_category, n_categories, **kwargs):
    fig, ax = plt.subplots()
    cmap = hb.generate_custom_colorbar(input_array, color_scheme='bold_spectral_white_left', transparent_at_cbar_step=0)
    im = ax.imshow(input_array, cmap=cmap)

    bin_size = (max_category - min_category) / (n_categories - 1)
    bounds = np.linspace(min_category, max_category + 1, n_categories + 1)
    bounds = [i - bin_size / 2.0 for i in bounds]

    ticks = np.linspace(min_category, max_category + 1, n_categories + 1)

    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)

    orientation = kwargs.get('orientation', 'horizontal')
    aspect = kwargs.get('aspect', 20)
    shrink = kwargs.get('shrink', 1.0)
    cbar = plt.colorbar(im, ax=ax, cmap=cmap, ticks=ticks, boundaries=bounds, **kwargs)  # , format='%1i', spacing='proportional', norm=norm,
    # cbar = plt.colorbar(im, ax=ax, orientation=orientation, aspect=aspect, shrink=shrink, cmap=cmap, ticks=ticks, boundaries=bounds)  # , format='%1i', spacing='proportional', norm=norm,

    if kwargs.get('tick_labels'):
        cbar.set_ticklabels(kwargs['tick_labels'])

    tick_labelsize = kwargs.get('labelsize', 6)
    cbar.ax.tick_params(labelsize=tick_labelsize)

    if kwargs.get('title'):
        ax.set_title(kwargs['title'])

    if kwargs.get('title_fontsize'):
        ax.title.set_fontsize(kwargs['title_fontsize'])

    fig.tight_layout()

    output_path = kwargs.get('output_path', None)
    if output_path is None:
        hb.plot_at_exit(plt)
    else:
        fig.savefig(output_path, dpi=600)
        plt.close()

def _flatten_multi_geoms(geoms, colors=None):
    """
    Returns Series like geoms and colors, except that any Multi geometries
    are split into their components and colors are repeated for all component
    in the same Multi geometry.  Maintains 1:1 matching of geometry to color.
    Passing `color` is optional, and when no `color` is passed a list of None
    values is returned as `component_colors`.
    "Colors" are treated opaquely and so can actually contain any values.
    Returns
    -------
    components : list of geometry
    component_colors : list of whatever type `colors` contains
    """
    if colors is None:
        colors = [None] * len(geoms)

    components, component_colors = [], []

    # precondition, so zip can't short-circuit
    assert len(geoms) == len(colors)
    for geom, color in zip(geoms, colors):
        if geom.type.startswith('Multi'):
            for poly in geom:
                components.append(poly)
                # repeat same color for all components
                component_colors.append(color)
        else:
            components.append(geom)
            component_colors.append(color)

    return components, component_colors


# define some default colorschemes
color_scheme_data = {
    # like spectral, but no breakpoints and has a stronger yellow in the middle so that it can be easily seen.
    'spectral_bold':
        '''158,1,66
        213,62,79
        244,109,67
        230,202,21
        102,194,165
        50,136,189
        94,79,162''',

    'spectral_bold_white_left':
        '''255, 255, 255
        158,1,66
        213,62,79
        244,109,67
        230,202,21
        102,194,165
        50,136,189
        94,79,162''',

    'seals_simplified':
        '''255,255,255
        220,66,69
        219,164,75
        227,227,34
        0,160,18
        111,232,94
        172,191,229
        244,244,244
        228,228,228
        255,0,255
        255,255,255''',

    'seals_simplified_6_color':
        '''220,66,69
        219,164,75
        227,227,34
        0,160,18
        111,232,94
        172,191,229''',

    'spectral':
        '''158,1,66
        213,62,79
        244,109,67
        253,174,97
        254,224,139
        255,255,191
        230,245,152
        171,221,164
        102,194,165
        50,136,189
        94,79,162''',

    '11_classes':
        '''166,206,227
        31,120,180
        178,223,138
        51,160,44
        251,154,153
        227,26,28
        253,191,111
        255,127,0
        202,178,214
        106,61,154
        255,255,153''',

    'nlcd_16_class':
        '''71,107,190
        71,107,180
        71,107,170
        221,201,201
        170,0,0
        118,211,84
        51,160,44
        253,191,111
        255,127,0
        177,222,177
        177,222,177
        177,222,177
        255,255,153
        206,189,134
        82,200,211
        82,200,211''',

    '11_classes_pastel':
        '''141,211,199
        255,255,179
        190,186,218
        251,128,114
        128,177,211
        253,180,98
        179,222,105
        252,205,229
        217,217,217
        188,128,189
        204,235,19''',

    '12_classes':
        '''166,206,227
        31,120,180
        178,223,138
        51,160,44
        251,154,153
        227,26,28
        253,191,111
        255,127,0
        202,178,214
        106,61,154
        255,255,153
        177,89,40''',

    '12_classes_pastel':
        '''141,211,199
        255,255,179
        190,186,218
        251,128,114
        128,177,211
        253,180,98
        179,222,105
        252,205,229
        217,217,217
        188,128,189
        204,235,197
        255,237,111''',

    'spectral_white_center':
        '''158,1,66
        213,62,79
        244,109,67
        253,174,97
        254,224,139
        255,255,255
        230,245,152
        171,221,164
        102,194,165
        50,136,189
        94,79,162''',

    'magenta_blue_white_center':
        '''73,0,106
        122,1,119
        174,1,126
        221,52,151
        247,104,161
        250,159,181
        252,197,192
        253,224,221
        255,247,243
        255,255,217
        237,248,177
        199,233,180
        127,205,187
        65,182,196
        29,145,192
        34,94,168
        37,52,148
        8,29,88''',

    'prgn':
        '''118,42,131
        153,112,171
        194,165,207
        231,212,232
        247,247,247
        217,240,211
        166,219,160
        90,174,97
        27,120,55''',

    'white_to_black':
        '''255,255,255
        240,240,240
        217,217,217
        189,189,189
        150,150,150
        115,115,115
        82,82,82
        37,37,37''',

    'spectral_contrast':
        '''158,1,66
        213,62,79
        244,109,67
        254,224,139
        200,233,158
        102,194,165
        50,136,189
        94,79,162''',

    'bold_spectral':  # Name mistake backup
        '''158,1,66
        213,62,79
        244,109,67
        230,202,21
        102,194,165
        50,136,189
        94,79,162''',

    'bold_spectral_white_left':  # Name mistake backup
        '''255, 255, 255
        158,1,66
        213,62,79
        244,109,67
        230,202,21
        102,194,165
        50,136,189
        94,79,162''',

    'brbg':
        '''166, 97, 26
        223, 194, 125
        245, 245, 245
        128, 205, 193
        1, 133, 113''',

    'piyg':
        '''197,27,125
        222,119,174
        241,182,218
        253,224,239
        247,247,247
        230,245,208
        184,225,134
        127,188,65
        77,146,33''',

    'puor':
        '''179,88,6
        224,130,20
        253,184,99
        254,224,182
        247,247,247
        216,218,235
        178,171,210
        128,115,172
        84,39,136''',

    'rdbu':
        '''178,24,43
        214,96,77
        244,165,130
        253,219,199
        247,247,247
        209,229,240
        146,197,222
        67,147,195
        33,102,17''',

    'rdylbu':
        '''215,48,39
        244,109,67
        253,174,97
        254,224,144
        255,255,191
        224,243,248
        171,217,233
        116,173,209
        69,117,180''',

    'oranges':
        '''255,245,235
        254,230,206
        253,208,162
        253,174,107
        253,141,60
        241,105,19
        217,72,1
        166,54,3
        127,39,4''',

    'reds':
        '''255,245,240
        254,224,210
        252,187,161
        252,146,114
        251,106,74
        239,59,44
        203,24,29
        165,15,21
        103,0,13''',

    'purples':
        '''252,251,253
        239,237,245
        218,218,235
        188,189,220
        158,154,200
        128,125,186
        106,81,163
        84,39,143
        63,0,125''',

    'greys':
        '''255,255,255
        240,240,240
        217,217,217
        189,189,189
        150,150,150
        115,115,115
        82,82,82
        37,37,37
        0,0,0''',

    'greens':
        '''247,252,245
        229,245,224
        199,233,192
        161,217,155
        116,196,118
        65,171,93
        35,139,69
        0,109,44
        0,68,27''',

    'blues':
        '''247,251,255
        222,235,247
        198,219,239
        158,202,225
        107,174,214
        66,146,198
        33,113,181
        8,81,156
        8,48,107''',

    'bugn':
        '''247,252,253
        229,245,249
        204,236,230
        153,216,201
        102,194,164
        65,174,118
        35,139,69
        0,109,44
        0,68,27''',

    'bupu':
        '''247,252,253
        224,236,244
        191,211,230
        158,188,218
        140,150,198
        140,107,177
        136,65,157
        129,15,124
        77,0,75''',

    'gnbu':
        '''247,252,240
        224,243,219
        204,235,197
        168,221,181
        123,204,196
        78,179,211
        43,140,190
        8,104,172
        8,64,129''',

    'orrd':
        '''255,247,236
        254,232,200
        253,212,158
        253,187,132
        252,141,89
        239,101,72
        215,48,31
        179,0,0
        127,0,0''',

    'pubu':
        '''255,247,251
        236,231,242
        208,209,230
        166,189,219
        116,169,207
        54,144,192
        5,112,176
        4,90,141
        2,56,88''',

    'pubugn':
        '''255,247,251
        236,226,240
        208,209,230
        166,189,219
        103,169,207
        54,144,192
        2,129,138
        1,108,89
        1,70,54''',

    'purd':
        '''247,244,249
        231,225,239
        212,185,218
        201,148,199
        223,101,176
        231,41,138
        206,18,86
        152,0,67
        103,0,31''',

    'rdpu':
        '''255,247,243
        253,224,221
        252,197,192
        250,159,181
        247,104,161
        221,52,151
        174,1,126
        122,1,119
        73,0,106''',

    'ylgn':
        '''255,255,229
        247,252,185
        217,240,163
        173,221,142
        120,198,121
        65,171,93
        35,132,67
        0,104,55
        0,69,41''',

    'ylgnbu':
        '''255,255,217
        237,248,177
        199,233,180
        127,205,187
        65,182,196
        29,145,192
        34,94,168
        37,52,148
        8,29,88''',

    'ylorbr':
        '''255,255,229
        255,247,188
        254,227,145
        254,196,79
        254,153,41
        236,112,20
        204,76,2
        153,52,4
        102,37,6''',

    'ylorrd':
        '''255,255,204
        255,237,160
        254,217,118
        254,178,76
        253,141,60
        252,78,42
        227,26,28
        189,0,38
        128,0,38''',

    'nlcd':
        '''255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        72,109,161
        231,239,252
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        225,205,206
        220,152,129
        241,1,0
        171,1,1
        171,1,1
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        179,175,164
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        107,169,102
        29,101,51
        189,204,147
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        180,156,70
        209,187,130
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        237,237,203
        208,209,129
        164,204,81
        130,186,157
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        221,216,62
        174,114,41
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        187,215,237
        255,255,255
        255,255,255
        255,255,255
        255,255,255
        113,164,193
        ''',

    'random':
        '''''' + str(random.randint(0, 255)) + ',' + str(random.randint(0, 255)) + ',' + str(random.randint(0, 255)) + '''
''' + str(random.randint(0, 255)) + ',' + str(random.randint(0, 255)) + ',' + str(random.randint(0, 255)) + '''
''' + str(random.randint(0, 255)) + ',' + str(random.randint(0, 255)) + ',' + str(random.randint(0, 255)) + '''
''' + str(random.randint(0, 255)) + ',' + str(random.randint(0, 255)) + ',' + str(random.randint(0, 255)) + '''
''' + str(random.randint(0, 255)) + ',' + str(random.randint(0, 255)) + ',' + str(random.randint(0, 255)) + '''
''' + str(random.randint(0, 255)) + ',' + str(random.randint(0, 255)) + ',' + str(random.randint(0, 255)) + '''
''' + str(random.randint(0, 255)) + ',' + str(random.randint(0, 255)) + ',' + str(random.randint(0, 255)) + '''
''' + str(random.randint(0, 255)) + ',' + str(random.randint(0, 255)) + ',' + str(random.randint(0, 255)) + '''
''' + str(random.randint(0, 255)) + ',' + str(random.randint(0, 255)) + ',' + str(random.randint(0, 255))
}


